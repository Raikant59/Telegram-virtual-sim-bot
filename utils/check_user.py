from utils.config import get_required_links
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from cachetools import TTLCache
from telebot import apihelper
import logging

logger = logging.getLogger(__name__)

# cache: key=(user_id, chat_id), value=status, expires in 300s
membership_cache = TTLCache(maxsize=10000, ttl=300)


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

def ensure_membership(bot, chat_id: int, user_id: str) -> bool:
    """
    Ensure user is a member of required group/channel.
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
            cache_key = (user_id, target_id)

            status = membership_cache.get(cache_key)
            if status is None:
                status = bot.get_chat_member(target_id, user_id).status
                membership_cache[cache_key] = status

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
