from flask import Blueprint, render_template, request, redirect, url_for
from models.server import Server
from utils.countries import countries

servers_bp = Blueprint("servers", __name__, template_folder="../templates")

@servers_bp.route("/", methods=["GET", "POST"])
def servers():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            name = request.form.get("name")
            country = request.form.get("country")
            if name and country:
                Server(name=name, country=country).save()

        elif action == "delete":
            server_id = request.form.get("server_id")
            Server.objects(id=server_id).delete()

        return redirect(url_for("servers.servers"))

    servers = Server.objects()
    return render_template("servers.html", servers=servers, countries=countries)
