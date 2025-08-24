from flask import Blueprint, render_template, request, redirect, url_for
from models.server import Server, ConnectApi

apis_bp = Blueprint("apis", __name__, template_folder="../templates")

def _parse_headers(raw_headers: str):
    """
    Accepts 'Key: Value, X-Api-Key: abc' or multi-line.
    Returns list of {'key': 'Key', 'value': 'Value'} as expected by ConnectApi.headers (ListField of DictField).
    """
    if not raw_headers:
        return []
    parts = []
    # split on commas but also tolerate newlines
    items = []
    for line in raw_headers.replace("\r", "").split("\n"):
        items.extend([p for p in line.split(",") if p.strip()])
    for item in items:
        if ":" in item:
            k, v = item.split(":", 1)
            parts.append({"key": k.strip(), "value": v.strip()})
    return parts

@apis_bp.route("/", methods=["GET", "POST"])
def apis():
    if request.method == "POST":
        action = request.form.get("action")

        if action in ("add", "edit"):
            server_id = request.form.get("server_id")
            api_name = request.form.get("api_name")
            get_number_url = request.form.get("get_number_url")
            get_status_url = request.form.get("get_status_url")
            next_number_url = request.form.get("next_number_url")
            cancel_url = request.form.get("cancel_url")
            success_keyword = request.form.get("success_keyword")

            # advanced fields
            use_headers = bool(request.form.get("use_headers"))
            headers_raw = request.form.get("headers", "")
            headers = _parse_headers(headers_raw) if use_headers else []
            response_type = request.form.get("response_type") or "Text"
            try:
                auto_cancel_time = int(request.form.get("auto_cancel_time") or 5)
            except ValueError:
                auto_cancel_time = 5
            try:
                retry_time = int(request.form.get("retry_time") or 0)
            except ValueError:
                retry_time = 0

            server = Server.objects(id=server_id).first()

            if action == "add" and server:
                ConnectApi(
                    server=server,
                    api_name=api_name,
                    get_number_url=get_number_url,
                    get_status_url=get_status_url,
                    next_number_url=next_number_url,
                    cancel_url=cancel_url,
                    success_keyword=success_keyword,
                    use_headers=use_headers,
                    headers=headers,
                    response_type=response_type,
                    auto_cancel_time=auto_cancel_time,
                    retry_time=retry_time
                ).save()

            elif action == "edit":
                api_id = request.form.get("api_id")
                api = ConnectApi.objects(id=api_id).first()
                if api:
                    if server:
                        api.server = server
                    api.api_name = api_name
                    api.get_number_url = get_number_url
                    api.get_status_url = get_status_url
                    api.next_number_url = next_number_url
                    api.cancel_url = cancel_url
                    api.success_keyword = success_keyword
                    api.use_headers = use_headers
                    api.headers = headers
                    api.response_type = response_type
                    api.auto_cancel_time = auto_cancel_time
                    api.retry_time = retry_time
                    api.save()

        elif action == "delete":
            api_id = request.form.get("api_id")
            ConnectApi.objects(id=api_id).delete()

        return redirect(url_for("apis.apis"))

    apis = ConnectApi.objects()
    servers = Server.objects()
    return render_template("apis.html", apis=apis, servers=servers)
