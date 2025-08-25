from bot.handlers import start, buy, status, balance, back, admin_balance,admin_numbers,admin_ban,admin_broadcast, admin_transactions,inline_services, purchase,cancel,admin_panel,recharge,promo,transactions, profile,history

def command_handlers(dispatcher):
    dispatcher.register_command("start", start.handle)
    dispatcher.register_command("buy", buy.handle)
    dispatcher.register_command("status", status.handle)
    dispatcher.register_command("add", admin_balance.handle)
    dispatcher.register_command("cut", admin_balance.handle)
    dispatcher.register_command("trnx", admin_transactions.handle)
    dispatcher.register_command("nums", admin_numbers.handle)
    dispatcher.register_command("show_server", inline_services.show_server)
    dispatcher.register_command("admin", admin_panel.handle)
    dispatcher.register_command("ban", admin_ban.handle)
    dispatcher.register_command("unban", admin_ban.handle)
    dispatcher.register_command("broadcast", admin_broadcast.handle)

def callback_handlers(dispatcher):
    # example: dispatcher.register_callback("confirm_buy", buy.confirm_callback)
    dispatcher.register_callback("balance", balance.handle)
    dispatcher.register_callback("back_main", back.handle)
    dispatcher.register_callback("trnx", admin_transactions.handle_callback)
    dispatcher.register_callback("purchase", purchase.handle)  
    dispatcher.register_callback("cancel", cancel.handle)
    dispatcher.register_callback("recharge", recharge.menu)          # open menu
    dispatcher.register_callback("rcg", recharge.action_callback)    # internal actions (approve/reject buttons for admins, etc.)
    dispatcher.register_callback("utr", recharge.ask_utr_callback)   # put user into UTR reply mode
    dispatcher.register_callback("amt", recharge.amount_callback)    # set amount for flows
    dispatcher.register_callback("pay", recharge.pay_callback)       # start payment (crypto/bharatpay/manual)
    dispatcher.register_callback("promo", promo.menu) 
    dispatcher.register_callback("transactions", transactions.handle)
    dispatcher.register_callback("profile", profile.handle)
    dispatcher.register_callback("history", history.handle)
    dispatcher.register_callback("nums", admin_numbers.handle_callback)
 
def inline_handlers(dispatcher):
    dispatcher.register_inline(inline_services.handle_inline)

def message_handlers(dispatcher):
    dispatcher.register_message(recharge.capture_utr_message)
    dispatcher.register_message(recharge.capture_custom_amount)
    dispatcher.register_message(promo.capture_code)