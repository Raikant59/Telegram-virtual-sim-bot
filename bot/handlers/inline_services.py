from telebot import types
from models.server import Service
from services.promos import apply_discount_for_service
from models.user import User


def handle_inline(bot, inline_query):
    query = inline_query.get("query", "").strip().lower()

    # Get all services
    services = Service.objects()
    results = []
    seen_names = set()

    for s in services:
        if query and query not in s.name.lower():
            continue
        if s.name in seen_names:
            continue  # skip duplicates
        seen_names.add(s.name)

        results.append(
            types.InlineQueryResultArticle(
                id=str(s.service_id),
                title=s.name,
                description=s.description,
                thumbnail_url=s.logo,
                input_message_content=types.InputTextMessageContent(
                    message_text=f"/show_server {s.name}"
                )
            )
        )

    bot.answer_inline_query(inline_query["id"], results, cache_time=1, is_personal=True)


def show_server(bot, message):
    """Handles /show_server {name}"""
    parts = message.get("text", "").split(maxsplit=1)
    if len(parts) < 2:
        bot.send_message(message["chat"]["id"], "⚠️ Usage: /show_server {name}")
        return

    service_name = parts[1]
    services = Service.objects(name=service_name)
    if not services:
        bot.send_message(message["chat"]["id"], f"❌ Service '{service_name}' not found.")
        return
    
    # current user
    uid = str(message["from"]["id"])
    user = User.objects(telegram_id=uid).first()
    if not user:
        bot.send_message(message["chat"]["id"], "⚠️ Please start bot first with /start")
        return

    text = f"➤ Selected Service: {service_name}\n\n↓ Choose a Server Below"
    markup = types.InlineKeyboardMarkup()

    for s in services:
        base_price = s.price
        final_price, redemption, discount = apply_discount_for_service(user, s, base_price)

        if discount:
            label = f"{s.server.name} → [{s.server.country.split()[0]}] [💎 {final_price} (🎟️ -{discount})]"
        else:
            label = f"{s.server.name} → [{s.server.country.split()[0]}] [{base_price} 💎]"

        markup.row(
            types.InlineKeyboardButton(
                text=label,
                callback_data=f"purchase:{s.service_id}"
            )
        )

    bot.send_message(message["chat"]["id"], text, parse_mode="HTML", reply_markup=markup)
