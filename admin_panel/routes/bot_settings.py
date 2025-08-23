from flask import Blueprint, render_template, request, redirect, url_for
from models.user import User
from models.order import Order
from models.admin import Admin
from utils.config import get_config, set_config

bot_settings_bp = Blueprint("bot_settings", __name__, template_folder="../templates", static_folder="../static")


@bot_settings_bp.route("/", methods=["GET", "POST"])
def bot_settings():
    if request.method == "POST":
        # Update support link
        support_url = request.form.get("support_url")
        if support_url is not None:
            set_config("support_url", support_url)

        # Add new admin
        new_admin_id = request.form.get("new_admin_id")
        new_admin_name = request.form.get("new_admin_name")
        if new_admin_id:
            Admin.objects(telegram_id=new_admin_id).update_one(
                set__telegram_id=new_admin_id,
                set__name=new_admin_name or "",
                upsert=True
            )

        # Remove admin
        remove_id = request.form.get("remove_id")
        if remove_id:
            Admin.objects(telegram_id=remove_id).delete()

        return redirect(url_for("bot_settings.bot_settings"))

    # GET request
    users_count = User.objects.count()
    orders_count = Order.objects.count()
    current_url = get_config("support_url", "")
    admins = Admin.objects()

    return render_template("bot_settings.html",
                           users_count=users_count,
                           orders_count=orders_count,
                           support_url=current_url,
                           admins=admins)
