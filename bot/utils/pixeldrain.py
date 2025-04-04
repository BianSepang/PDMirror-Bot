import aiohttp
import aiofiles
import os
import time
import base64
from typing import Callable

from pyrogram.types import Message

from bot import LOGGER
from bot.utils.tools import format_bytes, format_duration_us


class UploadStreamReader:
    def __init__(self, file_path: str, chunk_size: int = 1024 * 1024, callback: Callable = None):
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.callback = callback
        self.uploaded = 0
        self.total = os.path.getsize(file_path)
        self.start_time = time.time()
        self.last_update_time = 0

    async def __aiter__(self):
        async with aiofiles.open(self.file_path, "rb") as f:
            while True:
                chunk = await f.read(self.chunk_size)
                if not chunk:
                    break

                self.uploaded += len(chunk)

                now = time.time()
                if self.callback and (
                    now - self.last_update_time >= 10 or self.uploaded == self.total
                ):
                    elapsed = now - self.start_time
                    speed = self.uploaded / elapsed if elapsed > 0 else 0
                    percent = self.uploaded / self.total
                    await self.callback(self.uploaded, self.total, speed, percent)
                    self.last_update_time = now

                yield chunk


async def upload_file_to_pixeldrain(
    file_path: str,
    file_name: str,
    api_key: str,
    message: Message,
):
    async def progress_callback(uploaded, total, speed, percent):
        filled_bar = int(percent * 10)
        bar = f"{(filled_bar * 10) * '▰'}{int(10 - filled_bar) * '▱'}"
        speed_str = format_bytes(speed) + "/s"
        uploaded_str = format_bytes(uploaded)
        total_str = format_bytes(total)
        eta_str = format_duration_us(((uploaded - total) / speed) * 10**6)

        text = (
            f"📤 **Uploading to Pixeldrain**\n"
            f"`{file_name}`\n"
            f"{bar} `{percent * 100:.2f}%`\n"
            f"`{uploaded_str} / {total_str}` @ `{speed_str}`\n"
            f"⏳ ETA: `{eta_str}`"
        )

        try:
            await message.edit_text(text)
        except Exception as e:
            LOGGER.warning(e, exc_info=True)
            pass

    reader = UploadStreamReader(file_path, callback=progress_callback)
    headers = {
        "Authorization": "Basic " + base64.b64encode(f":{api_key}".encode()).decode()
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(
            f"https://pixeldrain.com/api/file/{file_name}",
            data=reader,
            headers=headers,
        ) as resp:
            if resp.status >= 400:
                err = await resp.text()
                raise Exception(f"Upload failed: {err}")
            result = await resp.json(content_type="text/plain")

    file_id = result.get("id")
    return f"https://pd.cybar.xyz/{file_id}"
