# bot/handlers/profile.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from bot.libs.helpers import safe_edit_message
from models.order import Order

def _is_available(v):
    # Treat None or empty string as NOT available.
    return v is not None and (not isinstance(v, str) or v.strip() != "")

def _fmt_money(v):
    try:
        return f"{float(v):.2f}"
    except Exception:
        return str(v)

def build_profile_message(user):
    """
    Returns (text, inline_kb). Only includes fields that are present (not None/empty).
    """
    lines = ["⚔️——— USER PROFILE ———⚔️\n"]

    # Basic identity
    if _is_available(getattr(user, "name", None)):
        lines.append(f"👤 Name : {user.name}")
    # always show id (should be available)
    uid = getattr(user, "telegram_id", getattr(user, "id", None))
    if uid is not None:
        lines.append(f"🆔 User ID : {uid}")

    # Balance
    if _is_available(getattr(user, "balance", None)):
        lines.append(f"💎 Balance : {_fmt_money(user.balance)}")

    total_bought = Order.objects(user=user).count()
    total_used = Order.objects(user=user, status="completed").count()
    total_cancelled = Order.objects(user=user, status="cancelled").count()

    if total_bought > 0:
        lines.append(f"📞 Total Numbers Bought : {total_bought}")
    if total_used > 0:
        lines.append(f"📲 Total Numbers Used : {total_used}")
    if total_cancelled > 0:
        lines.append(f"🚫 Total Numbers Cancelled : {total_cancelled}")
    
    if len(lines) == 1:
        # nothing useful to show
        text = "📭 No profile information available."
    else:
        text = "\n".join(lines)

    # Keyboard: back to main / close
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("« Back", callback_data="back_main"))
    return text, kb


def handle(bot, call):
    """
    Callback handler for callback_data starting with "profile".
    Supports "profile" or "profile:<page_or_id>" (we ignore the second part here).
    """
    user_id = str(call["from"]["id"])
    user = User.objects(telegram_id=user_id).first()
    if not user:
        bot.answer_callback_query(call["id"], "❌ User not found.")
        return

    text, kb = build_profile_message(user)
    safe_edit_message(bot, call, text, kb)
    bot.answer_callback_query(call["id"])
