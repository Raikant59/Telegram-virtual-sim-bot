from bot.handlers import start, buy, status, balance, back, admin_balance, admin_transactions,inline_services, purchase,cancel

def command_handlers(dispatcher):
    dispatcher.register_command("start", start.handle)
    dispatcher.register_command("buy", buy.handle)
    dispatcher.register_command("status", status.handle)
    dispatcher.register_command("add", admin_balance.handle)
    dispatcher.register_command("cut", admin_balance.handle)
    dispatcher.register_command("trnx", admin_transactions.handle)
    dispatcher.register_command("show_server", inline_services.show_server)  

def callback_handlers(dispatcher):
    # example: dispatcher.register_callback("confirm_buy", buy.confirm_callback)
    dispatcher.register_callback("balance", balance.handle)
    dispatcher.register_callback("back_main", back.handle)
    dispatcher.register_callback("trnx", admin_transactions.handle_callback)
    dispatcher.register_callback("purchase", purchase.handle)  
    dispatcher.register_callback("cancel", cancel.handle)
def inline_handlers(dispatcher):
    dispatcher.register_inline(inline_services.handle_inline)