from flask import Blueprint, render_template
from datetime import date
from models.user import User
from models.order import Order
from models.recharge import Recharge
from models.promo import PromoRedemption

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@dashboard_bp.route("/", methods=["GET"])
def dashboard():

    # --- Stats ---
    users_count = User.objects.count()
    today_users = User.objects(created_at__gte=date.today()).count()

    orders_count = Order.objects(status="completed").count()
    today_orders = Order.objects(status="completed", created_at__gte=date.today()).count()

    include_methods = ["manual", "crypto", "bharatpay", "admin_add"]

    total_recharge = Recharge.objects(
        status="paid",
        method__in=include_methods
    ).sum("amount") or 0

    today_recharge = Recharge.objects(
        status="paid",
        method__in=include_methods,
        created_at__gte=date.today()
    ).sum("amount") or 0

    # promo sum (wallet credits)
    promo_sum = PromoRedemption.objects(status="granted").sum("amount_credit") or 0
    promo_sum_today = PromoRedemption.objects(status="granted", created_at__gte=date.today()).sum("amount_credit") or 0

    # breakdown
    admin_cut_sum = Recharge.objects(status="paid", method="admin_cut").sum("amount") or 0
    admin_cut_sum_today = Recharge.objects(status="paid", method="admin_cut", created_at__gte=date.today()).sum("amount") or 0


    total_payments = total_recharge + promo_sum - admin_cut_sum
    today_payments = today_recharge + promo_sum_today - admin_cut_sum_today

    
    return render_template("dashboard.html",
                           users_count=users_count,
                           today_users=today_users,
                           orders_count=orders_count,
                           today_orders=today_orders,
                           total_payments=total_payments,
                           today_payments=today_payments,
                           )
