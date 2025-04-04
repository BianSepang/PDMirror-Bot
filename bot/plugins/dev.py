import os
import signal
import sys

from pyrogram import filters
from pyrogram.types import Message

from bot.bot_client import BotClient
from bot.utils.filters import AUTHORIZED_ONLY, OWNER_ONLY


@BotClient.on_message(AUTHORIZED_ONLY & filters.command("start"))
async def start_function(client: BotClient, message: Message):
    user = message.from_user

    await message.reply(
        text=f"Hello {user.full_name}!",
    )

    client.logger.info(f"User {user.full_name} ({user.id}) pressed start.")


@BotClient.on_message(OWNER_ONLY & filters.command("raw"))
async def raw_function(_, message: Message):
    await message.reply(message.raw)


@BotClient.on_message(OWNER_ONLY & filters.command("restart"))
async def restart_function(client: BotClient, message: Message):
    await message.reply("Restarting.")

    await client.stop(block=False, keep_aria=True)
    
    os.execv(sys.executable, [sys.executable, "-m", "bot"])


@BotClient.on_message(OWNER_ONLY & filters.command("shutdown"))
async def shutdown_function(client: BotClient, message: Message):
    await message.reply("Shutting down.")

    await client.stop(block=False)
    
    os.kill(os.getpid(), signal.SIGINT)
