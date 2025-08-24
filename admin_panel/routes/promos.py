# admin_panel/routes/promos.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
from models.promo import PromoCode, PromoRedemption
from models.server import Service
from datetime import datetime
import math
import csv
import io

promos_bp = Blueprint("promos", __name__, template_folder="../templates")


def _int_arg(name, default):
    try:
        return int(request.args.get(name, default) or default)
    except (ValueError, TypeError):
        return default


@promos_bp.route("/", methods=["GET", "POST"])
def promos():
    # POST actions: create / toggle / delete
    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            code = (request.form.get("code") or "").strip().upper()
            ptype = request.form.get("type") or "CREDIT_FCFS"
            title = request.form.get("title") or ""
            try:
                amount = float(request.form.get("amount") or 0)
            except ValueError:
                amount = 0.0
            try:
                percent = float(request.form.get("percent") or 0)
            except ValueError:
                percent = 0.0
            try:
                max_uses = int(request.form.get("max_uses") or 0)
            except ValueError:
                max_uses = 0
            try:
                per_user_limit = int(request.form.get("per_user_limit") or 1)
            except ValueError:
                per_user_limit = 1

            active = bool(request.form.get("active"))
            start_at = request.form.get("start_at")
            end_at = request.form.get("end_at")
            services = request.form.getlist("applicable_services")

            if not code or len(code) < 4:
                flash("Invalid code (min length 4).", "danger")
                return redirect(url_for("promos.promos"))

            pc = PromoCode(
                code=code,
                type=ptype,
                title=title,
                amount=amount,
                percent=percent,
                max_uses=max_uses,
                per_user_limit=per_user_limit,
                active=active,
                applicable_services=services or [],
            )
            try:
                if start_at:
                    pc.start_at = datetime.fromisoformat(start_at)
                if end_at:
                    pc.end_at = datetime.fromisoformat(end_at)
            except ValueError:
                flash("Invalid start/end datetime format. Use the picker.", "warning")

            try:
                pc.save()
                flash("Promo created.", "success")
            except Exception as e:
                flash(f"Could not create promo: {str(e)}", "danger")

        elif action == "toggle":
            pid = request.form.get("pid")
            if pid:
                p = PromoCode.objects(id=pid).first()
                if p:
                    p.update(set__active=(not p.active))
                    flash("Promo status toggled.", "info")
        elif action == "delete":
            pid = request.form.get("pid")
            if pid:
                PromoCode.objects(id=pid).delete()
                flash("Promo deleted.", "info")

        # redirect to preserve PRG pattern and include existing query params
        return redirect(url_for("promos.promos", **request.args.to_dict()))

    # --- GET: list, searches, pagination, export ---
    # Query params
    page = _int_arg("page", 1)
    per_page = _int_arg("per_page", 10)
    q = (request.args.get("q") or "").strip()
    filter_service = request.args.get("filter_service") or ""
    svc_q = (request.args.get("svc_q") or "").strip()
    rpage = _int_arg("rpage", 1)  # redemption page (optional)
    r_per_page = 10

    # Build filter for promos
    promos_query = PromoCode.objects
    if q:
        # filter by code (exact-ish) or title contains
        promos_query = promos_query.filter(__raw__={
            "$or": [
                {"code": {"$regex": q, "$options": "i"}},
                {"title": {"$regex": q, "$options": "i"}}
            ]
        })
    if filter_service:
        # match promos where applicable_services contains this service id
        promos_query = promos_query.filter(applicable_services=filter_service)

    total_promos = promos_query.count()
    total_pages = max(1, math.ceil(total_promos / per_page))

    # clamp page
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages

    # fetch page
    skip = (page - 1) * per_page
    promos = promos_query.order_by("-created_at").skip(skip).limit(per_page)

    # Build pagination urls list for template (range around current page)
    pages = []
    # window logic: show up to 7 page numbers
    start = max(1, page - 3)
    end = min(total_pages, start + 6)
    start = max(1, end - 6)
    for pnum in range(start, end + 1):
        args = request.args.to_dict()
        args["page"] = pnum
        pages.append({"num": pnum, "url": url_for("promos.promos", **args), "active": (pnum == page)})

    # Recent redemptions (paginated)
    redemption_q = PromoRedemption.objects
    total_redemptions = redemption_q.count()
    r_total_pages = max(1, math.ceil(total_redemptions / r_per_page))
    if rpage < 1:
        rpage = 1
    if rpage > r_total_pages:
        rpage = r_total_pages
    rskip = (rpage - 1) * r_per_page
    recent = redemption_q.order_by("-created_at").skip(rskip).limit(r_per_page)

    rpages = []
    rstart = max(1, rpage - 2)
    rend = min(r_total_pages, rstart + 4)
    rstart = max(1, rend - 4)
    for rp in range(rstart, rend + 1):
        args = request.args.to_dict()
        args["rpage"] = rp
        rpages.append({"num": rp, "url": url_for("promos.promos", **args), "active": (rp == rpage)})

    # Services: support server-side search for many services
    services_q = Service.objects
    if svc_q:
        services_q = services_q.filter(name__icontains=svc_q)
    services = services_q.order_by("name")
    
    return render_template(
        "promos.html",
        promos=promos,
        services=services,
        recent=recent,
        page=page,
        per_page=per_page,
        total_promos=total_promos,
        total_pages=total_pages,
        pages=pages,
        rpage=rpage,
        rpages=rpages,
        filter_service=filter_service,
        q=q,
        svc_q=svc_q,
    )
