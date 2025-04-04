from pyrogram import filters
from pyrogram.types import Message

from bot.bot_client import BotClient


async def owner_filter(_, client: BotClient, message: Message):
    if message.sender_chat:
        return False

    return message.from_user.id == int(client.config["required"]["owner_id"])


async def authorized_only_filter(_, client: BotClient, message: Message):
    users_config = client.config.get("users", {})
    authorized_users = map(int, users_config.get("authorized_users", "").split())
    authorized_chats = map(int, users_config.get("authorized_chats", "").split())

    return (
        message.from_user.id == int(client.config["required"]["owner_id"])
        or message.from_user.id in authorized_users
        or message.chat.id in authorized_chats
    )


# OWNER_ONLY = filters.create(owner_filter)
# AUTHORIZED_ONLY = filters.create(authorized_only_filter)
