import datetime
from mongoengine import Document, StringField, FloatField, DateTimeField, ReferenceField
from models.user import User

class Transaction(Document):
    user = ReferenceField(User, required=True)
    type = StringField(required=True, choices=["credit", "debit"])  # credit or debit
    amount = FloatField(required=True)
    discount = FloatField(default=0)
    closing_balance = FloatField(required=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    note = StringField(default="")  # e.g. "by bot" or "by admin"
