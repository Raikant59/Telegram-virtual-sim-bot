# admin_panel/routes/promos.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.promo import PromoCode, PromoRedemption
from models.server import Service
from datetime import datetime

promos_bp = Blueprint("promos", __name__, template_folder="../templates")

@promos_bp.route("/", methods=["GET", "POST"])
def promos():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            code = (request.form.get("code") or "").strip().upper()
            ptype = request.form.get("type")
            title = request.form.get("title") or ""
            amount = float(request.form.get("amount") or 0)
            percent = float(request.form.get("percent") or 0)
            max_uses = int(request.form.get("max_uses") or 0)
            per_user_limit = int(request.form.get("per_user_limit") or 1)
            active = bool(request.form.get("active"))
            start_at = request.form.get("start_at")
            end_at = request.form.get("end_at")
            services = request.form.getlist("applicable_services")

            pc = PromoCode(
                code=code, type=ptype, title=title, amount=amount, percent=percent,
                max_uses=max_uses, per_user_limit=per_user_limit, active=active,
                applicable_services=services or []
            )
            if start_at:
                pc.start_at = datetime.fromisoformat(start_at)
            if end_at:
                pc.end_at = datetime.fromisoformat(end_at)
            pc.save()
            flash("Promo created", "success")
        elif action == "toggle":
            pid = request.form.get("pid")
            p = PromoCode.objects(id=pid).first()
            if p:
                p.update(active=not p.active)
        elif action == "delete":
            pid = request.form.get("pid")
            PromoCode.objects(id=pid).delete()
        return redirect(url_for("promos.promos"))

    promos = PromoCode.objects().order_by("-created_at")
    services = Service.objects()
    recent = PromoRedemption.objects().order_by("-created_at")[:100]
    return render_template("promos.html", promos=promos, services=services, recent=recent)
