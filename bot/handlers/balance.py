from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from bot.libs.helpers import safe_edit_message

def handle(bot, call):
    """Handles Balance callback"""
    user_id = str(call["from"]["id"])
    user = User.objects(telegram_id=user_id).first()

    if not user:
        bot.answer_callback_query(call["id"], "❌ User not found. Please use /start first.")
        return

    available = user.balance
    total_recharged = user.total_recharged if hasattr(user, "total_recharged") else 0

    text = (
        "💰 <b>Balance Overview :</b>\n\n"
        f"🪙 <b>Available:</b> {available:.2f} 💎\n"
        f"💳 <b>Total Recharged:</b> {total_recharged} 💎\n\n"
        "~~ Check transaction below."
    )

    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("💳 Recharge", callback_data="recharge"),
        InlineKeyboardButton("💎 Transactions", callback_data="transactions"),
    )
    markup.row(InlineKeyboardButton("« Back", callback_data="back_main"))

    # ✅ use dict keys, not attributes
    safe_edit_message(bot, call, text, markup)


    bot.answer_callback_query(call["id"])
