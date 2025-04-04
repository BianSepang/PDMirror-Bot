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
            self.logger.info(e, exc_info=True)
            return
        
        if not state:
            return
        
        self.logger.info("Recovering bot state.")
        value = state.get("value")
        pts = value.get("pts")
        date = value.get("date")
        prev_pts = 0

        while True:
            diff = await self.invoke(
                raw.functions.updates.GetDifference(
                    pts=pts,
                    date=date,
                    qts=0,
                )
            )
            if isinstance(diff, raw.types.updates.DifferenceEmpty):
                self.db.remove(self.db_query.name == "state")
                break
            elif isinstance(diff, raw.types.updates.DifferenceTooLong):
                pts = diff.pts
                continue
            users = {user.id for user in diff.users}
            chats = {chat.id for chat in diff.chats}
            if isinstance(diff, raw.types.updates.DifferenceSlice):
                new_state = diff.intermediate_state
                pts = new_state.pts
                date = new_state.date
                # Stop if current pts is same with previous loop
                if prev_pts == pts:
                    self.db.remove(self.db_query.name == "state")
                    break
                prev_pts = pts
            else:
                new_state = diff.state
            for msg in diff.new_messages:
                self.dispatcher.updates_queue.put_nowait((
                    raw.types.UpdateNewMessage(
                        message=msg,
                        pts=new_state.pts,
                        pts_count=-1,
                    ),
                    users,
                    chats,
                ))

            for update in diff.other_updates:
                self.dispatcher.updates_queue.put_nowait((update, users, chats))
            if isinstance(diff, raw.types.updates.Difference):
                self.db.remove(self.db_query.name == "state")
                break
