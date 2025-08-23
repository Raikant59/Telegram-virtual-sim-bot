from flask import Blueprint, render_template, request, redirect, url_for, flash
from datetime import date
from models.user import User
from models.order import Order
from models.recharge import Recharge

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

@dashboard_bp.route("/", methods=["GET"])
def dashboard():

    # --- Stats ---
    users_count = User.objects.count()
    today_users = User.objects(created_at__gte=date.today()).count()

    orders_count = Order.objects(status="completed").count()
    today_orders = Order.objects(status="completed", created_at__gte=date.today()).count()

    total_payments = Recharge.objects(status="paid").sum("amount") or 0
    today_payments = Recharge.objects(status="paid", created_at__gte=date.today()).sum("amount") or 0

    
    return render_template("dashboard.html",
                           users_count=users_count,
                           today_users=today_users,
                           orders_count=orders_count,
                           today_orders=today_orders,
                           total_payments=total_payments,
                           today_payments=today_payments,
                           )
