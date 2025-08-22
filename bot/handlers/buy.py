from models.user import User
from models.order import Order

def handle(bot, message):

    return

    # chat_id = message["chat"]["id"]
    # user_id = str(message["from"]["id"])
    # username = message["from"].get("username", "")
    # user = User.objects(telegram_id=user_id).first()
    # if not user:
    #     user = User(telegram_id=user_id, username=username)
    #     user.save()
    # order = Order(service="telegram", country="india", user=user).save()
    # bot.send_message(chat_id, f"✅ Order created!\nOrder ID: {order.id}")
