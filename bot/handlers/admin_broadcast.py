# bot/handlers/broadcast.py
from models.user import User
from bot.libs.helpers import is_admin
import time

def handle(bot, message: dict):
    """
    Handles /broadcast command.
    Usage:
        /broadcast <your message here>
    """
    admin_id = str(message["from"]["id"])
    chat_id = message["chat"]["id"]

    if not is_admin(admin_id):
        bot.send_message(chat_id, "❌ You are not authorized.")
        return

    parts = message.get("text", "").split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(chat_id, "⚠️ Usage: /broadcast <message>")
        return

    broadcast_msg = parts[1]

    users = User.objects(blocked=False)
    sent_count, failed_count = 0, 0

    bot.send_message(chat_id, f"📢 Starting broadcast to {users.count()} users...")

    for user in users:
        try:
            bot.send_message(user.telegram_id, broadcast_msg)
            sent_count += 1
            time.sleep(0.05)  # prevent hitting Telegram flood limits
        except Exception as e:
            failed_count += 1
            # you may log this error if needed
            continue

    bot.send_message(
        chat_id,
        f"✅ Broadcast finished!\n\n"
        f"📨 Sent: {sent_count}\n"
        f"⚠️ Failed: {failed_count}"
    )
