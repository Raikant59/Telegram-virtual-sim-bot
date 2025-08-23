from models.recharge import Recharge
from models.transaction import Transaction
from models.user import User

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
            f"❌ Your recharge of ₹{r.amount:.2f} via {r.method} has been rejected by admin.\n"
            f"If this is a mistake, please contact support."
        )

    # --- NOTHING TO DO ---
    else:
        bot.edit_message_text(
            f"Nothing to do.\n\n{details_text}",
            chat_id=call["message"]["chat"]["id"],
            message_id=call["message"]["message_id"]
        )
