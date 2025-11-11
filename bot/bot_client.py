import asyncio

from pyrogram import Client, raw
from tinydb import TinyDB, Query

from bot import CONFIG_DICT, LOGGER, __version__
from bot.utils.aioaria import AioAria


class BotClient(Client):
    def __init__(self):
        self.logger = LOGGER
        self.logger.info("Initializing bot client.")
        self.aioaria = None
        self.config = CONFIG_DICT
        self.db = TinyDB("db.json").table("bot_settings")
        self.db_query = Query()
        # Map of aria2 download GID -> (chat_id, message_id) for status messages
        self.active_downloads = {}
        # Map of user_id -> (chat_id, message_id, update_task) for status command messages
        self.status_messages = {}

        super().__init__(
            name="botclient",
            api_id=self.config["required"]["api_id"],
            api_hash=self.config["required"]["api_hash"],
            bot_token=self.config["required"]["bot_token"],
            plugins={"root": "bot.plugins"},
        )


    async def start(self):
        await super().start()
        await self.recover_state()

        self.aioaria = await AioAria.initialize()

        bot_info = await self.get_me()
        self.logger.info(f"Bot is running version {__version__}")
        self.logger.info(f"Bot info : {bot_info.full_name} (@{bot_info.username})")
    
    async def stop(self, block=True, keep_aria=False):
        self.logger.info("Saving bot state.")

        state = await self.invoke(raw.functions.updates.GetState())
        value = {"pts": state.pts, "qts": state.qts, "date": state.date}
        self.db.upsert({"name": "state", "value": value}, self.db_query.name == "state")

        async def do_it():
            await self.terminate()
            await self.disconnect()
        
        if block:
            await do_it()
        else:
            self.loop.create_task(do_it())
        
        self.logger.info("Shutting down bot client.")

        if not keep_aria:
            await self.aioaria.shutdown()

        await asyncio.sleep(2.5)

        return self
    

    async def recover_state(self):
        try:
            state = self.db.get(self.db_query.name == "state")
        except Exception as e:
            self.logger.error("Failed to read saved state from DB", exc_info=True)
            return

        if not state:
            return

        self.logger.info("Recovering bot state.")
        value = state.get("value", {}) or {}
        pts = value.get("pts", 0)
        date = value.get("date", 0)
        prev_pts = None

        start_time = asyncio.get_event_loop().time()
        max_duration = 30.0  # seconds: fail-safe to avoid infinite loops
        max_retries = 5
        retry_count = 0

        while True:
            # Timeout guard
            if asyncio.get_event_loop().time() - start_time > max_duration:
                self.logger.warning("recover_state timed out; removing saved state and aborting recovery.")
                self.db.remove(self.db_query.name == "state")
                break

            try:
                diff = await self.invoke(
                    raw.functions.updates.GetDifference(
                        pts=pts,
                        date=date,
                        qts=0,
                    )
                )
                retry_count = 0
            except Exception as e:
                retry_count += 1
                self.logger.warning("GetDifference failed (attempt %s/%s). Retrying...", retry_count, max_retries, exc_info=True)
                if retry_count >= max_retries:
                    self.logger.error("Max retries reached while recovering state; aborting and removing saved state.")
                    self.db.remove(self.db_query.name == "state")
                    break
                # exponential backoff with cap
                await asyncio.sleep(min(2 ** retry_count, 5))
                continue

            # Defensive handling of diff types and attributes
            if isinstance(diff, raw.types.updates.DifferenceEmpty):
                self.db.remove(self.db_query.name == "state")
                break
            if isinstance(diff, raw.types.updates.DifferenceTooLong):
                # advance pts and try again
                pts = getattr(diff, "pts", pts)
                continue

            users = {user.id: user for user in getattr(diff, "users", []) or []}
            chats = {chat.id: chat for chat in getattr(diff, "chats", []) or []}

            if isinstance(diff, raw.types.updates.DifferenceSlice):
                new_state = getattr(diff, "intermediate_state", None)
                if new_state:
                    pts = getattr(new_state, "pts", pts)
                    date = getattr(new_state, "date", date)
                # stop if stuck on same pts
                if prev_pts is not None and prev_pts == pts:
                    self.logger.warning("recover_state detected no progress (pts unchanged). Cleaning up saved state.")
                    self.db.remove(self.db_query.name == "state")
                    break
                prev_pts = pts
            else:
                new_state = getattr(diff, "state", None)

            # enqueue new messages and other updates defensively
            for msg in getattr(diff, "new_messages", []) or []:
                try:
                    pts_for_msg = getattr(new_state, "pts", pts) if new_state else pts
                    update = raw.types.UpdateNewMessage(message=msg, pts=pts_for_msg, pts_count=-1)
                    self.dispatcher.updates_queue.put_nowait((update, users, chats))
                except Exception:
                    self.logger.exception("Failed to enqueue UpdateNewMessage from recovered diff.")

            for upd in getattr(diff, "other_updates", []) or []:
                try:
                    self.dispatcher.updates_queue.put_nowait((upd, users, chats))
                except Exception:
                    self.logger.exception("Failed to enqueue other update from recovered diff.")

            if isinstance(diff, raw.types.updates.Difference):
                # final snapshot reached; remove saved state
                self.db.remove(self.db_query.name == "state")
                break
