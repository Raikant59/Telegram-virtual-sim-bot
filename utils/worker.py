# utils/worker.py
"""
RQ-based OTP worker for the virtual-sim bot.

Features:
- Use Redis + RQ for job queueing.
- Each job processes a single OtpPending (by id).
- Uses a Redis lock per otp to avoid concurrent processing across processes.
- Re-enqueues itself with a short delay if OTP not yet available.
- Handles auto-cancel/refund logic.
- Catches NotUniqueError for OtpMessage.save() to avoid duplicates.

Requirements:
- redis server running
- pip install rq redis
- In production start an RQ worker:
    REDIS_URL=redis://localhost:6379 rq worker -u redis://localhost:6379 default
  Make sure PYTHONPATH includes your project so `utils.worker` is importable.

How to use:
- In your web code, call `notify_new_otp(str(otp_pending.id))` when you create a new OtpPending.
  Your existing call to init_worker(bot) is optional (keeps a reference to bot token),
  but RQ worker processes will create their own TeleBot from BOT_TOKEN env variable.
"""

import os
import time
import datetime
from datetime import timedelta
from typing import Optional

import redis
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError

from telebot import TeleBot
from mongoengine.errors import NotUniqueError
import requests

# Import your models (adjust paths if needed)
from models.otpPending import OtpPending
from models.otp import OtpMessage
from models.order import Order
from models.transaction import Transaction
from models.admin import Admin

# environment / defaults
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BOT_TOKEN = os.getenv("BOT_TOKEN")  # RQ worker processes will read this env directly
DEFAULT_QUEUE_NAME = os.getenv("RQ_QUEUE", "default")

# connect to redis
_redis = redis.from_url(REDIS_URL, decode_responses=True)
queue = Queue(DEFAULT_QUEUE_NAME, connection=_redis)

# lock settings
LOCK_PREFIX = "otp-lock:" 
LOCK_TIMEOUT = int(os.getenv("OTP_LOCK_TIMEOUT", "30"))  # seconds; lock expiry safety

# debug admin (optional)
try:
    DEBUG_ADMIN_ID = int(os.getenv("DEBUG_ADMIN_ID", "1443989714"))
except Exception:
    DEBUG_ADMIN_ID = None


def init_worker(bot: Optional[TeleBot] = None):
    """
    Called by web app on startup if you want (optional).
    Does NOT start any background threads. Just records BOT_TOKEN if bot instance provided.
    The RQ worker should be started separately (see README in header).
    """
    global BOT_TOKEN
    if bot is not None:
        # telebot.TeleBot stores token on .token (private), but safer to keep env based.
        # If token provided via TeleBot instance, prefer it:
        try:
            token = getattr(bot, "token", None)
            if token:
                BOT_TOKEN = token
                os.environ["BOT_TOKEN"] = token
        except Exception:
            pass

    # Ensure Redis is reachable
    try:
        _redis.ping()
    except Exception as e:
        # If Redis unavailable, log (Flask will show)
        print("WARN: Redis not reachable in init_worker:", e)


def notify_new_otp(otp_pending_id: str, delay_seconds: int = 0):
    """
    Enqueue a job to process a single OtpPending.
    - otp_pending_id: string id of OtpPending document
    - delay_seconds: schedule after N seconds (0 => immediate)
    """
    if not otp_pending_id:
        return None

    if delay_seconds and delay_seconds > 0:
        return queue.enqueue_in(timedelta(seconds=delay_seconds), process_otp, otp_pending_id)
    else:
        return queue.enqueue(process_otp, otp_pending_id)


def _get_telebot() -> TeleBot:
    """
    Create a TeleBot instance in worker process. RQ worker processes MUST have BOT_TOKEN
    available in env (or init_worker set it).
    """
    token = os.getenv("BOT_TOKEN", BOT_TOKEN)
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment for worker process")
    return TeleBot(token, parse_mode="HTML")


def _acquire_lock(otp_id: str):
    """
    Acquire a redis lock for this otp id. Non-blocking: returns Lock object or None.
    """
    lock_name = LOCK_PREFIX + str(otp_id)
    lock = _redis.lock(lock_name, timeout=LOCK_TIMEOUT)
    have = lock.acquire(blocking=False)
    if have:
        return lock
    else:
        return None


def process_otp(otp_pending_id: str):
    """
    Main job: process a single OtpPending.
    Behavior:
      - Acquire Redis lock for this otp id. If can't acquire, return (another worker is processing).
      - Load OtpPending doc. If missing, nothing to do.
      - If timed out -> perform cancel/refund flow (same as original logic).
      - Try to fetch OTP from provider URL. If found -> save OtpMessage (catch NotUniqueError) and send messages.
      - If no OTP yet and not timed out -> re-enqueue this job with small delay (e.g. 5s).
    """
    lock = None
    try:
        # Try to acquire lock for this otp id
        lock = _acquire_lock(otp_pending_id)
        if not lock:
            # someone else processing; exit
            return

        # Load fresh doc
        otp = OtpPending.objects(id=otp_pending_id).first()
        if not otp:
            return

        # create bot for sending messages
        bot = _get_telebot()

        now = datetime.datetime.utcnow()
        elapsed_time = (now - otp.created_at).total_seconds() if otp.created_at else 0

        # =====================
        # Timeout / Auto-cancel
        # =====================
        if otp.cancelTime and elapsed_time > otp.cancelTime:
            # Call cancel_url if present (best-effort)
            try:
                if otp.cancel_url:
                    # keep timeout short
                    requests.get(otp.cancel_url.format(id=otp.order_id), timeout=5)
            except Exception:
                pass

            order = Order.objects(provider_order_id=otp.order_id).first()
            if not order:
                # cleanup pending
                otp.delete()
                return

            # Refund only if NO OTP message exists
            has_message = OtpMessage.objects(order=order).count() > 0
            isRefund = not has_message

            # Only update order if not already terminal
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

                # send to user
                try:
                    bot.send_message(chat_id=otp.chat_id, text=text)
                except Exception:
                    pass

                # notify admins
                admins = Admin.objects()
                for admin in admins:
                    try:
                        bot.send_message(
                            admin.telegram_id,
                            f"Auto-cancel: user={otp.user.telegram_id} name={otp.user.name} number={otp.phone} order={otp.order_id} refund={'yes' if isRefund else 'no'}"
                        )
                    except Exception:
                        pass
            except Exception:
                pass

            # cleanup
            otp.delete()
            return

        # =====================
        # Fetch / parse OTP
        # =====================
        try:
            url = otp.url.format(id=otp.order_id)
            resp = requests.get(url, timeout=5)
        except Exception as e:
            # provider fetch error -> re-enqueue after small delay
            # (network blip)
            notify_new_otp(str(otp.id), delay_seconds=5)
            return

        otp_token = None
        is_new = False
        order = Order.objects(provider_order_id=otp.order_id).first()
        if not order:
            otp.delete()
            return

        # parse response (text or json)
        try:
            if otp.responseType == "Text":
                raw = (resp.text or "").strip()
                if raw.startswith("STATUS_OK") or raw.startswith("ACCESS_OTP") or "OTP" in raw or ":" in raw:
                    # try conservative parsing
                    parts = raw.split(":")
                    otp_token = parts[1].strip() if len(parts) > 1 else raw
            else:
                # JSON-like
                try:
                    res = resp.json() if hasattr(resp, "json") else {}
                except Exception:
                    res = {}
                status = (res.get("status") or res.get("state") or "").upper() if isinstance(res, dict) else ""
                otp_token = res.get("otp") or res.get("sms") if isinstance(res, dict) else otp_token
                if status in ("OK", "STATUS_OK", "SUCCESS") or otp_token:
                    otp_token = str(otp_token)
        except Exception:
            otp_token = None

        if not otp_token:
            # no OTP yet -> re-enqueue later (unless close to timeout)
            # schedule next check at 5s (or less, if remaining time < 5s)
            next_delay = 5
            if otp.cancelTime:
                remaining = otp.cancelTime - elapsed_time
                if remaining <= 0:
                    next_delay = 0
                else:
                    next_delay = min(5, max(1, int(remaining / 4)))
            notify_new_otp(str(otp.id), delay_seconds=next_delay)
            return

        # check duplicate (some other worker/process may have saved same)
        already = OtpMessage.objects(order=order, otp=otp_token).first()
        if already:
            # we consider handled. Still, you may want to notify user? skip
            try:
                # still notify admins (if desired) but avoid duplicate OTP to user
                pass
            except Exception:
                pass
            # optionally remove pending entry
            otp.delete()
            return

        # Save OtpMessage (unique index + NotUniqueError protection)
        try:
            otpMessage = OtpMessage(
                order=order,
                user=otp.user,
                otp=otp_token,
                raw={"fetched_at": datetime.datetime.utcnow().isoformat()}
            )
            otpMessage.save()
        except NotUniqueError:
            # Another process saved the same OTP concurrently
            try:
                otp.delete()
            except Exception:
                pass
            return
        except Exception:
            # unexpected DB error -> re-enqueue small delay
            notify_new_otp(str(otp.id), delay_seconds=5)
            return

        # Send OTP message to user
        try:
            bot.send_message(
                otp.chat_id,
                f"💭 <b>New Message:</b> [<i>+{otp.phone}</i>]\n\n<b>Code:</b> <code>{otp_token}</code>"
            )
        except Exception:
            pass

        # call next_otp_url if present, best effort
        try:
            if otp.next_otp_url:
                requests.get(otp.next_otp_url.format(id=otp.order_id), timeout=5)
        except Exception:
            pass

        # notify admins
        try:
            admins = Admin.objects()
            for admin in admins:
                try:
                    bot.send_message(
                        admin.telegram_id,
                        f"Received OTP for user={otp.user.telegram_id} name={otp.user.name} number={otp.phone} order={otp.order_id} otp={otp_token}"
                    )
                except Exception:
                    pass
        except Exception:
            pass

        # finally remove pending entry
        try:
            otp.delete()
        except Exception:
            pass

    finally:
        # release lock if we acquired
        try:
            if lock:
                lock.release()
        except Exception:
            pass
