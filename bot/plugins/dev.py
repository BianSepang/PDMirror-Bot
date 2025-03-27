import os
import signal
import sys

from pyrogram import filters
from pyrogram.types import Message

from bot.bot_client import BotClient


@BotClient.on_message(filters.incoming & filters.private & filters.command("start"))
async def start_function(_, message: Message):
    await message.reply(
        text=f"Hello {message.from_user.full_name}!",
    )


@BotClient.on_message(filters.incoming & filters.private & filters.command("raw"))
async def raw_function(_, message: Message):
    await message.reply(message.raw)


@BotClient.on_message(filters.incoming & filters.private & filters.command("restart"))
async def restart_function(client: BotClient, message: Message):
    await message.reply("Restarting.")

    await client.stop(block=False, keep_aria=True)
    
    os.execv(sys.executable, [sys.executable, "-m", "bot"])


@BotClient.on_message(filters.incoming & filters.private & filters.command("shutdown"))
async def shutdown_function(client: BotClient, message: Message):
    await message.reply("Shutting down.")

    await client.stop(block=False)
    
    os.kill(os.getpid(), signal.SIGINT)
