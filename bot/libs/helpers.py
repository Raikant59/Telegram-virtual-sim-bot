import json
from telebot.apihelper import ApiTelegramException
from models.admin import Admin
from models.otp import OtpMessage
from models.user import User

def get_total_user_balance():
    pipeline = [
        {"$group": {"_id": None, "total": {"$sum": "$balance"}}}
    ]
    result = User.objects.aggregate(*pipeline)
    result = list(result)
    return result[0]["total"] if result else 0.0

def build_messages_block(order):
    messages = [m.otp for m in OtpMessage.objects(order=order)]
    if not messages:
        return ""  # no OTPs for this order → don't show block
    
    formatted_msgs = "\n".join([f"{i+1}. {msg}" for i, msg in enumerate(messages)])
    return f"✉️<b>Messages</b>:\n{formatted_msgs}"


def safe_edit_message(bot, call, new_text, new_markup):

    try:
        old_text = call["message"].get("text", "")
        old_markup = call["message"].get("reply_markup")

        # Convert both markups to JSON strings for comparison
        old_markup_json = json.dumps(old_markup, sort_keys=True) if old_markup else None
        new_markup_json = new_markup.to_json() if new_markup else None

        if old_text == new_text and old_markup_json == new_markup_json:
            # Nothing changed → avoid 400 error
            return

        bot.edit_message_text(
            chat_id=call["message"]["chat"]["id"],
            message_id=call["message"]["message_id"],
            text=new_text,
            parse_mode="HTML",
            reply_markup=new_markup
        )
    except Exception:
        pass  

from models.admin import Admin


def is_admin(user_id: str) -> bool:
    return Admin.objects(telegram_id=user_id).first() is not None