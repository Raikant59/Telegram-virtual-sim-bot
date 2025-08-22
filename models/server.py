from mongoengine import Document, StringField, ReferenceField, BooleanField, ListField, URLField, CASCADE, IntField, FloatField,UUIDField

import cuid

class Server(Document):
    name = StringField(required=True, unique=True)
    country = StringField(required=True)

    def __str__(self):
        return self.name

class ConnectApi(Document):
    server = ReferenceField(Server, reverse_delete_rule=CASCADE)

    api_name = StringField(required=True)
    use_headers = BooleanField(default=False)
    response_type = StringField(choices=["Text", "JSON"], default="Text")
    headers = ListField(StringField(), default=[])

    get_number_url = URLField(required=True)
    get_status_url = URLField(required=True)

    success_keyword = StringField(required=True)

    next_number_url = URLField(required=True)
    cancel_url = URLField(required=True)
    auto_cancel_time = IntField(default=5)
    retry_time = IntField(default=0)

    def __str__(self):
        return f"{self.api_name} ({self.server.name})"


class Service(Document):
    server = ReferenceField(Server, reverse_delete_rule=CASCADE)

    service_id = StringField(required=True, unique=True, default=lambda: cuid.cuid())
    name = StringField(required=True)
    logo = URLField(required=True)
    code = StringField(required=True)
    description = StringField(required=True)
    price = FloatField(required=True)
    disable_time = IntField(default=0)
    def __str__(self):
        return f"{self.name} - {self.server.name}"
