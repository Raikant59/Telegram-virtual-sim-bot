import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from bot.libs.helpers import is_admin
from dotenv import load_dotenv

load_dotenv()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5000/admin")


def handle(bot, message):
    user_id = str(message["from"]["id"])
    chat_id = message["chat"]["id"]

    if not is_admin(user_id):
        bot.send_message(
            chat_id, "❌ You are not authorized to use this command.")
        return

    # Example user ID
    example_id = "1980442239"

    text = (
        f"👋 Hello @{message['from'].get('username', '') or 'Admin'}\n\n"
        "⚙️ <b>Admin Commands:</b>\n\n"
        f"➕ Add Balance → <code>/add {example_id} 100</code>\n"
        f"➖ Cut Balance → <code>/cut {example_id} 100</code>\n"
        f"📜 User Transactions → <code>/trnx {example_id}</code>\n"
        f"📱 User Number History → <code>/nums {example_id}</code>\n"
        f"⛔ Ban User → <code>/ban {example_id}</code>\n"
        f"✅ Unban User → <code>/unban {example_id}</code>\n"
        f"📢 Broadcast → <code>/broadcast hello everyone</code>\n\n"
        "<i>Remember to replace the example ID with the actual user’s ID.</i>"
    )

    # Inline Mini WebApp buttons
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(
            "Dashboard", web_app=WebAppInfo(url=f"{FRONTEND_URL}")),
        InlineKeyboardButton("Users", web_app=WebAppInfo(
            url=f"{FRONTEND_URL}/users")),
    )
    markup.add(
        InlineKeyboardButton("Add Server", web_app=WebAppInfo(
            url=f"{FRONTEND_URL}/servers")),
        InlineKeyboardButton("Add Service", web_app=WebAppInfo(
            url=f"{FRONTEND_URL}/services")),
    )
    markup.add(
        InlineKeyboardButton("Connect API", web_app=WebAppInfo(
            url=f"{FRONTEND_URL}/apis")),
        InlineKeyboardButton("Edit Bot Settings", web_app=WebAppInfo(
            url=f"{FRONTEND_URL}/bot_settings")),
    )
    markup.add(
        InlineKeyboardButton("Promo Codes", web_app=WebAppInfo(
            url=f"{FRONTEND_URL}/promos")),
    )
    markup.add(
        InlineKeyboardButton("Payment Gateways", web_app=WebAppInfo(
            url=f"{FRONTEND_URL}/payments")),
        InlineKeyboardButton("Recharges", web_app=WebAppInfo(
            url=f"{FRONTEND_URL}/recharges")),
    )
    

    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
