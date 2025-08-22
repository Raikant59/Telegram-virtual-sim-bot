from models.order import Order

def handle(bot, message):

    return
    # chat_id = message["chat"]["id"]
    # user_id = str(message["from"]["id"])
    # orders = Order.objects(user__telegram_id=user_id).order_by('-created_at')[:3]
    # if not orders:
    #     bot.send_message(chat_id, "❌ No recent orders found.")
    #     return
    # text = "📦 Your recent orders:\n\n"
    # for o in orders:
    #     text += f"🆔 {o.id} | {o.service} | {o.status}\n"
    # bot.send_message(chat_id, text)
