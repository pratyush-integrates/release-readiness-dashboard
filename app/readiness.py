"""Readiness metrics computed from a release's issues."""
from collections import Counter
from dataclasses import dataclass

from .services.jira_service import Issue

BLOCKER_PRIORITIES = {"Blocker", "Highest"}


def is_blocker(issue: Issue) -> bool:
    if issue.status_category == "done":
        return False
    return (
        "block" in issue.status.lower()
        or issue.priority in BLOCKER_PRIORITIES
        or "blocker" in (label.lower() for label in issue.labels)
        or bool(issue.blocked_by)
    )


@dataclass
class Readiness:
    total: int
    done: int
    in_progress: int
    to_do: int
    percent_ready: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
    by_assignee: dict[str, int]
    blockers: list[Issue]


def compute(issues: list[Issue]) -> Readiness:
    categories = Counter(i.status_category for i in issues)
    total = len(issues)
    done = categories["done"]
    return Readiness(
        total=total,
        done=done,
        in_progress=categories["indeterminate"],
        to_do=categories["new"],
        percent_ready=round(100 * done / total) if total else 0,
        by_status=dict(Counter(i.status for i in issues).most_common()),
        by_priority=dict(Counter(i.priority for i in issues).most_common()),
        by_assignee=dict(Counter(i.assignee for i in issues).most_common()),
        blockers=[i for i in issues if is_blocker(i)],
    )
