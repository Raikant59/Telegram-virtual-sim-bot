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


# Event to signal new OTP
new_otp_event = threading.Event()
lock = threading.Lock()


def otp_worker():
    while True:
        print("Waiting for new OTP...")
        new_otp_event.wait()
        while True:
            with lock:
                pending_otps = OtpPending.objects()
                if not pending_otps:
                    new_otp_event.clear()
                    break

                for otp in pending_otps:
                    elapsed_time = (datetime.datetime.utcnow() -
                                    otp.created_at).total_seconds()
                    # Timeout: cancel at provider and refund user/order
                    if otp.cancelTime and elapsed_time > otp.cancelTime:
                        try:
                            # provider cancel (best-effort)
                            if otp.cancel_url:
                                url = otp.cancel_url.format(id=otp.order_id)
                                requests.get(url, timeout=5)
                        except Exception as e:
                            pass

                        # Refund logic (if linked order exists)
                        order = Order.objects(
                            provider_order_id=otp.order_id).first()
                        if order and order.status not in ("cancelled", "refunded", "completed"):
                            user = order.user
                            user.balance += order.price
                            user.save()
                            Transaction(
                                user=user,
                                type="credit",
                                amount=order.price,
                                closing_balance=user.balance,
                                note=f"timeout_refund:{order.id}"
                            ).save()
                            order.status = "cancelled"
                            order.save()

                        try:
                            bot_instance.send_message(
                                chat_id=otp.chat_id,
                                text=f"⏳ <b>Time limit expired for +{otp.phone}.</b>\n\n<i>We've also Issued the refund of this service amount, because the number wasnt used</i>"
                            )

                            # notify admins
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
                        except Exception as e:
                            print(e)
                            pass

                        otp.delete()
                        continue

                    # Poll the provider status URL
                    try:
                        url = otp.url.format(id=otp.order_id)
                        resp = requests.get(url, timeout=5)
                        if otp.responseType == "Text":
                            raw = resp.text.strip()
                            # Expected format could be: STATUS_OK:OTP or STATUS:...
                            if raw.startswith("STATUS_OK") or raw.startswith("ACCESS_OTP") or "OTP" in raw:
                                # heuristics to extract OTP token
                                parts = raw.split(":")
                                otp_token = parts[1] if len(parts) > 1 else raw
                                # Save OTP to DB
                                order = Order.objects(
                                    provider_order_id=otp.order_id).first()
                                otpMessage = OtpMessage(
                                    order=order,
                                    user=otp.user if hasattr(
                                        otp, "user") else None,
                                    otp=otp_token,
                                    raw={"text": raw}
                                ).save()

                                # update order status
                                if order:
                                    order.status = "completed"
                                    order.save()

                                try:

                                    # notify user chat
                                    bot_instance.send_message(
                                        chat_id=otp.chat_id,
                                        text=f"💭<b>New Message:</b> [<i>+{otp.phone}</i>]\n\n<b>Code:</b> <code>{otp_token}</code>"
                                    )

                                    for admin in admins:
                                        bot_instance.send_message(admin.telegram_id, recived_otp_text.format(
                                            user_id=otp.user.telegram_id,
                                            name=otp.user.name,
                                            username=otp.user.username,
                                            number=otp.phone,
                                            order_id=otp.order_id,
                                            price=otp.price,
                                            message=otpMessage.raw,
                                        ))
                                    otp.delete()
                                except Exception as e:
                                    print(e)
                                    pass
                        else:
                            res = resp.json()
                            # Provider-specific: check for status/otp fields
                            status = res.get("status") or res.get("state")
                            otp_token = res.get(
                                "otp") or res.get("sms") or None
                            if status in ("ok", "STATUS_OK", "SUCCESS") or otp_token:
                                # Save OTP message
                                order = Order.objects(
                                    provider_order_id=otp.order_id).first()
                                otpMessage = OtpMessage(
                                    order=order,
                                    user=otp.user if hasattr(
                                        otp, "user") else None,
                                    otp=otp_token or str(res),
                                    raw=res
                                ).save()

                                if order:
                                    order.status = "completed"
                                    order.save()

                                try:

                                    bot_instance.send_message(
                                        chat_id=otp.chat_id,
                                        text=f"💭<b>New Message:</b> [<i>+{otp.phone}</i>]\n\n<b>Code:</b> <code>{otp_token}</code>"
                                    )

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
                                except Exception as e:
                                    print(e)
                                    pass

                                otp.delete()
                    except Exception as e:
                        # ignore transient polling failures
                        print(e)
                        pass
            # small sleep to avoid tight loop
            time.sleep(1)


def notify_new_otp():
    new_otp_event.set()


def init_worker(bot):
    global bot_instance
    bot_instance = bot
    threading.Thread(target=otp_worker, daemon=True).start()
