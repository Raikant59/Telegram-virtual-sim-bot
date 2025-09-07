# bot/handlers/history.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from models.order import Order
from models.otp import OtpMessage
from bot.libs.helpers import safe_edit_message

PAGE_SIZE = 3  # orders per page


def format_order(order):
    """Format a single order with OTP/messages."""
    lines = []
    otps = OtpMessage.objects(order=order).order_by("created_at")
    when = order.created_at.strftime("%Y-%m-%d %I:%M %p")
    lines.append(f"📅 <b>Date:</b> {when}")
    lines.append(f"💳 <b>Price:</b> {order.price:.2f}")
    lines.append(f"📞 <b>Number:</b> {order.number}")
    lines.append(f"🆔 <b>Order ID:</b> {order.id}")
    if not otps:
        lines.append(f"📌 <b>Status:</b> {order.status.capitalize()}")
    else:
        lines.append(f"📌 <b>Status:</b> Completed")
    lines.append(f"⚜️ <b>Service:</b> {order.service.name}")
    lines.append(f"🔅 <b>Server:</b> {order.server.name}")
    # if hasattr(order, "refund"):
    #     lines.append(f"💰 <b>Refund:</b> {order.refund}")
    # else:
    #     lines.append(f"💰 <b>Refund:</b> N/A")

    # OTP messages
    if not otps:
        lines.append("✉️ <b>Messages:</b> No OTP received")
    else:
        lines.append("✉️ <b>Messages:</b>")
        for i, otp in enumerate(otps, start=1):
            lines.append(f"{i}️⃣ {otp.otp}")

    return "\n".join(lines)


def build_history_message(user, page=1):
    """Build paginated history message + inline keyboard."""
    total = Order.objects(user=user).count()
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE or 1

    orders = Order.objects(user=user) \
        .order_by("-created_at") \
        .skip((page - 1) * PAGE_SIZE) \
        .limit(PAGE_SIZE)

    if not orders:
        return "📭 No order history found.", None

    lines = [f"📖 <b>Order History — Page {page} of {pages}</b>\n"]
    for o in orders:
        lines.append(format_order(o))
        lines.append("─" * 23)

    # Pagination buttons
    kb = InlineKeyboardMarkup()
    btns = []
    if page > 1:
        btns.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"history:{page-1}"))
    if page < pages:
        btns.append(InlineKeyboardButton("Next ➡️", callback_data=f"history:{page+1}"))
    if btns:
        kb.row(*btns)

    kb.row(InlineKeyboardButton("« Back", callback_data="back_main"))
    return "\n".join(lines), kb


def handle(bot, call):
    """
    Called for callback_query where callback_data starts with "history".
    data can be "history" (open page 1) or "history:<page>"
    """
    data = call.get("data", "") or ""
    parts = data.split(":", 1)
    page = 1
    if len(parts) > 1:
        try:
            page = int(parts[1])
            if page < 1:
                page = 1
        except Exception:
            page = 1

    user = User.objects(telegram_id=str(call["from"]["id"])).first()
    if not user:
        bot.answer_callback_query(call["id"], "❌ User not found.")
        return

    msg, kb = build_history_message(user, page)
    safe_edit_message(bot, call, msg, kb)
    bot.answer_callback_query(call["id"])
