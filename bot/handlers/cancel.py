# bot/handlers/cancel.py
from models.otpPending import OtpPending
from models.order import Order
from models.transaction import Transaction
from models.user import User
import requests

def handle(bot, call):
    data = call["data"].split(":")
    if len(data) != 2:
        bot.answer_callback_query(call["id"], "⚠️ Invalid request.")
        return

    provider_order_id = data[1]
    pending_otp = OtpPending.objects(order_id=provider_order_id).first()
    if not pending_otp:
        bot.answer_callback_query(call["id"], "❌ No pending OTP found.")
        return

    # Attempt provider cancel (best-effort)
    try:
        if pending_otp.cancel_url:
            url = pending_otp.cancel_url.format(id=provider_order_id)
            requests.get(url, timeout=5)
    except Exception as e:
        # don't fail the flow if provider cancel fails
        pass

    # Find corresponding Order by provider_order_id and refund if needed
    order = Order.objects(provider_order_id=provider_order_id).first()
    if order and order.status not in ("cancelled", "refunded"):
        user = order.user
        # Credit back the amount
        user.balance += order.price
        user.save()

        # Record transaction (credit)
        Transaction(
            user=user,
            type="credit",
            amount=order.price,
            closing_balance=user.balance,
            note=f"refund:{order.id}"
        ).save()

        order.status = "cancelled"
        order.save()

    # remove pending otp
    pending_otp.delete()

    bot.answer_callback_query(call["id"], "✅ Cancelled and refunded (if applicable).")
