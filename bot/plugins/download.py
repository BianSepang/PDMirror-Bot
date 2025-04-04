import asyncio
import os

from pyrogram import filters
from pyrogram.types import Message

from bot.bot_client import BotClient
from bot.utils.filters import AUTHORIZED_ONLY
from bot.utils.tools import format_duration_us, readable_bytes
from bot.utils.pixeldrain import upload_file_to_pixeldrain


@BotClient.on_message(AUTHORIZED_ONLY & filters.command(["download", "dl"]))
async def download_handler(client: BotClient, message: Message):
    if len(message.command) < 2:
        await message.reply("Must provide a download link.")
        return

    url = message.command[1]
    download_gid = await client.aioaria.client.addUri([url])

    status_message = await message.reply(f"Download added, GID : `{download_gid}`")

    last_status_message = ""
    last_update_time = 0

    while True:
        await asyncio.sleep(1)

        download = await client.aioaria.client.tellStatus(download_gid)

        filename = os.path.basename(download.get("files")[0].get("path"))
        completed_length = int(download.get("completedLength", 0))
        total_length = int(download.get("totalLength", 0))
        download_speed = int(download.get("downloadSpeed", 0))
        try:
            eta = ((total_length - completed_length) / download_speed) * 1_000_000
        except ZeroDivisionError:
            eta = 0

        if download["status"] == "complete":
            status = f"Download completed.\n{filename}"
            if last_status_message != status:
                await status_message.edit(status)
                await client.aioaria.client.removeDownloadResult(download_gid)
                break

        now = asyncio.get_event_loop().time()
        if now - last_update_time >= 10:
            status = (
                f"Name : {filename}\n"
                f"Downloaded : {readable_bytes(completed_length)} of {readable_bytes(total_length)}\n"
                f"ETA : {format_duration_us(eta)} @ {readable_bytes(download_speed)}/s"
            )
            if last_status_message != status:
                await status_message.edit(status)
                last_status_message = status
                last_update_time = now


@BotClient.on_message(AUTHORIZED_ONLY & filters.command("pd"))
async def pd_handler(client: BotClient, message: Message):
    if len(message.command) < 2:
        await message.reply("Input args")
        return
    
    file_path = message.command[1]
    file_name = os.path.basename(file_path)

    if not os.path.exists(file_path):
        await message.reply("File not exists.")
        return

    status_message = await message.reply("Uploading to pixeldrain.")

    link = await upload_file_to_pixeldrain(
        file_path=file_path,
        file_name=file_name,
        api_key=client.config["general"]["pixeldrain_api_key"],
        message=status_message
    )

    await status_message.edit(f"Upload complete.\n{link}")
