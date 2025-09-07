# bot/handlers/numbers.py
from telebot import types
from models.user import User
from models.order import Order
from models.otp import OtpMessage
from bot.libs.helpers import is_admin

PAGE_SIZE = 5  # orders per page


def format_order(order):
    """Format one order with OTPs/messages."""
    otps = OtpMessage.objects(order=order).order_by("created_at")
    lines = []
    lines.append(f"📅 Bought On: {order.created_at.strftime('%m/%d/%Y, %I:%M:%S %p')}")
    lines.append(f"💳 Price: {order.price:.2f}")
    lines.append(f"📞 Number: {order.number}")
    lines.append(f"🆔 Order ID: {order.id}")
    if not otps:
        lines.append(f"📌 <b>Status:</b> {order.status.capitalize()}")
    else:
        lines.append(f"📌 <b>Status:</b> Completed")
    lines.append(f"⚜️ <b>Service:</b> {order.service.name}")
    lines.append(f"🔅 <b>Server:</b> {order.server.name}")

    # OTP messages (if any)
    if not otps:
        lines.append("✉️ Messages: No OTP received")
    else:
        lines.append("✉️ Messages:")
        for i, otp in enumerate(otps, start=1):
            lines.append(f"{i}️⃣ {otp.otp}")

    return "\n".join(lines)


def build_numbers_message(user, page=1):
    """Builds paginated order history message + inline keyboard"""
    total = Order.objects(user=user).count()
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE or 1

    orders = (
        Order.objects(user=user)
        .order_by("-created_at")
        .skip((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )

    if not orders:
        return "📭 No orders found for this user.", None

    msg_lines = [f"📖 <b>Orders for {user.telegram_id}</b> — Page {page} of {pages}\n"]
    for order in orders:
        msg_lines.append(format_order(order))
        msg_lines.append("─" * 23)

    # build inline keyboard
    kb = types.InlineKeyboardMarkup()

    # --- Row 1: page numbers ---
    num_row = []
    if page > 1:
        num_row.append(types.InlineKeyboardButton(str(page - 1), callback_data=f"nums:{user.telegram_id}:{page-1}"))

    num_row.append(types.InlineKeyboardButton(f"[ {page} ]", callback_data="noop"))

    if page < pages:
        num_row.append(types.InlineKeyboardButton(str(page + 1), callback_data=f"nums:{user.telegram_id}:{page+1}"))

    kb.row(*num_row)

    # --- Row 2: Prev/Next ---
    nav_row = []
    if page > 1:
        nav_row.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"nums:{user.telegram_id}:{page-1}"))
    if page < pages:
        nav_row.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"nums:{user.telegram_id}:{page+1}"))

    if nav_row:
        kb.row(*nav_row)

    return "\n".join(msg_lines), kb


def handle(bot, message: dict):
    """Handles the /nums userid command"""
    user_id = str(message["from"]["id"])
    chat_id = message["chat"]["id"]

    if not is_admin(user_id):
        bot.send_message(chat_id, "❌ You are not authorized.")
        return

    parts = message.get("text", "").split()
    if len(parts) < 2:
        bot.send_message(chat_id, "⚠️ Usage: /nums user_id")
        return

    target_id = parts[1]
    user = User.objects(telegram_id=target_id).first()
    if not user:
        bot.send_message(chat_id, "❌ User not found.")
        return

    msg, kb = build_numbers_message(user, 1)
    bot.send_message(chat_id, msg, parse_mode="HTML", reply_markup=kb)


def handle_callback(bot, call):
    """Handles inline button clicks for /nums"""
    data = call["data"].split(":")
    if len(data) != 3:
        return

    _, target_id, page_str = data
    user = User.objects(telegram_id=target_id).first()
    if not user:
        bot.send_message(call["message"]["chat"]["id"], "❌ User not found.")
        return

    try:
        page = int(page_str)
    except Exception:
        page = 1

    msg, kb = build_numbers_message(user, page)
    bot.edit_message_text(
        msg,
        chat_id=call["message"]["chat"]["id"],
        message_id=call["message"]["message_id"],
        parse_mode="HTML",
        reply_markup=kb
    )
