"""Jira Cloud access through atlassian-python-api.

Only the handful of calls the dashboard needs are exposed here, so the rest
of the app never touches the library directly and a mock can stand in.
"""
from dataclasses import dataclass, field

from atlassian import Jira

from ..cache import TTLCache

ISSUE_FIELDS = ["summary", "status", "priority", "assignee", "issuetype", "labels", "fixVersions", "issuelinks"]


@dataclass
class Issue:
    key: str
    summary: str
    status: str
    status_category: str  # "new", "indeterminate" or "done"
    priority: str
    assignee: str
    issue_type: str
    labels: list[str] = field(default_factory=list)
    blocked_by: list[str] = field(default_factory=list)

    @classmethod
    def from_api(cls, raw: dict) -> "Issue":
        f = raw.get("fields", {})
        status = f.get("status") or {}
        blocked_by = [
            link["inwardIssue"]["key"]
            for link in f.get("issuelinks") or []
            if link.get("type", {}).get("name") == "Blocks"
            and "inwardIssue" in link
            and link["inwardIssue"].get("fields", {}).get("status", {}).get("statusCategory", {}).get("key") != "done"
        ]
        return cls(
            key=raw["key"],
            summary=f.get("summary", ""),
            status=status.get("name", "Unknown"),
            status_category=(status.get("statusCategory") or {}).get("key", "new"),
            priority=(f.get("priority") or {}).get("name", "None"),
            assignee=(f.get("assignee") or {}).get("displayName", "Unassigned"),
            issue_type=(f.get("issuetype") or {}).get("name", "Task"),
            labels=f.get("labels") or [],
            blocked_by=blocked_by,
        )


class JiraService:
    def __init__(self, url: str, email: str, token: str, cache_seconds: float = 60):
        self.base_url = url
        self.client = Jira(url=url, username=email, password=token, cloud=True)
        self.cache = TTLCache(cache_seconds)

    def projects(self) -> list[dict]:
        return self.cache.get_or_set(
            "projects", lambda: [{"key": p["key"], "name": p["name"]} for p in self.client.projects()]
        )

    def versions(self, project_key: str) -> list[dict]:
        return self.cache.get_or_set(
            ("versions", project_key),
            lambda: [
                {"id": v["id"], "name": v["name"], "released": v.get("released", False)}
                for v in self.client.get_project_versions(project_key)
            ],
        )

    def issues(self, project_key: str, version: str) -> list[Issue]:
        return self.cache.get_or_set(("issues", project_key, version), lambda: self._fetch_issues(project_key, version))

    def _fetch_issues(self, project_key: str, version: str) -> list[Issue]:
        jql = f'project = "{project_key}" AND fixVersion = "{version}" ORDER BY priority DESC, key ASC'
        issues, token = [], None
        while True:
            page = self.client.enhanced_jql(jql, fields=ISSUE_FIELDS, nextPageToken=token, limit=100)
            issues += [Issue.from_api(raw) for raw in page.get("issues", [])]
            token = page.get("nextPageToken")
            if not token or page.get("isLast", True):
                return issues

    def transitions(self, issue_key: str) -> list[dict]:
        return [{"id": str(t["id"]), "name": t["name"], "to": t["to"]} for t in self.client.get_issue_transitions(issue_key)]

    def transition(self, issue_key: str, status_name: str) -> None:
        self.client.set_issue_status(issue_key, status_name)
        self.cache.clear()

    def add_comment(self, issue_key: str, body: str) -> None:
        self.client.issue_add_comment(issue_key, body)
        self.cache.clear()

    def browse_url(self, issue_key: str) -> str:
        return f"{self.base_url}/browse/{issue_key}"
