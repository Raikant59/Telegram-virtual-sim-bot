from mongoengine import Document, StringField, DateTimeField, IntField, FloatField
import datetime

class User(Document):
    telegram_id = StringField(required=True, unique=True)
    username = StringField()
    balance = IntField(default=0)
    total_recharged = FloatField(default=0)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
