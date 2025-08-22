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
        bot.send_message(chat_id, "❌ You are not authorized to use this command.")
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
        f"📊 User SMM History → <code>/smm_history {example_id}</code>\n"
        f"⛔ Ban User → <code>/ban {example_id}</code>\n"
        f"✅ Unban User → <code>/unban {example_id}</code>\n"
        f"📢 Broadcast → <code>/broadcast hello everyone</code>\n\n"
        "<i>Remember to replace the example ID with the actual user’s ID.</i>"
    )

    # Inline Mini WebApp buttons
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=f"{FRONTEND_URL}")),
        InlineKeyboardButton("🖥 Servers", web_app=WebAppInfo(url=f"{FRONTEND_URL}/servers")),
    )
    markup.add(
        InlineKeyboardButton("🛒 Services", web_app=WebAppInfo(url=f"{FRONTEND_URL}/services")),
        InlineKeyboardButton("🔌 APIs", web_app=WebAppInfo(url=f"{FRONTEND_URL}/apis")),
    )
    markup.add(
        InlineKeyboardButton("👤 Users", web_app=WebAppInfo(url=f"{FRONTEND_URL}/users"))
    )

    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
