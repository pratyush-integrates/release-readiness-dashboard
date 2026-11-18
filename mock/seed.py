"""Generates the mock seed data (mock/seed.json). Run: python -m mock.seed"""
import json
from pathlib import Path

PEOPLE = ["Priya Shah", "Marco Rossi", "Aiko Tanaka", "Sam Okafor", None]

ISSUES = {
    ("WEB", "2.4.0"): [
        ("Story", "Done", "High", "Checkout: save card for later"),
        ("Story", "Done", "Medium", "Order history filters"),
        ("Story", "In Review", "Medium", "Dark mode for account pages"),
        ("Story", "In Progress", "High", "Gift card redemption"),
        ("Task", "Done", "Low", "Upgrade analytics SDK"),
        ("Bug", "Done", "High", "Cart total wrong with mixed currencies"),
        ("Bug", "Done", "Medium", "Search box loses focus on mobile Safari"),
        ("Bug", "Blocked", "Highest", "Payment provider timeout on 3DS challenge"),
        ("Bug", "To Do", "Medium", "Broken image on empty wishlist"),
        ("Story", "To Do", "Low", "Recently viewed carousel"),
        ("Bug", "In Progress", "Blocker", "Session expires during checkout"),
        ("Task", "Done", "Medium", "Release feature flags cleanup"),
        ("Story", "Done", "Medium", "Address autocomplete"),
        ("Bug", "Done", "Low", "Typo in password reset email"),
    ],
    ("WEB", "2.5.0"): [
        ("Story", "To Do", "Medium", "Product comparison view"),
        ("Story", "To Do", "High", "One-click reorder"),
        ("Bug", "To Do", "Low", "Footer links misaligned on tablets"),
    ],
    ("MOB", "1.8.0"): [
        ("Story", "Done", "High", "Push notification preferences"),
        ("Story", "Done", "Medium", "Biometric login"),
        ("Bug", "Done", "High", "Crash when rotating on photo upload"),
        ("Bug", "In Progress", "Medium", "Offline banner flickers"),
        ("Task", "Done", "Low", "Bump minimum iOS to 16"),
        ("Story", "In Review", "Medium", "Widget for order tracking"),
    ],
}


def build() -> dict:
    data = {
        "projects": [{"key": "WEB", "name": "Web Storefront"}, {"key": "MOB", "name": "Mobile App"}],
        "versions": {
            "WEB": [{"name": "2.3.0", "released": True}, {"name": "2.4.0", "released": False}, {"name": "2.5.0", "released": False}],
            "MOB": [{"name": "1.8.0", "released": False}],
        },
        "issues": [],
        "pages": [],
    }
    counters = {}
    for (project, version), rows in ISSUES.items():
        for n, (itype, status, priority, summary) in enumerate(rows):
            counters[project] = counters.get(project, 100) + 1
            data["issues"].append({
                "key": f"{project}-{counters[project]}",
                "project": project,
                "fixVersion": version,
                "type": itype,
                "status": status,
                "priority": priority,
                "assignee": PEOPLE[n % len(PEOPLE)],
                "summary": summary,
                "labels": [],
                "blockedBy": [],
                "comments": [],
            })
    # WEB-103 (In Review) waits on the blocked payment bug WEB-108.
    for issue in data["issues"]:
        if issue["key"] == "WEB-103":
            issue["blockedBy"] = ["WEB-108"]
    return data


if __name__ == "__main__":
    path = Path(__file__).with_name("seed.json")
    path.write_text(json.dumps(build(), indent=2))
    print(f"Wrote {path}")
