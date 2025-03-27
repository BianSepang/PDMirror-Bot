import asyncio

from pyrogram import idle

from bot.bot_client import BotClient, LOGGER


async def main():
    await BotClient().start()
    await idle()


if __name__ == "__main__":
    asyncio.run(main())