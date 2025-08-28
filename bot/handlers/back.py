from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from utils.config import get_config
from bot.libs.helpers import safe_edit_message
from models.order import Order

def handle(bot, call):
    """Handles the Back button → return to main menu"""

    user_id = str(call["from"]["id"])
    user = User.objects(telegram_id=user_id).first()

    if not user:
        bot.send_message(call["message"]["chat"]["id"], "❌ User not found. Please use /start first.")
        return

    balance = user.balance
    user_orders = Order.objects(user=user)
    total_purchased = user_orders.count()

    total_used = user_orders.filter(status="completed").count()
    # Get support url from config (dynamic from admin panel)
    support_url = get_config("support_url", "")

    text = (
        f"👋 Hello {call['from'].get('first_name', '')} !\n\n"
        f"💰 Your Balance : {balance:.2f} 💎\n"
        f"📊 Total Numbers Purchased : {total_purchased}\n"
        f"✉️ Total Numbers Used : {total_used}\n\n"
        "<i>~~ You can use this 💎 for purchasing Numbers ..\n"
        "~~ For Support Click on Support below.</i>"
    )

    # Build inline keyboard (same as /start)
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton("🛒 Services", switch_inline_query_current_chat=""),
    )
    markup.row(
        InlineKeyboardButton("💰 Balance", callback_data="balance"),
        InlineKeyboardButton("💳 Recharge", callback_data="recharge")
    )
    markup.row(InlineKeyboardButton("🎟 Use Promocode", callback_data="promo"))
    markup.row(
        InlineKeyboardButton("👤 Profile", callback_data="profile"),
        InlineKeyboardButton("📜 History", callback_data="history")
    )

    if support_url:
        markup.row(InlineKeyboardButton("📞 Support", url=support_url))
    else:
        markup.row(InlineKeyboardButton("📞 Support", callback_data="support"))

    # ✅ Edit back into the main menu
    safe_edit_message(bot, call, text, markup)