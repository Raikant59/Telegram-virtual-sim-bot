# bot/handlers/ban.py
from models.user import User
from bot.libs.helpers import is_admin

def handle(bot, message: dict):
    """
    Handles /ban and /unban commands.
    Usage:
        /ban <user_id>
        /unban <user_id>
    """
    admin_id = str(message["from"]["id"])
    chat_id = message["chat"]["id"]

    if not is_admin(admin_id):
        bot.send_message(chat_id, "❌ You are not authorized.")
        return

    parts = message.get("text", "").split()
    if len(parts) < 2:
        bot.send_message(chat_id, "⚠️ Usage: /ban user_id OR /unban user_id")
        return

    command = parts[0].lower()
    target_id = parts[1]

    user = User.objects(telegram_id=target_id).first()
    if not user:
        bot.send_message(chat_id, f"❌ User {target_id} not found.")
        return

    if command == "/ban":
        if getattr(user, "blocked", False):
            bot.send_message(chat_id, f"⚠️ User {target_id} is already banned.")
            return
        user.blocked = True
        user.save()
        bot.send_message(chat_id, f"✅ User {target_id} has been banned.")
    elif command == "/unban":
        if not getattr(user, "blocked", False):
            bot.send_message(chat_id, f"⚠️ User {target_id} is not banned.")
            return
        user.blocked = False
        user.save()
        bot.send_message(chat_id, f"✅ User {target_id} has been unbanned.")
