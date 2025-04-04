import asyncio

from pyrogram import idle

from bot.bot_client import BotClient, LOGGER


async def main():
    bot = BotClient()

    try:
        await bot.start()
        await idle()
    except KeyboardInterrupt:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
