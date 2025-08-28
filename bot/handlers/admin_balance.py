from models.user import User
from bot.libs.helpers import is_admin
from models.transaction import Transaction
from models.recharge import Recharge
from bot.libs.helpers import get_total_user_balance


def handle(bot, message: dict):
    user_id = str(message["from"]["id"])
    chat_id = message["chat"]["id"]

    # check if admin
    if not is_admin(user_id):
        bot.send_message(
            chat_id, "❌ You are not authorized to use this command.")
        return

    # parse command
    text = message.get("text", "")
    parts = text.split()
    if len(parts) != 3:
        bot.send_message(
            chat_id, "⚠️ Usage:\n/add user_id amount\n/cut user_id amount")
        return

    command, target_id, amount_str = parts
    try:
        amount = float(amount_str)
    except ValueError:
        bot.send_message(chat_id, "⚠️ Amount must be a number.")
        return

    user = User.objects(telegram_id=target_id).first()
    if not user:
        bot.send_message(chat_id, "❌ User not found.")
        return

    if command == "/add":
        user.balance += amount
        user.total_recharged += amount
        user.save()
        bot.send_message(
            chat_id,
            f"✅ Added {amount} 💎 to user {target_id}. New balance: {user.balance:.2f}"
        )
        Transaction(
            user=user,
            type="credit",
            amount=amount,
            closing_balance=user.balance,
            note="by admin"
        ).save()

        Recharge(
            user=user,
            method="admin_add",
            amount=amount,
            currency="INR",
            status="paid",
        ).save()


    elif command == "/cut":
        if user.balance < amount:
            bot.send_message(
                chat_id, f"❌ User {target_id} doesn’t have enough balance.")
        else:
            user.balance -= amount
            user.total_recharged -= amount
            user.save()
            bot.send_message(
                chat_id,
                f"✅ Cut {amount} 💎 from user {target_id}. New balance: {user.balance:.2f}"
            )
            Transaction(
                user=user,
                type="debit",
                amount=amount,
                closing_balance=user.balance,
                note="by admin"
            ).save()
            Recharge(
                user=user,
                method="admin_cut",
                amount=amount,
                currency="INR",
                status="paid", 
            ).save()
    else:
        bot.send_message(chat_id, "⚠️ Unknown command.")


def handle_callback(bot, call):
    """Handles Balance callback"""
    user_id = str(call["from"]["id"])
    user = User.objects(telegram_id=user_id).first()

    if not is_admin(user_id):
        bot.send_message(
            user_id, "❌ You are not authorized to use this command.")
        return
    
    total = get_total_user_balance()
    bot.answer_callback_query(call["id"])
    bot.send_message(
        call["message"]["chat"]["id"],
        f"💰 <b>Total Balance of All Users:</b> ₹<code>{total:.2f}</code>",
        parse_mode="HTML"
    )
