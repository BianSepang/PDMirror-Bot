import logging
import os
import sys

import tomli


__version__ = "0.1.3"

# Setting up logging
logging.basicConfig(
    format="[%(asctime)s] %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
LOGGER = logging.getLogger("PDMirror_BOT")

# Load config.toml
with open("config.toml", "rb") as f:
    CONFIG_DICT = tomli.load(f)

# Check if the required section of config.toml is filled
if not all(CONFIG_DICT["required"].values()):
    LOGGER.error("Must filled all the required section of config.toml. Exiting.")
    sys.exit(1)

# Create download directory
DOWNLOAD_DIR = os.path.join(os.getcwd(), CONFIG_DICT["general"]["download_dir"])
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
