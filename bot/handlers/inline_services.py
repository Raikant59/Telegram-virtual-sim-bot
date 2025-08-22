from telebot import types
from models.server import Service

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
    service = Service.objects(name=service_name)
    if not service:
        bot.send_message(message["chat"]["id"], f"❌ Service '{service_name}' not found.")
        return
    
    text = f"➤ Selected Service: {service_name}\n\n ↓ Choose a Server Below"

    markup = types.InlineKeyboardMarkup()
    for s in service:
        markup.row(
            types.InlineKeyboardButton(
                text=f"{s.server.name} → [{s.server.country.split()[0]}] [{s.price} 💎]",
                callback_data=f"purchase:{s.service_id}"
            )
        )
    bot.send_message(message["chat"]["id"], text, parse_mode="HTML", reply_markup=markup)      