import os
from flask import Flask, request
from dotenv import load_dotenv
from telebot import TeleBot
from mongoengine import connect

from bot.dispatcher import dispatcher
from admin_panel.routes.dashboard import dashboard_bp

# Load env vars
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/virtualsim")

# Init DB
connect(host=MONGO_URI)

# Init Flask
app = Flask(__name__)

# Init Telebot (just for parsing)
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

# Register admin routes
app.register_blueprint(dashboard_bp, url_prefix="/admin")

# Telegram webhook route
@app.route("/webhook", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        update = request.get_json()
        dispatcher.handle_update(update, bot)  # manual dispatch
        return "OK", 200
    return "Unsupported Media Type", 415

@app.route("/webhook/<token>", methods=["POST"])
def webhooka(token):
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
