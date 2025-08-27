# bot/handlers/cancel.py
from models.otpPending import OtpPending
from models.order import Order
from models.transaction import Transaction
from models.user import User
import requests
from models.admin import Admin
from bot.libs.Admin_message import cancel_text
from models.otp import OtpMessage
import datetime


def handle(bot, call):
    from mongoengine.queryset.visitor import Q  # For atomic filters

    data = call["data"].split(":")
    if len(data) != 2:
        bot.send_message(call["message"]["chat"]["id"], "⚠️ Invalid request.")
        return

    provider_order_id = data[1]

    # Claim pending_otp first
    pending_otp = OtpPending.objects(order_id=provider_order_id).first()
    if not pending_otp:
        bot.send_message(call["message"]["chat"]["id"], "❌ Order is already cancelled.")
        return

    order = Order.objects(provider_order_id=provider_order_id).first()
    if not order:
        bot.send_message(call["message"]["chat"]["id"], "⚠️ Order not found.")
        return

    # Wait lock
    wait_time = (order.created_at + datetime.timedelta(seconds=order.service.disable_time)) - datetime.datetime.utcnow()
    if wait_time.total_seconds() > 0:
        bot.send_message(
            call["message"]["chat"]["id"],
            f"🔴 You can cancel numbers after {int(wait_time.total_seconds())} seconds. Auto refund in 10 minutes."
        )
        return

    # Attempt provider cancel
    try:
        if pending_otp.cancel_url:
            url = pending_otp.cancel_url.format(id=provider_order_id)
            requests.get(url, timeout=5)
    except Exception:
        bot.send_message(call["message"]["chat"]["id"], "⚠️ We are not able to cancel this request.")
        return

    # RELOAD order and check if still pending
    order.reload()

    user = order.user
    has_otp = OtpMessage.objects(order=order).count() > 0
    isRefund = not has_otp

    # Try atomic status update (only if still pending)
    updated = Order.objects(
        Q(id=order.id) & Q(status="pending")
    ).update_one(set__status="cancelled")

    if updated:
        if isRefund:
            # Perform refund
            user.update(inc__balance=order.price)
            user.reload()  # Get updated balance

            Transaction(
                user=user,
                type="credit",
                amount=order.price,
                closing_balance=user.balance,
                note=f"refund:{order.id}"
            ).save()
    else:
        # Already cancelled/refunded/completed — no action
        isRefund = False
        order.reload()

    # Clean up
    text = f"✅ <b>Successfully Cancelled</b>\n<i>+{pending_otp.phone}\n\n"
    if isRefund:
        text += "We've also issued the refund of this service amount, because the number wasn't used.</i>"
    else:
        text += "There is no refund as the number was used or already cancelled.</i>"

    bot.send_message(call["message"]["chat"]["id"], text)
    bot.answer_callback_query(call["id"], "✅ Cancelled.")

    # Notify admins
    admins = Admin.objects()
    cancel_text2 = cancel_text.format(
        user_id=call["from"]["id"],
        name=call["from"].get("first_name", "Unknown"),
        username=call["from"].get("username", "N/A"),
        number=pending_otp.phone,
        order_id=pending_otp.order_id,
        price=pending_otp.price,
        balance=user.balance,
        refund="Refund issued" if isRefund else "Refund not issued"
    )

    if not isRefund:
        otps = OtpMessage.objects(order=order)
        if otps:
            cancel_text2 += "\n💭 Message:"
            for otp in otps:
                if otp.otp:
                    cancel_text2 += f"\n{otp.otp}"

    for admin in admins:
        try:
            bot.send_message(admin.telegram_id, cancel_text2)
        except Exception as e:
            print(f"Failed to notify {admin.telegram_id}: {e}")

    pending_otp.delete()
