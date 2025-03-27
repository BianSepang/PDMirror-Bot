import asyncio
import logging
import os

from aioaria2 import Aria2WebsocketClient
from aioaria2.exceptions import Aria2rpcException

from bot import DOWNLOAD_DIR
from .tools import run_command


class AioAria:
    def __init__(self, client):
        self.logger = self._setup_logging()
        self.client: Aria2WebsocketClient = client

    
    def _setup_logging(self):
        logger = logging.getLogger("AioAria")
        logger.setLevel(logging.INFO)

        return logger

    
    @classmethod
    async def initialize(cls):
        try:
            client: Aria2WebsocketClient = await Aria2WebsocketClient.new(
                url="http://localhost:6800/jsonrpc"
            )
        except Aria2rpcException:
            logger = logging.getLogger("AioAria")
            logger.setLevel(logging.INFO)

            logger.info("Initializing aria2 daemon.")
            await run_command("aria2c --enable-rpc=true --daemon=true --quiet")
            
            await asyncio.sleep(2.5)

            client: Aria2WebsocketClient = await Aria2WebsocketClient.new(
                url="http://localhost:6800/jsonrpc"
            )
        
        await client.changeGlobalOption(
            {
                "allow-overwrite": "true",
                "auto-file-renaming": "true",
                "bt-enable-lpd": "true",
                "bt-remove-unselected-file": "true",
                "check-certificate": "false",
                "content-disposition-default-utf8": "true",
                "continue": "true",
                "dir": os.path.join(os.getcwd(), DOWNLOAD_DIR),
                "disk-cache": "32M",
                "follow-torrent": "mem",
                "http-accept-gzip": "true",
                "max-concurrent-downloads": "3",
                "max-connection-per-server": "10",
                "max-file-not-found": "0",
                "max-overall-download-limit": "0",
                "max-overall-upload-limit": "1K",
                "max-tries": "20",
                "min-split-size": "10M",
                "reuse-uri": "true",
                "rpc-max-request-size": "1024M",
                "seed-time": "0",
                "split": "10",
                "summary-interval": "0",
                "user-agent": "Wget/1.12"
            }
        )

        return cls(client)

    
    async def shutdown(self):
        self.logger.info("Shutting down aria2 daemon and AioAria client.")
        await self.client.purgeDownloadResult()
        await self.client.forceShutdown()
        await self.client.close()
