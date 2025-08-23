from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from utils.config import get_config
from dotenv import load_dotenv
import os
from models.order import Order
from models.otp import OtpMessage

load_dotenv()
BOT_URL = os.getenv("BOT_URL")

def handle(bot, message):
    chat_type = message["chat"]["type"]
    chat_id = message["chat"]["id"]

    if chat_type == "private":
        user_id = str(message["from"]["id"])
        username = message["from"].get("username", "")

        # Get or create user
        user = User.objects(telegram_id=user_id).first()


        if not user:
            user = User(telegram_id=user_id, username=username,name=message["from"]["first_name"])
            user.save()
        else:
            user.name = message["from"]["first_name"]
            user.save()

        balance = user.balance

        user_orders = Order.objects(user=user)
        total_purchased = user_orders.count()

        total_used = OtpMessage.objects(user=user).count()

        text = (
            f"👋 Hello {message['from'].get('first_name', '')} !\n\n"
            f"💰 Your Balance : {balance:.2f} 💎\n"
            f"📊 Total Numbers Purchased : {total_purchased}\n"
            f"✉️ Total Numbers Used : {total_used}\n\n"
            "<i>~~ You can use this 💎 for purchasing Numbers ..\n"
            "~~ For Support Click on Support below.</i>"
        )

        # Get dynamic support link (default to BOT_URL if none in DB)
        support_url = get_config("support_url", BOT_URL)

        # Build inline keyboard
        markup = InlineKeyboardMarkup(row_width=2)
        markup.row(InlineKeyboardButton("🛒 Services", switch_inline_query_current_chat=""))
        markup.row(
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
            InlineKeyboardButton("💳 Recharge", callback_data="recharge")
        )
        markup.row(InlineKeyboardButton("🎟 Use Promocode", callback_data="promocode"))
        markup.row(
            InlineKeyboardButton("👤 Profile", callback_data="profile"),
            InlineKeyboardButton("📜 History", callback_data="history")
        )
        markup.row(InlineKeyboardButton("📞 Support", url=support_url))

        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="HTML")

    else:
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("✉️ Send Message", url=BOT_URL))
        bot.send_message(chat_id, "👋 Hello there! To purchase a number please message me personally.", reply_markup=markup, parse_mode="HTML")
