# bot/handlers/recharge.py
import re, json, requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from models.user import User
from models.recharge import Recharge
from models.payment_config import PaymentConfig
from models.transaction import Transaction
from bot.libs.helpers import safe_edit_message, is_admin
from models.admin import Admin

AMOUNTS = [100, 200, 500]

def _cfg():
    cfg = PaymentConfig.objects().first()
    return cfg

def _ensure_user(bot, from_):
    uid = str(from_["id"])
    user = User.objects(telegram_id=uid).first()
    if not user:
        user = User(telegram_id=uid, username=from_.get("username","")).save()
    return user

def menu(bot, call):
    """Callback: recharge"""
    user = _ensure_user(bot, call["from"])
    cfg = _cfg()
    if not cfg:
        bot.answer_callback_query(call["id"], "Payments not configured yet.")
        return

    text = "💳 <b>Recharge</b>\nChoose a method below."
    kb = InlineKeyboardMarkup(row_width=1)
    if cfg.enable_manual:
        kb.add(InlineKeyboardButton("🇮🇳 Manual (UPI/QR)", callback_data="pay:manual"))
    if cfg.enable_bharatpay:
        kb.add(InlineKeyboardButton("🏦 BharatPay (Link/UPI)", callback_data="pay:bharatpay"))
    if cfg.enable_crypto:
        kb.add(InlineKeyboardButton("🪙 Crypto", callback_data="pay:crypto"))
    kb.add(InlineKeyboardButton("« Back", callback_data="back_main"))
    safe_edit_message(bot, call, text, kb)
    bot.answer_callback_query(call["id"])

def amount_keyboard(cfg):
    kb = InlineKeyboardMarkup(row_width=3)
    btns = [InlineKeyboardButton(f"{a} 💎", callback_data=f"amt:{a}") for a in AMOUNTS]
    kb.row(*btns)
    kb.row(InlineKeyboardButton("Enter custom amount", callback_data="amt:custom"))
    kb.row(InlineKeyboardButton("« Back", callback_data="recharge"))
    return kb

def pay_callback(bot, call):
    # data: "pay:<method>"
    _, method = call["data"].split(":")
    cfg = _cfg()
    if method == "manual":
        text = (
            "🇮🇳 <b>Manual UPI Recharge</b>\n"
            f"UPI ID: <code>{cfg.manual_upi_id or '—'}</code>\n\n"
            "1) Select amount\n2) Pay to the UPI/QR\n3) Tap 'I Paid • Submit UTR' and REPLY your UTR number.\n"
        )
        markup = amount_keyboard(cfg)
        safe_edit_message(bot, call, text, markup)
    elif method in ["crypto", "bharatpay"]:
        text = f"🔗 <b>{method.capitalize()} Recharge</b>\nSelect amount to generate a payment link."
        markup = amount_keyboard(cfg)
        safe_edit_message(bot, call, text, markup)
    bot.answer_callback_query(call["id"])

def amount_callback(bot, call):
    # data: "amt:<value|custom>"
    _, v = call["data"].split(":")
    cfg = _cfg()
    if v == "custom":
        bot.answer_callback_query(call["id"], "Send the amount (numbers only).")
        bot.send_message(call["message"]["chat"]["id"],
            f"💵 Enter amount (>= {cfg.min_amount:.0f} 💎).", reply_markup=ForceReply(selective=True))
        return
    amt = float(v)
    _show_method_resume(bot, call, amt)

def _show_method_resume(bot, call, amount):
    # Reconstruct method from previous text (we encoded it earlier) — or simpler: store in message meta
    # We’ll use the currently displayed text to detect method:
    text = call["message"]["text"]
    m = "manual" if "Manual UPI" in text else ("crypto" if "Crypto Recharge" in text else "bharatpay")
    cfg = _cfg()
    if amount < (cfg.min_amount or 0):
        bot.answer_callback_query(call["id"], f"Min amount is {cfg.min_amount:.0f} 💎")
        return

    if m == "manual":
        disp = (
            f"🇮🇳 <b>Manual UPI</b>\nAmount: {amount:.2f} 💎\nUPI: <code>{cfg.manual_upi_id or '-'}</code>\n"
            f"{'📷 QR: ' + cfg.manual_qr_url if cfg.manual_qr_url else ''}\n\n"
            "After you pay, press the button below and REPLY with your UTR."
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("✅ I Paid • Submit UTR", callback_data=f"utr:{amount}"))
        kb.add(InlineKeyboardButton("« Back", callback_data="recharge"))
        safe_edit_message(bot, call, disp, kb)
    else:
        # Create a draft Recharge now; payment link will be generated on click "Generate Link"
        disp = f"🔗 <b>{m.capitalize()} Recharge</b>\nAmount: {amount:.2f} 💎\nTap the button to generate a payment link."
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔗 Generate Link", callback_data=f"utr:{amount}"))  # reuse 'utr' slot to continue
        kb.add(InlineKeyboardButton("« Back", callback_data="recharge"))
        safe_edit_message(bot, call, disp, kb)
    bot.answer_callback_query(call["id"])

def ask_utr_callback(bot, call):
    # We branch by looking at current text (manual vs gateway)
    text = call["message"]["text"]
    chat_id = call["message"]["chat"]["id"]
    user = _ensure_user(bot, call["from"])
    amount = float(call["data"].split(":")[1])

    if "Manual UPI" in text:
        r = Recharge(user=user, method="manual", amount=amount, currency="INR",
                     status="awaiting_utr", chat_id=chat_id).save()
        msg = bot.send_message(chat_id,
            "📮 Reply to this message with your <b>UTR</b> number.", parse_mode="HTML",
            reply_markup=ForceReply(selective=True))
        r.request_message_id = msg.message_id
        r.save()
    else:
        # Crypto / BharatPay — create order/invoice via configured API
        rmethod = "crypto" if "Crypto" in text else "bharatpay"
        cfg = _cfg()
        r = Recharge(user=user, method=rmethod, amount=amount, currency="INR",
                     status="pending", chat_id=chat_id).save()
        try:
            if rmethod == "crypto":
                # Generic invoice create
                payload = {
                    "amount": amount,
                    "currency": "INR",
                    "account": cfg.crypto_wallet_or_account,
                    "reference": str(r.id),
                    "callback": f"/webhooks/crypto",   # absolute URL recommended in production
                }
                headers = {"Authorization": f"Bearer {cfg.crypto_api_key}"} if cfg.crypto_api_key else {}
                resp = requests.post(cfg.crypto_create_invoice_url, json=payload, headers=headers, timeout=10)
                data = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {}
                r.provider_txn_id = data.get("id") or data.get("invoice_id")
                r.payment_link = data.get("hosted_url") or data.get("invoice_url")
                r.address_or_upi = data.get("address")
                r.details = data
                r.save()
            else:
                payload = {
                    "merchant_id": cfg.bharatpay_merchant_id,
                    "amount": amount,
                    "reference": str(r.id),
                    "callback": f"/webhooks/bharatpay",
                }
                headers = {"X-API-KEY": cfg.bharatpay_api_key} if cfg.bharatpay_api_key else {}
                resp = requests.post(cfg.bharatpay_create_order_url, json=payload, headers=headers, timeout=10)
                data = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {}
                r.provider_txn_id = data.get("order_id") or data.get("id")
                r.payment_link = data.get("payment_url") or data.get("short_url")
                r.address_or_upi = cfg.bharatpay_upi_id
                r.details = data
                r.save()
            if r.payment_link:
                kb = InlineKeyboardMarkup()
                kb.add(InlineKeyboardButton("🔗 Pay Now", url=r.payment_link))
                kb.add(InlineKeyboardButton("« Back", callback_data="recharge"))
                safe_edit_message(bot, call,
                    f"✅ Link generated.\nAmount: {amount:.2f} 💎\nOpen the payment link to complete.",
                    kb)
            else:
                safe_edit_message(bot, call, "⚠️ Failed to generate a payment link. Try another method.", None)
                r.mark("failed")
        except Exception as e:
            r.mark("failed", details={"error": str(e)})
            safe_edit_message(bot, call, f"⚠️ Error: {e}", None)

    bot.answer_callback_query(call["id"])

# Capture UTR replies (ForceReply)
def capture_utr_message(bot, message):
    # Only act if it is a reply
    reply = message.get("reply_to_message")
    if not reply: 
        return
    # Find a recharge waiting for this reply
    r = Recharge.objects(chat_id=message["chat"]["id"], request_message_id=reply["message_id"], status="awaiting_utr").first()
    if not r:
        return
    utr = (message.get("text") or "").strip()
    # quick sanity: 6-25 alphanum (banks vary)
    if not re.match(r"^[A-Za-z0-9\-]{6,25}$", utr):
        bot.send_message(message["chat"]["id"], "❌ Invalid UTR format. Please send only the UTR (6–25 chars).")
        return
    r.utr = utr
    r.mark("pending")
    bot.send_message(message["chat"]["id"], f"✅ UTR received: <code>{utr}</code>\nWe’ll verify shortly.", parse_mode="HTML")
    _notify_admins(bot, r)

def _notify_admins(bot, r: Recharge):
    from models.admin import Admin
    admins = Admin.objects()
    if not admins:
        return
    text = (
        "🆕 <b>Recharge Pending</b>\n\n"
        f"User: <code>{r.user.telegram_id}</code>\n"
        f"Method: {r.method}\nAmount: {r.amount:.2f} 💎\n"
        f"UTR/Txn: <code>{r.utr or r.provider_txn_id or '-'}</code>\n"
        f"ID: {r.id}\n\nApprove?"
    )
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"rcg:approve:{r.id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"rcg:reject:{r.id}")
    )
    for a in admins:
        try:
            bot.send_message(int(a.telegram_id), text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass


def action_callback(bot, call):
    # Only admins
    if not is_admin(str(call["from"]["id"])):
        bot.answer_callback_query(call["id"], "Not allowed.")
        return

    try:
        _, action, rid = call["data"].split(":")
    except ValueError:
        bot.answer_callback_query(call["id"], "Invalid action.")
        return

    r = Recharge.objects(id=rid).first()
    if not r:
        bot.edit_message_text(
            "Recharge not found.",
            chat_id=call["message"]["chat"]["id"],
            message_id=call["message"]["message_id"]
        )
        return

    user = r.user
    if not user:
        bot.edit_message_text(
            "User not found.",
            chat_id=call["message"]["chat"]["id"],
            message_id=call["message"]["message_id"]
        )
        return

    # Build detail text for admin
    details_text = (
        f"User: {user.id}\n"
        f"Method: {r.method}\n"
        f"Amount: {r.amount:.2f} 💎\n"
        f"UTR/Txn: {r.utr or r.provider_txn_id or 'N/A'}"
    )

    # --- APPROVE ---
    if action == "approve" and r.status in ["pending", "awaiting_utr"]:
        # update balance
        user.balance += r.amount
        user.total_recharged = (user.total_recharged or 0) + r.amount
        user.save()

        # add transaction entry
        Transaction(
            user=user,
            type="credit",
            amount=r.amount,
            closing_balance=user.balance,
            note=f"recharge via {r.method}"
        ).save()

        # mark recharge
        r.mark("paid")

        # edit admin message
        bot.edit_message_text(
            f"Recharge Approved ✅\n\n{details_text}",
            chat_id=call["message"]["chat"]["id"],
            message_id=call["message"]["message_id"]
        )

        # notify user
        bot.send_message(
            user.chat_id,
            f"✅ Your recharge of {r.amount:.2f} 💎 via {r.method} has been approved.\n"
            f"New Balance: {user.balance:.2f} 💎"
        )

    # --- REJECT ---
    elif action == "reject" and r.status in ["pending", "awaiting_utr"]:
        r.mark("rejected")

        # edit admin message
        bot.edit_message_text(
            f"Recharge Rejected ❌\n\n{details_text}",
            chat_id=call["message"]["chat"]["id"],
            message_id=call["message"]["message_id"]
        )

        # notify user
        bot.send_message(
            user.chat_id,
            f"❌ Your recharge of {r.amount:.2f} 💎 via {r.method} has been rejected by admin.\n"
            f"If this is a mistake, please contact support."
        )

    # --- NOTHING TO DO ---
    else:
        bot.edit_message_text(
            f"Nothing to do.\n\n{details_text}",
            chat_id=call["message"]["chat"]["id"],
            message_id=call["message"]["message_id"]
        )
