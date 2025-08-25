from bot.groups import command_handlers, callback_handlers,inline_handlers,message_handlers
from models.user import User
from utils.check_user import ensure_membership

class Dispatcher:
    def __init__(self):
        self.command_handlers = {}
        self.callback_handlers = {}
        self.inline_handlers = []
        self.message_handlers = []
    
    def register_message(self, func):
        self.message_handlers.append(func)

    def register_command(self, cmd, func):
        self.command_handlers[cmd] = func

    def register_callback(self, data_key, func):
        self.callback_handlers[data_key] = func
    
    def register_inline(self, func):
        self.inline_handlers.append(func)

    def handle_update(self, update, bot):


        if "callback_query" in update:
            user_id = str(update["callback_query"]["from"]["id"])
            chat_id = update["callback_query"]["message"]["chat"]["id"]

            if not ensure_membership(bot, chat_id, user_id):
                return
            user = User.objects(telegram_id=user_id).first()
            if user and user.blocked:
                bot.send_message(update["message"]["chat"]["id"], "❌ You are banned by admin can't use this bot")
                return

        """Manually route updates to correct handler"""
        if "message" in update and "text" in update["message"]:
            text = update["message"]["text"]
            user_id = str(update["message"]["from"]["id"])
            chat_id = update["message"]["chat"]["id"]
            
            if not ensure_membership(bot, chat_id, user_id):
                return
            
            user = User.objects(telegram_id=user_id).first()
            if user and user.blocked:
                bot.send_message(update["message"]["chat"]["id"], "❌ You are banned by admin can't use this bot")
                return

            if text.startswith("/"):
                cmd = text.split()[0][1:]
                if cmd in self.command_handlers:
                    self.command_handlers[cmd](bot, update["message"])
            else:
                for fn in self.message_handlers:
                    fn(bot, update["message"])

        elif "callback_query" in update:
            data = update["callback_query"]["data"]
            prefix = data.split(":")[0]
            if prefix in self.callback_handlers:
                self.callback_handlers[prefix](bot, update["callback_query"])
        elif "inline_query" in update:  # ✅ handle inline queries
            for func in self.inline_handlers:
                func(bot, update["inline_query"])

# global dispatcher instance
dispatcher = Dispatcher()

# Register groups
command_handlers(dispatcher)
callback_handlers(dispatcher)
inline_handlers(dispatcher)
message_handlers(dispatcher)