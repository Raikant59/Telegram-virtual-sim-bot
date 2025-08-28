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
    data = call["data"].split(":")
    if len(data) != 2:
        bot.send_message(call["message"]["chat"]["id"], "⚠️ Invalid request.")
        return

    provider_order_id = data[1]
    pending_otp = OtpPending.objects(order_id=provider_order_id).first()
    if not pending_otp:
        bot.send_message(call["message"]["chat"]["id"],
                         "❌ Order is already cancelled.")
        return
    
    order = Order.objects(provider_order_id=provider_order_id).first()
    wait_time = (order.created_at + datetime.timedelta(seconds=order.service.disable_time)) - datetime.datetime.utcnow()
    if wait_time.total_seconds() > 0:
        bot.send_message(
            call["message"]["chat"]["id"],
            f"🔴 You can cancel numbers after {int(wait_time.total_seconds())} seconds. Auto refund in 10 minutes."
        )
        return


    # Attempt provider cancel (best-effort)
    try:
        if pending_otp.cancel_url:
            url = pending_otp.cancel_url.format(id=provider_order_id)
            res = requests.get(url, timeout=5)

            if pending_otp.responseType == "Text":
                if not (res.text.strip().startswith("ACCESS_CANCEL")) :
                    bot.send_message(call["message"]["chat"]["id"], "⚠️ We are not able to cancel this request.")
                    return
    except Exception as e:
        # don't fail the flow if provider cancel fails
        bot.send_message(call["message"]["chat"]["id"],
                         "⚠️ We are not able to cancel this request.")
        return

    # Find corresponding Order by provider_order_id and refund if needed
    
        
    isRefund = not OtpMessage.objects(order=order).count() > 0
    user = order.user
    if order and order.status not in ("cancelled", "refunded", "completed"):
        if isRefund:
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

    text = f""

    if isRefund:
        text += "✅ <b>Successfully Cancelled</b>\n<i>+{pending_otp.phone}\n\nWe've also Issued the refund of this service amount, because the number wasnt used</i>"
    else:
        text += "✅ <b>Your Order Successfully</b>\n<i>+{pending_otp.phone}\n\nThere is no refund as the number is used </i>"

    bot.send_message(call["message"]["chat"]["id"], text)
    bot.answer_callback_query(call["id"], "✅ Cancelled.")
    # notify admins
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
        otps = OtpMessage.objects(order=order)  # query all OTPs for the order
        if otps:
            cancel_text2 += "\n💭 Message:"
            for otp in otps:
                if otp.otp:  # make sure otp field is not None
                    cancel_text2 += f"\n{otp.otp}"

    for admin in admins:
        try:
            bot.send_message(admin.telegram_id, cancel_text2)
        except Exception as e:
            print(f"Failed to send to {admin.telegram_id}: {e}")
            pass
    pending_otp.delete()
