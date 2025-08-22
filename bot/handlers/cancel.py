from models.otpPending import OtpPending
import requests
def handle(bot, call):
    data = call["data"].split(":")
    if len(data) != 2:
        bot.answer_callback_query(call["id"], "⚠️ Invalid request.")
        return

    order_id = data[1]
    pending_otp = OtpPending.objects(order_id=order_id).first()
    if not pending_otp:
        bot.answer_callback_query(call["id"], "❌ No pending OTP found.")
        return
    
    url = pending_otp.cancel_url.format(id=order_id)
    try:
        resp = requests.get(url, timeout=5)
        bot.answer_callback_query(call["id"], "✅ Cancelled!")
    except Exception as e:
        bot.answer_callback_query(call["id"], f"❌ Error cancelling OTP: {e}")

    OtpPending.objects(order_id=order_id).delete()
    bot.answer_callback_query(call["id"], "✅ Cancelled!")