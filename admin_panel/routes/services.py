from flask import Blueprint, render_template, request, redirect, url_for
from models.server import Server, Service

services_bp = Blueprint("services", __name__, template_folder="../templates")
@services_bp.route("/", methods=["GET", "POST"])
def services():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            server_id = request.form.get("server_id")
            service = Service(
                server=Server.objects(id=server_id).first(),
                name=request.form.get("name"),
                logo=request.form.get("logo"),
                code=request.form.get("code"),
                description=request.form.get("description"),
                price=float(request.form.get("price")),
                disable_time=int(request.form.get("disable_time") or 0)
            )
            service.save()

        elif action == "edit":
            service_id = request.form.get("service_id")
            service = Service.objects(id=service_id).first()
            if service:
                service.update(
                    set__name=request.form.get("name"),
                    set__logo=request.form.get("logo"),
                    set__code=request.form.get("code"),
                    set__description=request.form.get("description"),
                    set__price=float(request.form.get("price")),
                    set__disable_time=int(request.form.get("disable_time") or 0),
                    set__server=Server.objects(id=request.form.get("server_id")).first()
                )

        elif action == "delete":
            service_id = request.form.get("service_id")
            Service.objects(id=service_id).delete()

        return redirect(url_for("services.services"))

    services = Service.objects()
    servers = Server.objects()
    return render_template("services.html", services=services, servers=servers)
