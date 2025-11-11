import asyncio
import os

from aioaria2 import Aria2rpcException
from aiopath import AsyncPath
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

    client.logger.info(f"Added download GID : {download_gid} for URL : {url}")

    status_message = await message.reply(f"Download added, GID : `{download_gid}`")
    # Register status message so other handlers (cancel) can update it
    client.active_downloads[download_gid] = (status_message.chat.id, status_message.id)

    last_status_message = ""
    last_update_time = 0
    start_time = asyncio.get_event_loop().time()

    while True:
        await asyncio.sleep(1)

        try:
            download = await client.aioaria.client.tellStatus(download_gid)
        except Aria2rpcException as e:
            # GID disappeared (likely cancelled/removed) — stop polling and notify
            client.logger.info(f"GID {download_gid} not found during status poll: {e}")
            # Only update the status message if it's still registered (cancel handler may have already edited+removed it)
            mapping = client.active_downloads.pop(download_gid, None)
            if mapping:
                chat_id, msg_id = mapping
                try:
                    await client.edit_message_text(chat_id, msg_id, f"Download GID `{download_gid}` not found (cancelled or removed).")
                except Exception:
                    pass
            break

        # files may be missing if status is incomplete/removed — guard access
        files = download.get("files") or []
        filename = os.path.basename(files[0].get("path")) if files and files[0].get("path") else "unknown"
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
                client.active_downloads.pop(download_gid, None)
                await client.aioaria.client.removeDownloadResult(download_gid)
                break

        now = asyncio.get_event_loop().time()
        if now - last_update_time >= 10:
            elapsed_usec = int((now - start_time) * 1_000_000)
            status = (
                f"Name : {filename}\n"
                f"Elapsed : {format_duration_us(elapsed_usec)}\n"
                f"Downloaded : {readable_bytes(completed_length)} of {readable_bytes(total_length)}\n"
                f"ETA : {format_duration_us(eta)} @ {readable_bytes(download_speed)}/s\n"
                f"GID : `{download_gid}`"
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
    client.logger.info(f"Uploaded {file_path} to Pixeldrain: {link}")


@BotClient.on_message(AUTHORIZED_ONLY & filters.command(["cancel", "c"]))
async def cancel_download_handler(client: BotClient, message: Message):
    if len(message.command) < 2:
        await message.reply("Must provide a download GID to cancel.")
        return

    download_gid = message.command[1]
    
    if client.active_downloads.get(download_gid) is None:
        await message.reply(f"No active download with GID#`{download_gid}` found.")
        return
    
    files = await client.aioaria.client.getFiles(download_gid)

    try:
        await client.aioaria.client.remove(download_gid)
        await client.aioaria.client.removeDownloadResult(download_gid)
    except Aria2rpcException as e:
        await message.reply(f"Failed to remove GID#`{download_gid}`")
        client.logger.error(f"Failed to remove GID#{download_gid} : {e.msg}")
        return

    # If we have a status message registered for this gid, update it to "Cancelled"
    mapping = client.active_downloads.pop(download_gid, None)
    if mapping:
        chat_id, msg_id = mapping
        try:
            await client.edit_message_text(chat_id, msg_id, f"Cancelled download GID#`{download_gid}`.")
        except Exception:
            # ignore edit errors
            pass
    
    if files:
        for file_info in files:
            file = AsyncPath(file_info.get("path"))
            temp_files = [AsyncPath(file), AsyncPath(f"{file}.aria2")]
            for temp_file in temp_files:
                if await temp_file.exists():
                    await temp_file.unlink()
        client.logger.info(f"Deleted {[temp_file.name for temp_file in temp_files]} from GID#{download_gid}")

    client.logger.info(f"Cancelled download GID : {download_gid}")
    await message.reply(f"GID#`{download_gid}` cancelled.")

@BotClient.on_message(AUTHORIZED_ONLY & filters.command("status"))
async def status_handler(client: BotClient, message: Message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Cancel any existing status update task for this user and delete old message
    if user_id in client.status_messages:
        old_chat_id, old_msg_id, old_task = client.status_messages[user_id]
        if old_task and not old_task.done():
            old_task.cancel()
        # Delete the old status message if it's in the same chat
        if old_chat_id == chat_id:
            try:
                await client.delete_messages(chat_id, old_msg_id)
            except Exception as e:
                client.logger.debug(f"Failed to delete old status message: {e}")
    
    # Create initial status message
    status_msg = await message.reply("📥 Fetching download status...")
    
    # Create update task
    async def update_status():
        try:
            last_update_count = 0
            while True:
                await asyncio.sleep(5)  # Update every 5 seconds
                
                try:
                    # Get all active downloads
                    downloads = await client.aioaria.client.tellActive()
                except Exception as e:
                    client.logger.warning(f"Failed to fetch active downloads: {e}")
                    try:
                        await status_msg.edit_text(f"❌ Error fetching downloads: {str(e)[:50]}")
                    except Exception:
                        pass
                    continue
                
                if not downloads:
                    # No active downloads; exit gracefully
                    try:
                        await status_msg.edit_text("✅ No active downloads.")
                    except Exception:
                        pass
                    break
                
                # If download count changed, clean up task from mapping
                if len(downloads) != last_update_count:
                    last_update_count = len(downloads)
                
                # Build status text
                now = asyncio.get_event_loop().time()
                status_lines = [
                    f"📥 **Active Downloads** [{len(downloads)}]",
                    f"⏰ Last updated: <t:{int(now)}:R>\n"
                ]
                
                total_completed = 0
                total_size = 0
                
                for idx, dl in enumerate(downloads, 1):
                    gid = dl.get("gid", "unknown")
                    files = dl.get("files") or []
                    filename = os.path.basename(files[0].get("path")) if files and files[0].get("path") else "unknown"
                    completed = int(dl.get("completedLength", 0))
                    total = int(dl.get("totalLength", 0))
                    speed = int(dl.get("downloadSpeed", 0))
                    
                    total_completed += completed
                    total_size += total
                    
                    try:
                        eta = ((total - completed) / speed) * 1_000_000 if speed > 0
