# models/recharge.py
import datetime
from mongoengine import (
    Document, ReferenceField, StringField, FloatField, DateTimeField,
    DictField, IntField
)
from .user import User

class Recharge(Document):
    user = ReferenceField(User, required=True)
    method = StringField(required=True, choices=["manual", "crypto", "bharatpay"])
    amount = FloatField(required=True)
    currency = StringField(default="INR")

    utr = StringField()                 # for manual UPI
    provider_txn_id = StringField()     # txn/invoice id from gateway
    payment_link = StringField()        # invoice/payment url
    address_or_upi = StringField()      # crypto addr or UPI ID

    chat_id = IntField()
    request_message_id = IntField()

    status = StringField(choices=[
        "created", "awaiting_utr", "pending", "paid", "rejected", "failed", "expired"
    ], default="created")

    # renamed from `meta`
    details = DictField(default={})

    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    def mark(self, new_status: str, **updates):
        self.status = new_status
        for k, v in updates.items():
            setattr(self, k, v)
        self.updated_at = datetime.datetime.utcnow()
        self.save()
