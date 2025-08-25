purchase_text = '''🔔<b> New Number Alert </b> 🔔

Your user with user id of <code>{user_id}</code> has just bought {service_name} service from {server_name}.

👦<b>Username</b>: @{username}
⚜️<b>Name</b>: {name}
🔎<b>User id</b>: {user_id}
☎️<b>Number</b>: {number}
🌱<b>Number id</b>: {order_id}
🌐<b>Service Price</b>: {price} 💎
🧩<b>Discount Price</b>: {discount} 💎
💰<b>New User Balance</b>: {balance} 💎
🏦<b>New User API Balance</b>: 0.00 💎'''


cancel_text = '''🔔<b> Number Cancellation Alert </b> 🔔

Your user with user id of <code>{user_id}</code> has just cancelled mobile number {number}.

👦<b>Username</b>: @{username}
⚜️<b>Name</b>: {name}
🔎<b>User id</b>: {user_id}
☎️<b>Number</b>: {number}
🌱<b>Number id</b>: {order_id}
🌐<b>Service Price</b>: {price} 💎
🧩<b>Discount Price</b>: Not Applied
🌱<b>Refund</b>: {refund}
💰<b>New User Balance</b>: {balance} 💎
🏦<b>New User API Balance</b>: 0.00 💎'''


auto_cancel_text = '''🔔<b> Auto Cancellation Alert </b> 🔔

Your user with user id of <code>{user_id}</code> reached auto cancel time limit of {auto_cancel_time} minutes.

👦<b>Username</b>: @{username}
⚜️<b>Name</b>: {name}
🔎<b>User id</b>: {user_id}
☎️<b>Number</b>: {number}
🌱<b>Number id</b>: {order_id}
🌐<b>Service Price</b>: {price} 💎
🧩<b>Discount Price</b>: Not Applied
🌱<b>Refund</b>: {refund} 💎
💰<b>New User Balance</b>: {balance} 💎
🏦<b>New User API Balance</b>: 0.00 💎'''


recived_otp_text = '''🔔<b> New OTP Alert </b> 🔔

Your user with user id of <code>{user_id}</code> has just recived OTP for mobile number {number}.

👦<b>Username</b>: @{username}
⚜️<b>Name</b>: {name}
🔎<b>User id</b>: {user_id}
☎️<b>Number</b>: {number}
🌱<b>Number id</b>: {order_id}
🌐<b>Service Price</b>: {price} 💎
📩<b>Message</b>: {message}'''

promo_used_text = '''🔔 <b>Promo Used</b>

👤 <b>User</b>: @{username} (ID: {user_id})
🎟️ <b>Code</b>: {code}
📦 <b>Type</b>: {ptype}
💬 <b>Outcome</b>: {outcome}
'''
