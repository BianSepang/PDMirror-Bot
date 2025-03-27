import asyncio

from aioaria2 import Aria2WebsocketClient
from pyrogram import Client

from bot import CONFIG_DICT, LOGGER, __version__
from bot.utils.aria import Aria2
from bot.utils.aioaria import AioAria


class BotClient(Client):
    def __init__(self):
        self.logger = LOGGER

        self.logger.info("Initializing bot client.")

        super().__init__(
            name="botclient",
            api_id=CONFIG_DICT["required"]["api_id"],
            api_hash=CONFIG_DICT["required"]["api_hash"],
            bot_token=CONFIG_DICT["required"]["bot_token"],
            plugins={"root": "bot.plugins"},
        )

        self.aioaria = None

        self.config = CONFIG_DICT


    async def start(self):
        await super().start()

        self.aioaria = await AioAria.initialize()

        bot_info = await self.get_me()
        self.logger.info(f"Bot is running version {__version__}")
        self.logger.info(f"Bot info : {bot_info.full_name} (@{bot_info.username})")
    
    async def stop(self, block=True, keep_aria=False):
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

