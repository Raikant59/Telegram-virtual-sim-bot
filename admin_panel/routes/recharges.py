# admin_panel/routes/recharges.py
from flask import Blueprint, render_template, request, redirect, url_for
from models.recharge import Recharge
from models.user import User
from models.transaction import Transaction

recharges_bp = Blueprint("recharges", __name__, template_folder="../templates")

@recharges_bp.route("/", methods=["GET", "POST"])
def recharges():
    if request.method == "POST":
        action = request.form.get("action")
        rid = request.form.get("rid")
        recharge = Recharge.objects(id=rid).first()
        if recharge:
            if action == "approve" and recharge.status in ["pending", "awaiting_utr"]:
                user = recharge.user
                user.balance += recharge.amount
                user.total_recharged = (user.total_recharged or 0) + recharge.amount
                user.save()
                Transaction(
                    user=user, type="credit", amount=recharge.amount,
                    closing_balance=user.balance, note=f"recharge via {recharge.method}"
                ).save()
                recharge.mark("paid")
            elif action == "reject" and recharge.status in ["pending", "awaiting_utr"]:
                recharge.mark("rejected")
        return redirect(url_for("recharges.recharges"))

    allowed_methods = ["manual", "crypto", "bharatpay"]
    q = (request.args.get("q") or "").strip().lower()
    status = request.args.get("status") or ""
    qs = Recharge.objects

    # search by utr / provider_txn_id
    if q:
        qs = qs.filter(__raw__={"$or": [
            {"utr": {"$regex": q, "$options": "i"}},
            {"provider_txn_id": {"$regex": q, "$options": "i"}},
        ]})

    # filter by status if provided
    if status:
        qs = qs.filter(status=status)

    # ✅ restrict to allowed methods
    qs = qs.filter(method__in=allowed_methods)

    # order & limit
    recharges = qs.order_by("-created_at")[:300]

    return render_template("recharges.html", recharges=recharges, status=status, q=q)