# models/otp.py
from mongoengine import Document, ReferenceField, StringField, DictField, DateTimeField
import datetime
from .order import Order
from .user import User

class OtpMessage(Document):
    order = ReferenceField(Order, required=False)
    user = ReferenceField(User, required=False)
    otp = StringField()        
    raw = DictField()  
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "otp_messages",
        "indexes": [
            {"fields": ["order", "otp"], "unique": True}
        ]
    }

