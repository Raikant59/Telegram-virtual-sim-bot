from mongoengine import Document, StringField, DateTimeField
from datetime import datetime


class Admin(Document):
    telegram_id = StringField(required=True, unique=True)  # Telegram user ID
    name = StringField()  # Optional name/username
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {"collection": "admins"}
