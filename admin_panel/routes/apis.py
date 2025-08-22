from flask import Blueprint, render_template, request, redirect, url_for
from models.server import Server, ConnectApi

apis_bp = Blueprint("apis", __name__, template_folder="../templates")

@apis_bp.route("/", methods=["GET", "POST"])
def apis():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add":
            server_id = request.form.get("server_id")
            api_name = request.form.get("api_name")
            get_number_url = request.form.get("get_number_url")
            get_status_url = request.form.get("get_status_url")
            next_number_url = request.form.get("next_number_url")
            cancel_url = request.form.get("cancel_url")
            success_keyword = request.form.get("successKeyword")

            server = Server.objects(id=server_id).first()
            if server:
                ConnectApi(
                    server=server,
                    api_name=api_name,
                    get_number_url=get_number_url,
                    get_status_url=get_status_url,
                    next_number_url=next_number_url,
                    cancel_url=cancel_url,
                    sucessKeyword=success_keyword
                ).save()

        elif action == "delete":
            api_id = request.form.get("api_id")
            ConnectApi.objects(id=api_id).delete()

        return redirect(url_for("apis.apis"))

    apis = ConnectApi.objects()
    servers = Server.objects()
    return render_template("apis.html", apis=apis, servers=servers)
