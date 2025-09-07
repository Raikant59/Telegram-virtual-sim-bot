from utils.config import get_required_links
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


def join_check_keyboard(group_url: str = None, channel_url: str = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()

    if group_url:
        kb.add(InlineKeyboardButton(
            text="👥 Join Group",
            url=f"https://t.me/{group_url.replace('@', '')}"
        ))

    if channel_url:
        kb.add(InlineKeyboardButton(
            text="📢 Join Channel",
            url=f"https://t.me/{channel_url.replace('@', '')}"
        ))

    return kb

from cachetools import TTLCache

# cache: key=(user_id, chat_id), value=status, expires in 300s
membership_cache = TTLCache(maxsize=10000, ttl=300)

def ensure_membership(bot, chat_id: int, user_id: str) -> bool:
    links = get_required_links()
    group = links.get("group")
    channel = links.get("channel")

    required_chats = [c for c in (group, channel) if c]

    try:
        for target in required_chats:
            cache_key = (user_id, target)

            status = membership_cache.get(cache_key)
            if status is None:
                status = bot.get_chat_member(target, user_id).status
                membership_cache[cache_key] = status

            if status in {"left", "kicked"}:
                bot.send_message(
                    chat_id,
                    "🚨 You must join our group/channel to use this bot.",
                    reply_markup=join_check_keyboard(group, channel),
                )
                return False

    except Exception as e:
        print(f"Membership check failed for {user_id}: {e}")
        return True

    return True
