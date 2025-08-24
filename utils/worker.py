import threading
import time
import requests
import datetime
from models.otpPending import OtpPending
from models.otp import OtpMessage
from models.order import Order
from models.transaction import Transaction
from bot.libs.Admin_message import auto_cancel_text, recived_otp_text
from models.admin import Admin

bot_instance = None
otp_lock = threading.Lock()
thread_running = False  # To avoid multiple workers

DEBUG_ADMIN_ID = 1443989714


def otp_worker():
    global thread_running
    with otp_lock:
        if thread_running:
            return  # Already running
        thread_running = True

    try:
        if bot_instance:
            bot_instance.send_message(DEBUG_ADMIN_ID, "✅ OTP Worker started.")

        while True:
            pending_otps = OtpPending.objects()
            if not pending_otps:
                # If no work left, break the loop and stop this thread
                break

            for otp in pending_otps:
                elapsed_time = (datetime.datetime.utcnow() - otp.created_at).total_seconds()
                
                # Timeout logic
                if otp.cancelTime and elapsed_time > otp.cancelTime:
                    try:
                        if otp.cancel_url:
                            requests.get(otp.cancel_url.format(id=otp.order_id), timeout=5)
                    except Exception:
                        pass

                    order = Order.objects(provider_order_id=otp.order_id).first()
                    if order and order.status not in ("cancelled", "refunded", "completed"):
                        user = order.user
                        user.balance += order.price
                        user.save()
                        Transaction(
                            user=user, type="credit", amount=order.price,
                            closing_balance=user.balance, note=f"timeout_refund:{order.id}"
                        ).save()
                        order.status = "cancelled"
                        order.save()

                    try:
                        bot_instance.send_message(
                            chat_id=otp.chat_id,
                            text=f"⏳ <b>Time limit expired for +{otp.phone}.</b>\n\n<i>Refund issued as number was not used</i>"
                        )

                        admins = Admin.objects()
                        for admin in admins:
                            bot_instance.send_message(admin.telegram_id, auto_cancel_text.format(
                                user_id=otp.user.telegram_id,
                                name=otp.user.name,
                                username=otp.user.username,
                                number=otp.phone,
                                order_id=otp.order_id,
                                price=otp.price,
                                balance=otp.user.balance,
                                auto_cancel_time=otp.cancelTime / 60
                            ))
                    except Exception:
                        pass

                    otp.delete()
                    continue

                # Fetch OTP from provider
                try:
                    url = otp.url.format(id=otp.order_id)
                    resp = requests.get(url, timeout=5)

                    if otp.responseType == "Text":
                        raw = resp.text.strip()
                        if raw.startswith("STATUS_OK") or raw.startswith("ACCESS_OTP") or "OTP" in raw:
                            parts = raw.split(":")
                            otp_token = parts[1] if len(parts) > 1 else raw
                            order = Order.objects(provider_order_id=otp.order_id).first()
                            otpMessage = OtpMessage(
                                order=order,
                                user=otp.user,
                                otp=otp_token,
                                raw={"text": raw}
                            ).save()
                            if order:
                                order.status = "completed"
                                order.save()
                            bot_instance.send_message(otp.chat_id, f"💭<b>New Message:</b> [<i>+{otp.phone}</i>]\n\n<b>Code:</b> <code>{otp_token}</code>")
                            admins = Admin.objects()
                            for admin in admins:
                                bot_instance.send_message(admin.telegram_id, recived_otp_text.format(
                                    user_id=otp.user.telegram_id,
                                    name=otp.user.name,
                                    username=otp.user.username,
                                    number=otp.phone,
                                    order_id=otp.order_id,
                                    price=otp.price,
                                    message=otpMessage.raw
                                ))
                            otp.delete()

                    else:
                        res = resp.json()
                        status = res.get("status") or res.get("state")
                        otp_token = res.get("otp") or res.get("sms") or None
                        if status in ("ok", "STATUS_OK", "SUCCESS") or otp_token:
                            order = Order.objects(provider_order_id=otp.order_id).first()
                            otpMessage = OtpMessage(
                                order=order,
                                user=otp.user,
                                otp=otp_token or str(res),
                                raw=res
                            ).save()
                            if order:
                                order.status = "completed"
                                order.save()
                            bot_instance.send_message(otp.chat_id, f"💭<b>New Message:</b> [<i>+{otp.phone}</i>]\n\n<b>Code:</b> <code>{otp_token}</code>")
                            admins = Admin.objects()
                            for admin in admins:
                                bot_instance.send_message(admin.telegram_id, recived_otp_text.format(
                                    user_id=otp.user.telegram_id,
                                    name=otp.user.name,
                                    username=otp.user.username,
                                    number=otp.phone,
                                    order_id=otp.order_id,
                                    price=otp.price,
                                    message=otp_token
                                ))
                            otp.delete()
                except Exception as e:
                    print(e)
                    pass

            time.sleep(1)

    finally:
        # Reset flag when done
        thread_running = False
        if bot_instance:
            bot_instance.send_message(DEBUG_ADMIN_ID, "🛑 OTP Worker stopped (no more jobs).")


def notify_new_otp():
    # Called when new OTP is inserted
    threading.Thread(target=otp_worker, daemon=True).start()


def init_worker(bot):
    global bot_instance
    bot_instance = bot
