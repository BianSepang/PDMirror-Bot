import logging
import os
import subprocess
import time

import aria2p
from requests.exceptions import ConnectionError

from bot import DOWNLOAD_DIR


class Aria2:

    def __init__(self):
        self.logger = self._setup_logging()
        self.download_dir = os.path.join(os.getcwd(), DOWNLOAD_DIR)

        self.aria2client = aria2p.API(
            aria2p.Client(
                host="http://localhost",
                port=6800,
                secret="",
            )
        )

        try:
            self.aria2client.get_downloads()
        except ConnectionError:
            self.initialize_aria2()
            time.sleep(2.5)
        else:
            self.logger.info("Aria2c is already up and running.")
        
        self.aria2client.set_global_options(
            {
                "allow-overwrite": "true",
                "auto-file-renaming": "true",
                "bt-enable-lpd": "true",
                "bt-remove-unselected-file": "true",
                "check-certificate": "false",
                "content-disposition-default-utf8": "true",
                "continue": "true",
                "dir": self.download_dir,
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
    
    def initialize_aria2(self):
        self.logger.info("Initializing Aria2.")
        try:
            subprocess.Popen(["aria2c", "--enable-rpc=true", "--daemon=true", "--quiet=true"])
        except Exception as exc:
            self.logger.error(f'"{exc}" Unable to initialize Aria2.')
        else:
            self.logger.info("Aria2 is now up and running.")
        
    def _setup_logging(self):
        logger = logging.getLogger("Aria2")
        logger.setLevel(logging.INFO)

        return logger

    def download_uri(self, uri):
        return self.aria2client.add_uris([uri])
    
    def get_download(self, gid):
        return self.aria2client.get_download(gid)
