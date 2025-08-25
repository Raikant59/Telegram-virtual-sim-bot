from mongoengine import *
import datetime


class OtpPending(Document):
    user = ReferenceField("User")
    phone = StringField()
    order_id = StringField()
    url = StringField()
    chat_id = IntField()
    cancel_url = StringField()
    next_otp_url = StringField()
    price = FloatField()
    message_id = IntField()
    cancelTime = IntField()
    responseType = StringField(choices=["Text", "JSON"], default="Text")
    created_at = DateTimeField(default=datetime.datetime.utcnow)