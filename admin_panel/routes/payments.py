# admin_panel/routes/payments.py
from flask import Blueprint, render_template, request, redirect, url_for
from models.payment_config import PaymentConfig

payments_bp = Blueprint("payments", __name__, template_folder="../templates")

def _cfg():
    cfg = PaymentConfig.objects().first()
    if not cfg:
        cfg = PaymentConfig().save()
    return cfg

@payments_bp.route("/", methods=["GET", "POST"])
def payments():
    cfg = _cfg()
    if request.method == "POST":
        # toggles
        cfg.enable_manual = bool(request.form.get("enable_manual"))
        cfg.enable_crypto = bool(request.form.get("enable_crypto"))
        cfg.enable_bharatpay = bool(request.form.get("enable_bharatpay"))

        # values
        cfg.min_amount = float(request.form.get("min_amount") or 50)

        cfg.manual_upi_id = request.form.get("manual_upi_id") or ""
        cfg.manual_qr_url = request.form.get("manual_qr_url") or ""

        cfg.crypto_provider = request.form.get("crypto_provider") or "custom"
        cfg.crypto_api_key = request.form.get("crypto_api_key") or ""
        cfg.crypto_create_invoice_url = request.form.get("crypto_create_invoice_url") or ""
        cfg.crypto_webhook_secret = request.form.get("crypto_webhook_secret") or ""
        cfg.crypto_wallet_or_account = request.form.get("crypto_wallet_or_account") or ""

        cfg.bharatpay_merchant_id = request.form.get("bharatpay_merchant_id") or ""
        cfg.bharatpay_api_key = request.form.get("bharatpay_api_key") or ""
        cfg.bharatpay_create_order_url = request.form.get("bharatpay_create_order_url") or ""
        cfg.bharatpay_webhook_secret = request.form.get("bharatpay_webhook_secret") or ""
        cfg.bharatpay_upi_id = request.form.get("bharatpay_upi_id") or ""

        cfg.save()
        return redirect(url_for("payments.payments"))

    return render_template("payments.html", cfg=cfg)
