import threading
import time
import requests
import datetime
from models.otpPending import OtpPending

bot_instance = None


# Event to signal new OTP
new_otp_event = threading.Event()
lock = threading.Lock()
def otp_worker():
    while True:
        # Wait until there is new OTP

        print("Waiting for new OTP...")
        new_otp_event.wait()
        while True:
            with lock:
                pending_otps = OtpPending.objects()
                if not pending_otps:
                    new_otp_event.clear()
                    break

                for otp in pending_otps:
                    elapsed_time = (datetime.datetime.utcnow() - otp.created_at).total_seconds()
                    if otp.cancelTime and elapsed_time > otp.cancelTime:
                        try:
                            bot_instance.send_message(
                                chat_id=otp.chat_id,
                                text=f"OTP request for {otp.phone} cancelled (timeout)."
                            )
                            url = otp.cancel_url.format(id=otp.order_id)
                            resp = requests.get(url, timeout=5)
                        except Exception as e:
                            print(f"Telegram send failed: {e}")
                            pass
                        otp.delete()
                        continue
                   

                    try:
                        url = otp.url.format(id=otp.order_id)
                        resp = requests.get(url, timeout=5)
                        if otp.responseType == "Text":
                            raw = resp.text
                            status = raw.split(":")[0]
                            print(f"Status: {status}")
                            if status == "STATUS_OK":
                                bot_instance.send_message(
                                    chat_id=otp.chat_id,
                                    text=f"OTP request for {otp.phone} is {raw.split(':')[1]}"
                                )
                                otp.delete()
                        else:
                            res = resp.json()
                            

                            if res.get("status") == "Recieved":
                                sms_list = res.get("sms", [])
                                if sms_list:
                                    code = sms_list[0].get("code")
                                else:
                                    code = None
                                bot_instance.send_message(
                                    chat_id=otp.chat_id,
                                    text=f"OTP request for {otp.phone} is {code}"
                                )
                                otp.delete()
                    except Exception as e:
                        print(f"Error fetching OTP URL {otp.url}: {e}")
                        pass
            time.sleep(5)

def notify_new_otp():
    new_otp_event.set()

def init_worker(bot):
    global bot_instance
    bot_instance = bot
    threading.Thread(target=otp_worker, daemon=True).start()