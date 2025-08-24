# bot/handlers/transactions.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from models.transaction import Transaction
from bot.libs.helpers import safe_edit_message

PAGE_SIZE = 5  # items per page

def build_transaction_message(user, page=1):
    total = Transaction.objects(user=user).count()
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE or 1

    transactions = Transaction.objects(user=user) \
        .order_by("-created_at") \
        .skip((page - 1) * PAGE_SIZE) \
        .limit(PAGE_SIZE)

    if not transactions:
        return "📭 No transactions found.", None

    lines = [f"📄 <b>Transactions — Page {page} of {pages}</b>\n"]
    for t in transactions:
        when = t.created_at.strftime("%Y-%m-%d %I:%M %p")
        if t.type == "debit":
            lines.append(
                f"📩 <b>Debited</b> — {t.note or '-'}\n"
                f"Amount: -{t.amount:.2f} 💎\n"
                f"Closing balance: {t.closing_balance:.2f} 💰\n"
                f"🗓 {when}"
            )
        else:
            lines.append(
                f"📨 <b>Credited</b> — {t.note or '-'}\n"
                f"Amount: +{t.amount:.2f} 💎\n"
                f"Closing balance: {t.closing_balance:.2f} 💰\n"
                f"🗓 {when}"
            )

    # inline keyboard for pagination
    kb = InlineKeyboardMarkup()
    btns = []
    if page > 1:
        btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"transactions:{page-1}"))
    if page < pages:
        btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"transactions:{page+1}"))
    if btns:
        kb.row(*btns)

    # add a back button to main menu
    kb.row(InlineKeyboardButton("« Back", callback_data="back_main"))
    return "\n\n".join(lines), kb


def handle(bot, call):
    """
    Called for callback_query where callback_data starts with "transactions".
    data can be "transactions" (open page 1) or "transactions:<page>"
    """
    data = call.get("data", "") or ""
    parts = data.split(":", 1)
    page = 1
    if len(parts) > 1:
        try:
            page = int(parts[1])
            if page < 1: page = 1
        except Exception:
            page = 1

    user = User.objects(telegram_id=str(call["from"]["id"])).first()
    if not user:
        bot.answer_callback_query(call["id"], "❌ User not found.")
        return

    msg, kb = build_transaction_message(user, page)
    # Reuse safe_edit_message so we don't spam chat or raise edit errors
    safe_edit_message(bot, call, msg, kb)
    bot.answer_callback_query(call["id"])
