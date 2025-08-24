# models/promo.py
import datetime
from mongoengine import (
    Document, StringField, DateTimeField, IntField, FloatField,
    ListField, ReferenceField, 
    BooleanField
)
from models.server import Service

class PromoCode(Document):
    """
    types:
      - CREDIT_FCFS: add `amount` 💎 to wallet, fcfs limited by max_uses
      - PERCENT_SERVICE: percent discount for next purchase of applicable services
      - FLAT_SERVICE: flat discount (amount) for next purchase of applicable services
      - LUCKY: random reward: credit or discount reserved for next service
    """
    code = StringField(required=True, unique=True, regex=r"^[A-Z0-9_-]{4,32}$")
    title = StringField(default="")
    type = StringField(required=True, choices=[
        "CREDIT_FCFS", "PERCENT_SERVICE", "FLAT_SERVICE", "LUCKY", "SPECIAL"
    ])
    amount = FloatField(default=0)         # credit amount or flat discount
    percent = FloatField(default=0)        # % discount
    max_uses = IntField(default=0)         # 0 = unlimited
    per_user_limit = IntField(default=1)
    uses = IntField(default=0)
    active = BooleanField(default=True)
    start_at = DateTimeField(default=datetime.datetime.utcnow)
    end_at = DateTimeField()               # optional
    applicable_services = ListField(StringField())  # list of Service.service_id
    notes = StringField(default="")
    created_by = StringField()             # admin tg id or name
    created_at = DateTimeField(default=datetime.datetime.utcnow)

class PromoRedemption(Document):
    promo = ReferenceField(PromoCode, required=True)
    user = ReferenceField('User', required=True)
    status = StringField(choices=['granted','reserved','consumed','expired','rejected'], default='granted')
    # if granted as wallet credit:
    amount_credit = FloatField(default=0)
    service = ReferenceField(Service, null=True)

    # if reserved for discount on next purchase:
    server_id = StringField()
    percent = FloatField(default=0)
    flat = FloatField(default=0)
    service_id = StringField()             # set on consume
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    consumed_at = DateTimeField()
