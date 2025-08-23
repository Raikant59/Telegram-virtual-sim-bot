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
from admin_panel.routes.payments import payments_bp
from admin_panel.routes.recharges import recharges_bp
from models.recharge import Recharge
from models.transaction import Transaction
from models.user import User
from models.payment_config import PaymentConfig



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
app.register_blueprint(payments_bp, url_prefix="/admin/payments")
app.register_blueprint(recharges_bp, url_prefix="/admin/recharges")


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

from flask import jsonify

@app.route("/webhooks/crypto", methods=["POST"])
def crypto_webhook():
    cfg = PaymentConfig.objects().first()
    if not cfg: return "no cfg", 400
    # Validate secret header/body (implementation depends on provider)
    if cfg.crypto_webhook_secret and request.headers.get("X-Webhook-Secret") != cfg.crypto_webhook_secret:
        return "forbidden", 403
    data = request.get_json(force=True, silent=True) or {}
    ref = (data.get("reference") or data.get("metadata",{}).get("reference") or "").strip()
    rid = ref or data.get("order_id") or data.get("invoice_id")
    if not rid: return "ok", 200
    r = Recharge.objects(id=rid).first()
    if not r: return "ok", 200
    status = (data.get("status") or "").lower()
    # Map provider statuses
    if status in ["paid","confirmed","completed","success"]:
        if r.status != "paid":
            u = r.user
            u.balance += r.amount
            u.total_recharged = (u.total_recharged or 0) + r.amount
            u.save()
            Transaction(user=u, type="credit", amount=r.amount,
                        closing_balance=u.balance, note="recharge via crypto").save()
            r.mark("paid", provider_txn_id=data.get("id") or data.get("invoice_id"), details=data)
    elif status in ["failed","expired","canceled","cancelled"]:
        r.mark("failed", details=data)
    else:
        r.details = data; r.save()
    return jsonify(ok=True)

@app.route("/webhooks/bharatpay", methods=["POST"])
def bharatpay_webhook():
    cfg = PaymentConfig.objects().first()
    if not cfg: return "no cfg", 400
    if cfg.bharatpay_webhook_secret and request.headers.get("X-Webhook-Secret") != cfg.bharatpay_webhook_secret:
        return "forbidden", 403
    data = request.get_json(force=True, silent=True) or {}
    rid = str(data.get("reference") or data.get("order_id") or "").strip()
    if not rid: return "ok", 200
    r = Recharge.objects(id=rid).first()
    if not r: return "ok", 200
    status = (data.get("status") or "").lower()
    if status in ["paid","success","captured","completed"]:
        if r.status != "paid":
            u = r.user
            u.balance += r.amount
            u.total_recharged = (u.total_recharged or 0) + r.amount
            u.save()
            Transaction(user=u, type="credit", amount=r.amount,
                        closing_balance=u.balance, note="recharge via BharatPay").save()
            r.mark("paid", provider_txn_id=data.get("txn_id") or data.get("id"), details=data)
    elif status in ["failed","expired","cancelled","canceled"]:
        r.mark("failed", details=data)
    else:
        r.details = data; r.save()
    return jsonify(ok=True)


@app.route("/webhook/<token>", methods=["POST"])
def webhooka(token):
    return "OK", 200

@app.route("/")
def index():
    return "Hello World!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
