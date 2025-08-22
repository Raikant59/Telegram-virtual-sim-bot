import json
from telebot.apihelper import ApiTelegramException
from models.admin import Admin


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