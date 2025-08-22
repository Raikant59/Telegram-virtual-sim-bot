from mongoengine import Document, StringField, DateTimeField, ReferenceField
import datetime
from .user import User

from mongoengine import Document, StringField, DateTimeField, ReferenceField, FloatField, DictField
import datetime
from .user import User
from .server import Server, Service

class Order(Document):
    service = ReferenceField(Service, required=True)  
    server = ReferenceField(Server, required=True)
    user = ReferenceField(User, required=True)       

    number = StringField()        
    provider_order_id = StringField() 
    status = StringField(default="pending")   
    price = FloatField(default=0)

    raw_response = DictField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {"collection": "orders"}
