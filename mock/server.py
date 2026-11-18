"""A small fake Jira Cloud + Confluence Cloud that speaks the REST endpoints
atlassian-python-api calls. State lives in memory, seeded from seed.json.

Run: python -m mock.server  (listens on http://127.0.0.1:5001)
"""
import copy
import json
import re
from pathlib import Path

from flask import Flask, abort, jsonify, request

STATUSES = {
    "To Do": "new",
    "In Progress": "indeterminate",
    "In Review": "indeterminate",
    "Blocked": "indeterminate",
    "Done": "done",
}
SEED = json.loads(Path(__file__).with_name("seed.json").read_text())


def create_mock_app(seed: dict | None = None) -> Flask:
    app = Flask(__name__)
    state = copy.deepcopy(seed or SEED)
    issues = {i["key"]: i for i in state["issues"]}
    pages = {p["id"]: p for p in state["pages"]}
    base = lambda: request.host_url.rstrip("/")  # noqa: E731

    def status_json(name):
        return {"name": name, "statusCategory": {"key": STATUSES[name]}}

    def issue_json(i):
        links = [
            {"type": {"name": "Blocks"}, "inwardIssue": {"key": k, "fields": {"status": status_json(issues[k]["status"])}}}
            for k in i["blockedBy"]
            if k in issues
        ]
        return {
            "key": i["key"],
            "fields": {
                "summary": i["summary"],
                "status": status_json(i["status"]),
                "priority": {"name": i["priority"]},
                "assignee": {"displayName": i["assignee"]} if i["assignee"] else None,
                "issuetype": {"name": i["type"]},
                "labels": i["labels"],
                "fixVersions": [{"name": i["fixVersion"]}],
                "issuelinks": links,
            },
        }

    def get_issue(key):
        if key not in issues:
            abort(404)
        return issues[key]

    # ---------------- Jira ----------------
    @app.get("/rest/api/<v>/project/search")
    def projects(v):
        return jsonify({"values": state["projects"], "isLast": True})

    @app.get("/rest/api/<v>/project/<key>/versions")
    def versions(v, key):
        return jsonify([{"id": f"{key}-{n}", **ver} for n, ver in enumerate(state["versions"].get(key, []))])

    @app.get("/rest/api/3/search/jql")
    def search():
        jql = request.args.get("jql", "")
        project = re.search(r'project = "([^"]+)"', jql)
        version = re.search(r'fixVersion = "([^"]+)"', jql)
        found = [
            i for i in issues.values()
            if (not project or i["project"] == project.group(1)) and (not version or i["fixVersion"] == version.group(1))
        ]
        start = int(request.args.get("nextPageToken") or 0)
        size = int(request.args.get("maxResults") or 50)
        page = found[start:start + size]
        more = start + size < len(found)
        body = {"issues": [issue_json(i) for i in page], "isLast": not more}
        if more:
            body["nextPageToken"] = str(start + size)
        return jsonify(body)

    @app.get("/rest/api/<v>/issue/<key>/transitions")
    def transitions(v, key):
        current = get_issue(key)["status"]
        return jsonify({
            "transitions": [
                {"id": str(n), "name": name, "to": status_json(name)}
                for n, name in enumerate(STATUSES)
                if name != current
            ]
        })

    @app.post("/rest/api/<v>/issue/<key>/transitions")
    def do_transition(v, key):
        issue = get_issue(key)
        target = list(STATUSES)[int(request.json["transition"]["id"])]
        issue["status"] = target
        return "", 204

    @app.post("/rest/api/<v>/issue/<key>/comment")
    def add_comment(v, key):
        issue = get_issue(key)
        issue["comments"].append(request.json["body"])
        return jsonify({"id": str(len(issue["comments"])), "body": request.json["body"]}), 201

    @app.get("/rest/api/<v>/issue/<key>")
    def issue(v, key):
        return jsonify(issue_json(get_issue(key)) | {"comments": get_issue(key)["comments"]})

    @app.get("/browse/<key>")
    def browse(key):
        i = get_issue(key)
        comments = "".join(f"<li>{c}</li>" for c in i["comments"]) or "<li><em>No comments</em></li>"
        return f"<h1>{key}: {i['summary']}</h1><p>Status: {i['status']}</p><h2>Comments</h2><ul>{comments}</ul>"

    # ---------------- Confluence (REST API v2) ----------------
    spaces = [{"id": "9001", "key": key, "name": f"{key} space"} for key in state.get("spaces", ["REL"])]

    def page_json(p):
        return {
            "id": p["id"],
            "status": "current",
            "title": p["title"],
            "spaceId": p["spaceId"],
            "version": {"number": p["version"]},
            "body": {"storage": {"value": p["body"], "representation": "storage"}},
            "_links": {"webui": f"/pages/viewpage.action?pageId={p['id']}"},
        }

    @app.get("/wiki/api/v2/spaces")
    def list_spaces():
        keys = set(",".join(request.args.getlist("keys")).split(",")) - {""}
        return jsonify({"results": [s for s in spaces if not keys or s["key"] in keys], "_links": {}})

    @app.get("/wiki/api/v2/pages")
    def list_pages():
        space_id, title = request.args.get("space-id"), request.args.get("title")
        found = [
            p for p in pages.values()
            if (not space_id or p["spaceId"] == space_id) and (not title or p["title"] == title)
        ]
        return jsonify({"results": [page_json(p) for p in found], "_links": {}})

    @app.post("/wiki/api/v2/pages")
    def create_page():
        data = request.json
        if any(p["spaceId"] == data["spaceId"] and p["title"] == data["title"] for p in pages.values()):
            return jsonify({"errors": [{"title": "A page with this title already exists"}]}), 400
        page_id = str(1000 + len(pages))
        pages[page_id] = {
            "id": page_id,
            "spaceId": data["spaceId"],
            "title": data["title"],
            "body": data["body"]["storage"]["value"],
            "version": 1,
        }
        return jsonify(page_json(pages[page_id]))

    @app.get("/wiki/api/v2/pages/<page_id>")
    def get_page(page_id):
        if page_id not in pages:
            abort(404)
        return jsonify(page_json(pages[page_id]))

    @app.put("/wiki/api/v2/pages/<page_id>")
    def update_page(page_id):
        if page_id not in pages:
            abort(404)
        data = request.json
        p = pages[page_id]
        if data["version"]["number"] != p["version"] + 1:
            return jsonify({"errors": [{"title": "Version conflict"}]}), 409
        p.update(title=data.get("title", p["title"]), body=data["body"]["storage"]["value"], version=p["version"] + 1)
        return jsonify(page_json(p))

    @app.get("/wiki/pages/viewpage.action")
    def view_page():
        p = pages.get(request.args.get("pageId", ""))
        if not p:
            abort(404)
        return f"<h1>{p['title']}</h1><p><small>Version {p['version']} (mock Confluence)</small></p>{p['body']}"

    @app.errorhandler(404)
    def not_found(_):
        app.logger.warning("Mock has no route for %s %s", request.method, request.full_path)
        return jsonify({"errorMessages": [f"Not found: {request.path}"]}), 404

    app.state = state
    app.pages = pages
    return app


if __name__ == "__main__":
    create_mock_app().run(port=5001, debug=True)
