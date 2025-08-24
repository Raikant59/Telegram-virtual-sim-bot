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


def ensure_membership(bot, chat_id, user_id):
    links = get_required_links()
    group = links.get("group")
    channel = links.get("channel")

    try:
        if group:
            m = bot.get_chat_member(group, user_id)
            if m.status in ["left", "kicked"]:
                bot.send_message(chat_id,
                                 "🚨 You must join our group/channel to use this bot.",
                                 reply_markup=join_check_keyboard(group, channel))
                return False
        if channel:
            m = bot.get_chat_member(channel, user_id)
            if m.status in ["left", "kicked"]:
                bot.send_message(chat_id,
                                 "🚨 You must join our group/channel to use this bot.",
                                 reply_markup=join_check_keyboard(group, channel))
                return False
    except Exception as e:
        print("Membership check failed:", e)
        return False

    return True
