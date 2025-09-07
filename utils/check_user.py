from utils.config import get_required_links
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import apihelper
import logging
import redis
import json
import time

logger = logging.getLogger(__name__)

# Connect to Redis (local instance)
r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)


def join_check_keyboard(group_link: str = None, channel_link: str = None) -> InlineKeyboardMarkup:
    """
    Build join buttons using invite links or @usernames.
    """
    kb = InlineKeyboardMarkup()

    if group_link:
        kb.add(InlineKeyboardButton(
            text="👥 Join Group",
            url=group_link if group_link.startswith("http") else f"https://t.me/{group_link.replace('@', '')}"
        ))

    if channel_link:
        kb.add(InlineKeyboardButton(
            text="📢 Join Channel",
            url=channel_link if channel_link.startswith("http") else f"https://t.me/{channel_link.replace('@', '')}"
        ))

    return kb


def cache_get_status(user_id: str, chat_id: str):
    """Retrieve membership status from Redis cache."""
    key = f"membership:{user_id}:{chat_id}"
    data = r.get(key)
    if data:
        return json.loads(data).get("status")
    return None


def cache_set_status(user_id: str, chat_id: str, status: str, ttl: int = 300):
    """Store membership status in Redis with TTL."""
    key = f"membership:{user_id}:{chat_id}"
    r.setex(key, ttl, json.dumps({"status": status, "ts": int(time.time())}))


def ensure_membership(bot, chat_id: int, user_id: str) -> bool:
    """
    Ensure user is a member of required group/channel.
    Cached in Redis for 300s.
    """
    links = get_required_links()
    group_id = links.get("group_id")
    group_link = links.get("group_link")
    channel_id = links.get("channel_id")
    channel_link = links.get("channel_link")

    required_chats = [(group_id, group_link), (channel_id, channel_link)]
    required_chats = [(cid, link) for cid, link in required_chats if cid]

    try:
        for target_id, invite_link in required_chats:
            # Check Redis first
            status = cache_get_status(user_id, target_id)

            if status is None:
                # Call Telegram API if not cached
                status = bot.get_chat_member(target_id, user_id).status
                cache_set_status(user_id, target_id, status)

            if status in {"left", "kicked"}:
                bot.send_message(
                    chat_id,
                    "🚨 You must join our group/channel to use this bot.",
                    reply_markup=join_check_keyboard(group_link, channel_link),
                )
                return False

    except apihelper.ApiTelegramException as e:
        logger.error(f"Telegram API error during membership check for user {user_id}: {e}")
        bot.send_message(
            1443989714,
            f"Membership check failed for {user_id} in chat {target_id}: {e}"
        )
        return False

    except Exception as e:
        logger.warning(f"Membership check failed for {user_id}: {e}")
        bot.send_message(
            1443989714,
            f"Membership check failed for {user_id}: {e}"
        )
        return False

    return True
