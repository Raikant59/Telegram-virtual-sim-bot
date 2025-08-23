from models.user import User
from models.transaction import Transaction
from bot.libs.helpers import is_admin
from telebot import types

from bot.libs.helpers import safe_edit_message

PAGE_SIZE = 5  # transactions per page

def build_transaction_message(user, page=1):
    """Builds paginated transaction message + inline keyboard"""
    total = Transaction.objects(user=user).count()
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE or 1

    transactions = (
        Transaction.objects(user=user)
        .order_by("-created_at")
        .skip((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )

    if not transactions:
        return "📭 No transactions found.", None

    msg_lines = [f"📄 Page {page} of {pages}"]
    for trnx in transactions:
        if trnx.type == "debit":
            msg_lines.append(
                f"\n📩 <b>debited from wallet {trnx.note}</b>\n"
                f"Amount debited: {trnx.amount:.2f} 💰\n"
                f"Closing balance: {trnx.closing_balance:.2f} 💎\n"
                f"🗓 Created On {trnx.created_at.strftime('%m/%d/%Y, %I:%M:%S %p')}"
            )
        else:
            msg_lines.append(
                f"\n📨 <b>credited to wallet {trnx.note}</b>\n"
                f"Amount credited: {trnx.amount:.2f} 💰\n"
                f"Closing balance: {trnx.closing_balance:.2f} 💎\n"
                f"🗓 Created On {trnx.created_at.strftime('%m/%d/%Y, %I:%M:%S %p')}"
            )

    # build inline keyboard
    kb = types.InlineKeyboardMarkup()
    buttons = []
    if page > 1:
        buttons.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"trnx:{user.telegram_id}:{page-1}"))
    if page < pages:
        buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"trnx:{user.telegram_id}:{page+1}"))
    if buttons:
        kb.row(*buttons)

    return "\n".join(msg_lines), kb


def handle(bot, message: dict):
    user_id = str(message["from"]["id"])
    chat_id = message["chat"]["id"]

    if not is_admin(user_id):
        bot.send_message(chat_id, "❌ You are not authorized.")
        return

    parts = message.get("text", "").split()
    if len(parts) < 2:
        bot.send_message(chat_id, "⚠️ Usage: /trnx user_id")
        return

    target_id = parts[1]
    user = User.objects(telegram_id=target_id).first()
    if not user:
        bot.send_message(chat_id, "❌ User not found.")
        return

    msg, kb = build_transaction_message(user, 1)
    bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=kb)


def handle_callback(bot, call):
    """Handles inline button clicks"""
    data = call["data"].split(":")
    if len(data) != 3:
        return

    _, target_id, page_str = data
    user = User.objects(telegram_id=target_id).first()
    if not user:
        bot.send_message(call["message"]["chat"]["id"], "❌ User not found.")
        return

    page = int(page_str)
    msg, kb = build_transaction_message(user, page)

    bot.edit_message_text(
        msg,
        chat_id=call["message"]["chat"]["id"],
        message_id=call["message"]["message_id"],
        parse_mode="HTML",
        reply_markup=kb
    )
