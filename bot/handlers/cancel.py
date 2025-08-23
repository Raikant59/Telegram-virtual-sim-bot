# bot/handlers/cancel.py
from models.otpPending import OtpPending
from models.order import Order
from models.transaction import Transaction
from models.user import User
import requests
from models.admin import Admin
from bot.libs.Admin_message import cancel_text

def handle(bot, call):
    data = call["data"].split(":")
    if len(data) != 2:
        bot.send_message(call["message"]["chat"]["id"], "⚠️ Invalid request.")
        return

    provider_order_id = data[1]
    pending_otp = OtpPending.objects(order_id=provider_order_id).first()
    if not pending_otp:
        bot.send_message(call["message"]["chat"]["id"], "❌ Order is not active.")
        return

    # Attempt provider cancel (best-effort)
    try:
        if pending_otp.cancel_url:
            url = pending_otp.cancel_url.format(id=provider_order_id)
            requests.get(url, timeout=5)
    except Exception as e:
        # don't fail the flow if provider cancel fails
        bot.send_message(call["message"]["chat"]["id"], "⚠️ Provider cancel failed.")
        return

    # Find corresponding Order by provider_order_id and refund if needed
    order = Order.objects(provider_order_id=provider_order_id).first()
    user = order.user
    if order and order.status not in ("cancelled", "refunded", "completed"):
        
        user.balance += order.price
        user.save()

        Transaction(
            user=user,
            type="credit",
            amount=order.price,
            closing_balance=user.balance,
            note=f"refund:{order.id}"
        ).save()

        order.status = "cancelled"
        order.save()

    user.reload()

    # remove pending otp
    

    bot.send_message(call["message"]["chat"]["id"], f"✅ <b>Successfully Cancelled</b>\n<i>+{pending_otp.phone}\n\nWe've also Issued the refund of this service amount, because the number wasnt used</i>")
    bot.answer_callback_query(call["id"], "✅ Cancelled.")
    # notify admins
    admins = Admin.objects()
    for admin in admins:
        try:
            bot.send_message(admin.telegram_id, cancel_text.format(
                user_id=call["from"]["id"],
                name=call["from"]["first_name"],
                username=call["from"]["username"],
                number=pending_otp.phone,
                order_id=pending_otp.order_id,
                price=pending_otp.price,
                balance=user.balance,
            ))
        except Exception as e:
            pass
        
    pending_otp.delete()