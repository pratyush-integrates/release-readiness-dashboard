"""HTTP routes: pick a release, view readiness, act on tickets, publish notes."""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from requests import HTTPError

from . import readiness, release_notes, services

bp = Blueprint("dashboard", __name__)


def _error_text(exc: Exception) -> str:
    if isinstance(exc, HTTPError) and exc.response is not None:
        return f"{exc.response.status_code} {exc.response.reason}: {exc.response.text[:200]}"
    return str(exc)


@bp.get("/")
def index():
    project = request.args.get("project")
    try:
        projects = services.jira().projects()
        versions = services.jira().versions(project) if project else []
    except Exception as exc:  # surface connection/auth problems on the page
        flash(f"Could not reach Jira: {_error_text(exc)}", "error")
        projects, versions = [], []
    return render_template("index.html", projects=projects, versions=versions, project=project)


@bp.get("/release")
def release_redirect():
    return redirect(url_for(".release", project=request.args["project"], version=request.args["version"]))


@bp.get("/release/<project>/<version>")
def release(project, version):
    jira = services.jira()
    try:
        issues = jira.issues(project, version)
    except Exception as exc:
        flash(f"Could not load issues: {_error_text(exc)}", "error")
        return redirect(url_for(".index", project=project))
    score = readiness.compute(issues)
    charts = {"status": score.by_status, "priority": score.by_priority, "assignee": score.by_assignee}
    return render_template(
        "release.html",
        project=project,
        version=version,
        issues=issues,
        score=score,
        charts=charts,
        browse_url=jira.browse_url,
        notes=release_notes.sections(issues),
    )


@bp.get("/api/issue/<key>/transitions")
def issue_transitions(key):
    return jsonify(services.jira().transitions(key))


@bp.post("/issue/<key>/transition")
def transition(key):
    status = request.form["status"]
    try:
        services.jira().transition(key, status)
        flash(f"Moved {key} to {status}.", "success")
    except Exception as exc:
        flash(f"Could not move {key}: {_error_text(exc)}", "error")
    return redirect(request.form.get("next") or url_for(".index"))


@bp.post("/issue/<key>/comment")
def comment(key):
    body = request.form.get("body", "").strip()
    if body:
        try:
            services.jira().add_comment(key, body)
            flash(f"Comment added to {key}.", "success")
        except Exception as exc:
            flash(f"Could not comment on {key}: {_error_text(exc)}", "error")
    return redirect(request.form.get("next") or url_for(".index"))


@bp.post("/release/<project>/<version>/publish")
def publish(project, version):
    jira = services.jira()
    issues = jira.issues(project, version)
    html = release_notes.build_html(project, version, issues, readiness.compute(issues), jira.browse_url)
    try:
        page = services.confluence().publish(release_notes.page_title(project, version), html)
        verb = "created" if page["created"] else "updated"
        flash(f'Release notes page {verb}: <a href="{page["url"]}" target="_blank">open in Confluence</a>', "success html")
    except Exception as exc:
        flash(f"Could not publish to Confluence: {_error_text(exc)}", "error")
    return redirect(url_for(".release", project=project, version=version))
