# models/payment_config.py
from mongoengine import Document, StringField, BooleanField, FloatField

class PaymentConfig(Document):
    # enable/disable
    enable_manual = BooleanField(default=True)
    enable_crypto = BooleanField(default=False)
    enable_bharatpay = BooleanField(default=False)

    # global
    min_amount = FloatField(default=50.0)

    # Manual/UPI
    manual_upi_id = StringField()
    manual_qr_url = StringField()

    # Crypto (generic)
    crypto_provider = StringField(choices=["custom", "coinbase", "nowpayments"], default="custom")
    crypto_api_key = StringField()
    crypto_create_invoice_url = StringField()     # POST endpoint
    crypto_webhook_secret = StringField()
    crypto_wallet_or_account = StringField()      # e.g., wallet/account id

    # BharatPay (generic merchant)
    bharatpay_merchant_id = StringField()
    bharatpay_api_key = StringField()
    bharatpay_create_order_url = StringField()    # POST endpoint
    bharatpay_webhook_secret = StringField()
    bharatpay_upi_id = StringField()

    meta = {"collection": "payment_config"}
