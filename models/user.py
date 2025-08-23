import datetime

from mongoengine import Document, StringField, DateTimeField, FloatField, BooleanField

class User(Document):
    telegram_id = StringField(required=True, unique=True)
    name = StringField(default="None")
    username = StringField()
    balance = FloatField(default=0.0)
    total_recharged = FloatField(default=0)
    blocked = BooleanField(default=False) # new
    created_at = DateTimeField(default=datetime.datetime.utcnow)