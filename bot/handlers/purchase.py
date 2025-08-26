import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from models.user import User
from models.order import Order
from models.server import Service, ConnectApi
from models.transaction import Transaction
from utils.worker import notify_new_otp
from models.otpPending import OtpPending
from models.admin import Admin
from bot.libs.Admin_message import purchase_text
from services.promos import apply_discount_for_service, consume_reserved_promo


def update_progress(bot, chat_id, message_id, step):
    """Update progress bar based on step number (1-6)."""
    progress_states = {
        1: "⚙️ Processing Your Order...\n▮▯▯▯▯▯▯▯▯▯ 10%",
        2: "⚙️ Processing Your Order...\n▮▮▯▯▯▯▯▯▯▯ 30%",
        3: "⚙️ Processing Your Order...\n▮▮▮▮▯▯▯▯▯▯ 50%",
        4: "⚙️ Processing Your Order...\n▮▮▮▮▮▮▯▯▯▯ 70%",
        5: "⚙️ Processing Your Order...\n▮▮▮▮▮▮▮▮▯▯ 90%",
        6: "⚙️ Processing Your Order...\n▮▮▮▮▮▮▮▮▮▯ 99%",
    }
    if step in progress_states:
        try:
            bot.edit_message_text(progress_states[step], chat_id=chat_id, message_id=message_id)
        except:
            pass


def handle(bot, call):
    user_id = str(call["from"]["id"])
    chat_id = call["message"]["chat"]["id"]
    progress_msg_id = None
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

    # Step 1 - show initial progress
    msg = bot.send_message(chat_id, "⚙️ Processing Your Order...\n▮▯▯▯▯▯▯▯▯▯ 10%")
    progress_msg_id = msg.message_id

    # --- DISCOUNT CALCULATION ---
    base_price = service.price
    final_price, redemption, discount = apply_discount_for_service(user, service, base_price)

    # Step 2 - check balance
    if user.balance < final_price:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(text="💸 Recharge now", callback_data=f"recharge"))
        bot.send_message(
            chat_id,
            f"❌ Not enough balance.\nYou have {user.balance:.2f} 💎\n"
            f"Required: {final_price:.2f} 💎",
            reply_markup=markup
        )
        if progress_msg_id:
            try:
                bot.delete_message(chat_id, progress_msg_id)
            except:
                pass

        bot.answer_callback_query(call["id"], "💰 Not enough balance!")
        return
    update_progress(bot, chat_id, progress_msg_id, 2)

    # Step 3 - get provider API config
    connect = ConnectApi.objects(server=service.server).first()
    if not connect:

        bot.answer_callback_query(call["id"], "🚫 Number not available on this  service.")
        if progress_msg_id:
            try:
                bot.delete_message(chat_id, progress_msg_id)
            except:
                pass
        return
    try:
        url = connect.get_number_url.format(service_code=service.code)
    except Exception:
        bot.send_message(chat_id, "🚫 Number not available on this  service.")
        bot.answer_callback_query(call["id"], "🚫 Number not available on this  service.")
        if progress_msg_id:
            try:
                bot.delete_message(chat_id, progress_msg_id)
            except:
                pass
        return
    update_progress(bot, chat_id, progress_msg_id, 3)

    # Step 4 - call provider
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        raw = response.text
    except Exception as e:
        bot.send_message(chat_id, f"🚫 Number not available on this  service")
        bot.answer_callback_query(call["id"], "🚫 Number not available on this  service")
        if progress_msg_id:
            try:
                bot.delete_message(chat_id, progress_msg_id)
            except:
                pass
        return
    update_progress(bot, chat_id, progress_msg_id, 4)

    # Step 5 - parse response
    provider_order_id, number, parsed = None, None, {}
    if connect.response_type == "Text":
        parts = raw.strip().split(":")
        if len(parts) >= 3 and parts[0] == "ACCESS_NUMBER":
            provider_order_id, number = parts[1], parts[2]
            parsed = {"id": provider_order_id, "phone": number}
        else:
            bot.send_message(chat_id, "🚫 Number not available on this  service.")
            if progress_msg_id:
                try:
                    bot.delete_message(chat_id, progress_msg_id)
                except:
                    pass
            return
    else:
        try:
            parsed = response.json()
            provider_order_id = str(parsed.get("id") or parsed.get("order_id") or "")
            number = parsed.get("phone") or parsed.get("number")
            if not provider_order_id or not number:
                bot.send_message(chat_id, "🚫 Number not available on this  service.")
                if progress_msg_id:
                    try:
                        bot.delete_message(chat_id, progress_msg_id)
                    except:
                        pass
                return
        except Exception:
            if progress_msg_id:
                try:
                    bot.delete_message(chat_id, progress_msg_id)
                except:
                    pass
            bot.send_message(chat_id, "🚫 Number not available on this  service.")
            return
    update_progress(bot, chat_id, progress_msg_id, 5)

    # Step 6 - deduct balance + create order
    user = User.objects(id=user.id, balance__gte=final_price).modify(dec__balance=final_price, new=True)
    if not user:
        bot.send_message(
            chat_id,
            f"❌ Not enough balance at the moment. "
            f"You have {User.objects(id=user.id).first().balance:.2f} 💎"
        )
        if progress_msg_id:
            try:
                bot.delete_message(chat_id, progress_msg_id)
            except:
                pass
        return

    order = Order(
        service=service,
        server=service.server,
        user=user,
        number=number,
        provider_order_id=provider_order_id,
        status="active",
        price=final_price,
        raw_response=parsed,
    )
    order.save()

    Transaction(
        user=user,
        type="debit",
        amount=final_price,
        discount=discount if discount else 0,
        closing_balance=user.balance,
        note=f"purchase:{order.id}"
    ).save()
    update_progress(bot, chat_id, progress_msg_id, 6)

    # 🔹 Consume promo redemption if used
    if redemption:
        consume_reserved_promo(redemption, service)
    
    country_code = number[:2]      # first 2 digits
    local_number = number[2:]      # rest of the digits


    # Final confirmation
    text = (
        f"📦 {service.name} [{service.server.country.split()[0]}] "
        f"[ 💎 {final_price} ]\n"
        f"📱 Number: +{country_code}<code>{local_number}</code>\n"
        f"⏳ <i>This Number is valid till</i> {connect.auto_cancel_time} minutes\n"
    )

    
    if discount:
        text = (
            f"📦 {service.name} [{service.server.country.split()[0]}]\n"
            f"💰 Base Price: {base_price} 💎\n"
            f"🎟️ Discount: -{discount} 💎\n"
            f"✅ Final Price Paid: {final_price} 💎\n\n"
            f"📱 Number: +{country_code}<code>{local_number}</code>\n"
            f"⏳ <i>This Number is valid till</i> {connect.auto_cancel_time} minutes\n"
        )

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton(text="🚫 Cancel", callback_data=f"cancel:{provider_order_id}"),
        InlineKeyboardButton(text="🔁 Buy Again", callback_data=f"purchase:{service_id}")
    )
    
    msg = bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
    if progress_msg_id:
        try:
            bot.delete_message(chat_id, progress_msg_id)
        except:
            pass
    try:
        bot.answer_callback_query(call["id"], "📦 Order placed!")
    except:
        pass

    # OTP Watcher
    OtpPending(
        user=user,
        phone=number,
        order_id=provider_order_id,
        url=connect.get_status_url,
        price=final_price,
        chat_id=chat_id,
        message_id=msg.message_id,
        cancelTime=connect.auto_cancel_time * 60,
        cancel_url=connect.cancel_url,
        next_otp_url=connect.next_number_url,
        responseType=connect.response_type,
    ).save()

    notify_new_otp()

    # Notify admins
    admins = Admin.objects()
    admin_text = purchase_text.format(
        user_id=call["from"]["id"],
        service_name=service.name,
        server_name=service.server.name,
        username=call["from"].get("username"),
        name=call["from"]["first_name"],
        number=number,
        discount=discount if discount else "Not Applied",
        order_id=provider_order_id,
        price=final_price,
        balance=user.balance,
    )
    for admin in admins:
        bot.send_message(admin.telegram_id, admin_text)
