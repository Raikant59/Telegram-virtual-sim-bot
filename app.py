import os
from flask import Flask, request
from dotenv import load_dotenv
from telebot import TeleBot
from mongoengine import connect
import json

from bot.dispatcher import dispatcher
from admin_panel.routes.dashboard import dashboard_bp
from admin_panel.routes.servers import servers_bp
from admin_panel.routes.services import services_bp
from admin_panel.routes.apis import apis_bp
from admin_panel.routes.users import users_bp



from utils.worker import init_worker



# Load env vars
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/virtualsim")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

# Init DB
connect(host=MONGO_URI)

# Init Flask
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.urandom(24)

# Init Telebot (just for parsing)
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")

init_worker(bot)

# Register admin routes
app.register_blueprint(dashboard_bp, url_prefix="/admin")
app.register_blueprint(servers_bp, url_prefix="/admin/servers")
app.register_blueprint(services_bp, url_prefix="/admin/services")
app.register_blueprint(apis_bp, url_prefix="/admin/apis")
app.register_blueprint(users_bp, url_prefix="/admin/users")


# Telegram webhook route
@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Always return 200 to Telegram. Attempt to parse and dispatch updates,
    but swallow errors so Telegram doesn't keep retrying.
    """
    update = None
    try:
        # Preferred: Flask provides is_json and get_json
        if request.is_json:
            # silent=True -> returns None instead of raising on bad JSON
            update = request.get_json(silent=True)
        else:
            # Try to parse request.data as JSON (covers other content types)
            raw = request.data or b""
            if raw:
                try:
                    update = json.loads(raw.decode("utf-8"))
                except Exception:
                    update = None

        if update:
            try:
                # call your dispatcher (wrap handler execution so it can't raise)
                dispatcher.handle_update(update, bot)
            except Exception as e:
                # log but do NOT return an error to Telegram
                app.logger.exception("Error while handling update: %s", e)
        else:
            # invalid/empty payload; log for investigation
            app.logger.warning("Webhook received empty/invalid payload. headers=%s body=%s",
                               dict(request.headers), request.data[:1000])
    except Exception as e:
        # catch-all so we never return non-200
        app.logger.exception("Unexpected error in webhook endpoint: %s", e)

    # ALWAYS return 200 so Telegram considers update delivered
    return "OK", 200


@app.route("/webhook/<token>", methods=["POST"])
def webhooka(token):
    return "OK", 200

@app.route("/")
def index():
    return "Hello World!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
