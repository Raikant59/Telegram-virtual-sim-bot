# bot/handlers/promo.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from models.user import User
from services.promos import redeem_code
from bot.libs.helpers import safe_edit_message

def _ensure_user(bot, from_):
    uid = str(from_["id"])
    user = User.objects(telegram_id=uid).first()
    if not user:
        user = User(telegram_id=uid, username=from_.get("username", "")).save()
    return user

def menu(bot, call):
    _ensure_user(bot, call["from"])
    text = "🎟️ <b>Use Promo</b>\n\nSend me your promo code (case-insensitive)."
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("« Back", callback_data="back_main"))
    safe_edit_message(bot, call, text, kb)
    bot.send_message(call["message"]["chat"]["id"],
                     "Please reply with your code:",
                     reply_markup=ForceReply(selective=True))

def capture_code(bot, message):
    reply = message.get("reply_to_message")
    if not reply: return
    if "Please reply with your code" not in (reply.get("text") or ""):
        return
    code = (message.get("text") or "").strip()
    user = _ensure_user(bot, message["from"])

    ok, msg = redeem_code(bot, user, code)
    bot.send_message(message["chat"]["id"], msg)
