from mongoengine import Document, StringField, DateTimeField, ReferenceField, IntField
import datetime
from .user import User

class Order(Document):
    service = StringField(required=True)      # e.g., telegram
    country = StringField(required=True)      # e.g., india
    number = StringField()
    status = StringField(default="pending")   # pending, active, completed
    price = IntField(default=0)
    user = ReferenceField(User)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
