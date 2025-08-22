from mongoengine import Document, StringField

class Config(Document):
    key = StringField(required=True, unique=True)
    value = StringField(required=True)

    meta = {"collection": "config"}
