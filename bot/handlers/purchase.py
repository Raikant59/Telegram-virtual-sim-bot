# bot/handlers/purchase.py
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from models.order import Order
from models.server import Service, ConnectApi
from models.transaction import Transaction
from bot.libs.helpers import safe_edit_message
from utils.worker import notify_new_otp
from models.otpPending import OtpPending

def handle(bot, call):
    user_id = str(call["from"]["id"])
    chat_id = call["message"]["chat"]["id"]

    user = User.objects(telegram_id=user_id).first()
    if not user:
        bot.answer_callback_query(call["id"], "❌ Please /start first.")
        return

    # Parse service id
    data = call["data"].split(":")
    if len(data) != 2:
        bot.answer_callback_query(call["id"], "⚠️ Invalid request.")
        return

    service_id = data[1]
    service = Service.objects(service_id=service_id).first()
    if not service:
        bot.answer_callback_query(call["id"], "❌ Service not found.")
        return

    # Check balance *before* attempting purchase (user must have enough)
    if user.balance < service.price:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(text="💸 Recharge now", callback_data=f"recharge"))
        bot.send_message(chat_id, f"❌ Not enough balance. You have {user.balance:.2f} 💎", reply_markup=markup)
        bot.answer_callback_query(call["id"], "💰 Not enough balance!")
        return

    # Find provider API config
    connect = ConnectApi.objects(server=service.server).first()
    if not connect:
        bot.answer_callback_query(call["id"], "⚠️ Provider not configured.")
        return

    url = connect.get_number_url.format(service_code=service.code)

    # Call provider first. Only if we successfully receive a number we will deduct and create Order.
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        raw = response.text
    except Exception as e:
        bot.send_message(chat_id, f"❌ Error contacting provider: {e}")
        bot.answer_callback_query(call["id"], "⚠️ Provider request failed.")
        return

    provider_order_id = None
    number = None
    parsed = {}

    # Parse response
    if connect.response_type == "Text":
        # Expected: ACCESS_NUMBER:{order_id}:{number}
        parts = raw.strip().split(":")
        if len(parts) >= 3 and parts[0] == "ACCESS_NUMBER":
            provider_order_id = parts[1]
            number = parts[2]
            parsed = {"id": provider_order_id, "phone": number}
        else:
            bot.send_message(chat_id, "⚠️ Unexpected provider response (Text).")
            return
    else:
        try:
            parsed = response.json()
            provider_order_id = str(parsed.get("id") or parsed.get("order_id") or "")
            number = parsed.get("phone") or parsed.get("number")
            if not provider_order_id or not number:
                bot.send_message(chat_id, "⚠️ Provider returned incomplete data.")
                return
        except Exception:
            bot.send_message(chat_id, "⚠️ Invalid JSON from provider.")
            return

    # At this point provider returned a number → deduct user balance atomically
    # Re-load fresh user from DB to reduce race-conditions
    user.reload()
    if user.balance < service.price:
        bot.send_message(chat_id, f"❌ Not enough balance at the moment. You have {user.balance:.2f} 💎")
        return

    user.balance -= service.price
    user.save()

    # Create Order record
    order = Order(
        service=service,
        server=service.server,
        user=user,
        number=number,
        provider_order_id=provider_order_id,
        status="active",
        price=service.price,
        raw_response=parsed,
    ).save()

    # Save transaction (debit)
    Transaction(
        user=user,
        type="debit",
        amount=service.price,
        closing_balance=user.balance,
        note=f"purchase:{order.id}"
    ).save()

    # Send message and create OtpPending linked to this order
    text = (f"📦 {service.name} [{service.server.country.split()[0]}] [ 💎 {service.price}  ]\n"
            f"📱 Number: +<code>{number}</code>\n"
            f"⏳ <i>This Number is valid till</i> {connect.auto_cancel_time} minutes\n"
            )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(text="🚫 Cancel", callback_data=f"cancel:{provider_order_id}"),
        InlineKeyboardButton(text="🔁 Buy Again", callback_data=f"buy:{provider_order_id}")
    )

    msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

    # Link otp watcher - store provider_order_id and order.id
    OtpPending(
        user=user,
        phone=number,
        order_id=provider_order_id,
        url=connect.get_status_url,
        chat_id=chat_id,
        message_id=msg.message_id,
        cancelTime=connect.auto_cancel_time * 60,
        cancel_url=connect.cancel_url,
        responseType=connect.response_type
    ).save()

    # Notify worker to start polling
    notify_new_otp()
    bot.answer_callback_query(call["id"], "✅ Order created!")
