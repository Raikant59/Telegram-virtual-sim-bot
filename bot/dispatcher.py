from bot.groups import command_handlers, callback_handlers

class Dispatcher:
    def __init__(self):
        self.command_handlers = {}
        self.callback_handlers = {}

    def register_command(self, cmd, func):
        self.command_handlers[cmd] = func

    def register_callback(self, data_key, func):
        self.callback_handlers[data_key] = func

    def handle_update(self, update, bot):
        """Manually route updates to correct handler"""
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            chat_id = update["message"]["chat"]["id"]

            if text.startswith("/"):
                cmd = text.split()[0][1:]
                if cmd in self.command_handlers:
                    self.command_handlers[cmd](bot, update["message"])
        
        elif "callback_query" in update:
            data = update["callback_query"]["data"]
            prefix = data.split(":")[0]
            if prefix in self.callback_handlers:
                self.callback_handlers[prefix](bot, update["callback_query"])

# global dispatcher instance
dispatcher = Dispatcher()

# Register groups
command_handlers(dispatcher)
callback_handlers(dispatcher)
