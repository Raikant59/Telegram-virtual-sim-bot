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
                break  # Stop if no jobs

            for otp in pending_otps:
                elapsed_time = (datetime.datetime.utcnow() - otp.created_at).total_seconds()

                # =====================
                # Timeout / Auto-cancel
                # =====================
                if otp.cancelTime and elapsed_time > otp.cancelTime:
                    try:
                        if otp.cancel_url:
                            requests.get(otp.cancel_url.format(id=otp.order_id), timeout=5)
                    except Exception:
                        pass

                    order = Order.objects(provider_order_id=otp.order_id).first()
                    if not order:
                        otp.delete()
                        continue

                    # Refund only if NO OTP message exists
                    has_message = OtpMessage.objects(order=order).count() > 0
                    isRefund = not has_message

                    if order.status not in ("cancelled", "refunded", "completed"):
                        user = order.user
                        if isRefund:
                            user.balance += order.price
                            user.save()
                            Transaction(
                                user=user,
                                type="credit",
                                amount=order.price,
                                closing_balance=user.balance,
                                note=f"timeout_refund:{order.id}"
                            ).save()
                            order.status = "refunded"
                        else:
                            order.status = "cancelled"
                        order.save()

                    try:
                        if isRefund:
                            text = f"⏳ <b>Time limit expired for +{otp.phone}.</b>\n<i>You have been refunded {order.price} 💎</i>"
                        else:
                            text = f"⏳ <b>Time limit expired for +{otp.phone}.</b>\n<i>No refund was issued.</i>"

                        bot_instance.send_message(chat_id=otp.chat_id, text=text)

                        admins = Admin.objects()
                        for admin in admins:
                            bot_instance.send_message(
                                admin.telegram_id,
                                auto_cancel_text.format(
                                    user_id=otp.user.telegram_id,
                                    name=otp.user.name,
                                    username=otp.user.username,
                                    number=otp.phone,
                                    order_id=otp.order_id,
                                    price=otp.price,
                                    balance=otp.user.balance,
                                    auto_cancel_time=otp.cancelTime / 60,
                                    refund="Refund issued" if isRefund else "No refund"
                                )
                            )
                    except Exception:
                        pass

                    otp.delete()
                    continue

                # =====================
                # Fetch OTP
                # =====================
                try:
                    url = otp.url.format(id=otp.order_id)
                    resp = requests.get(url, timeout=5)

                    otp_token = None
                    is_new = False
                    order = Order.objects(provider_order_id=otp.order_id).first()
                    if not order:
                        otp.delete()
                        continue

                    if otp.responseType == "Text":
                        raw = resp.text.strip()
                        if raw.startswith("STATUS_OK") or raw.startswith("ACCESS_OTP") or "OTP" in raw:
                            parts = raw.split(":")
                            otp_token = parts[1] if len(parts) > 1 else raw

                            # Avoid duplicate OTPs
                            is_new = not OtpMessage.objects(order=order, otp=otp_token).first()

                            if is_new:
                                otpMessage = OtpMessage(
                                    order=order,
                                    user=otp.user,
                                    otp=otp_token,
                                    raw={"text": raw}
                                ).save()

                                bot_instance.send_message(
                                    otp.chat_id,
                                    f"💭 <b>New Message:</b> [<i>+{otp.phone}</i>]\n\n<b>Code:</b> <code>{otp_token}</code>"
                                )

                                try:
                                    if otp.next_otp_url:
                                        requests.get(otp.next_otp_url.format(id=otp.order_id), timeout=5)
                                except:
                                    pass

                                admins = Admin.objects()
                                for admin in admins:
                                    bot_instance.send_message(
                                        admin.telegram_id,
                                        recived_otp_text.format(
                                            user_id=otp.user.telegram_id,
                                            name=otp.user.name,
                                            username=otp.user.username,
                                            number=otp.phone,
                                            order_id=otp.order_id,
                                            price=otp.price,
                                            message=otp_token
                                        )
                                    )

                    else:
                        res = resp.json()
                        status = res.get("status") or res.get("state")
                        otp_token = res.get("otp") or res.get("sms")

                        if status in ("ok", "STATUS_OK", "SUCCESS") or otp_token:
                            otp_token = otp_token if isinstance(otp_token, str) else str(otp_token)

                            # Avoid duplicates
                            is_new = not OtpMessage.objects(order=order, otp=otp_token).first()

                            if is_new:
                                otpMessage = OtpMessage(
                                    order=order,
                                    user=otp.user,
                                    otp=otp_token,
                                    raw=res
                                ).save()

                                bot_instance.send_message(
                                    otp.chat_id,
                                    f"💭 <b>New Message:</b> [<i>+{otp.phone}</i>]\n\n<b>Code:</b> <code>{otp_token}</code>"
                                )

                                try:
                                    if otp.next_otp_url:
                                        requests.get(otp.next_otp_url.format(id=otp.order_id), timeout=5)
                                except:
                                    pass

                                admins = Admin.objects()
                                for admin in admins:
                                    bot_instance.send_message(
                                        admin.telegram_id,
                                        recived_otp_text.format(
                                            user_id=otp.user.telegram_id,
                                            name=otp.user.name,
                                            username=otp.user.username,
                                            number=otp.phone,
                                            order_id=otp.order_id,
                                            price=otp.price,
                                            message=otp_token
                                        )
                                    )

                except Exception as e:
                    print("Fetch OTP Error:", e)
                    pass

            time.sleep(1)

    finally:
        thread_running = False
        if bot_instance:
            bot_instance.send_message(DEBUG_ADMIN_ID, "🛑 OTP Worker stopped (no more jobs).")


def notify_new_otp():
    threading.Thread(target=otp_worker, daemon=True).start()


def init_worker(bot):
    global bot_instance
    bot_instance = bot
