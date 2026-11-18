from app import readiness, release_notes
from app.services.jira_service import Issue


def make(key, status="To Do", category="new", itype="Story", priority="Medium", **kw):
    return Issue(key=key, summary=f"{key} summary", status=status, status_category=category,
                 priority=priority, assignee="Ana", issue_type=itype, **kw)


def test_percent_ready_counts_done_issues():
    issues = [make("A-1", "Done", "done"), make("A-2", "Done", "done"), make("A-3"), make("A-4", "In Progress", "indeterminate")]
    score = readiness.compute(issues)
    assert (score.total, score.done, score.in_progress, score.to_do) == (4, 2, 1, 1)
    assert score.percent_ready == 50


def test_empty_release_is_zero_percent():
    assert readiness.compute([]).percent_ready == 0


def test_blockers():
    assert readiness.is_blocker(make("A-1", "Blocked", "indeterminate"))
    assert readiness.is_blocker(make("A-2", priority="Highest"))
    assert readiness.is_blocker(make("A-3", labels=["blocker"]))
    assert readiness.is_blocker(make("A-4", blocked_by=["A-9"]))
    assert not readiness.is_blocker(make("A-5", "Done", "done", priority="Blocker"))
    assert not readiness.is_blocker(make("A-6"))


def test_release_note_sections():
    issues = [
        make("A-1", "Done", "done"),
        make("A-2", "Done", "done", itype="Bug"),
        make("A-3", itype="Bug"),
        make("A-4", priority="Blocker"),
        make("A-5"),
    ]
    s = release_notes.sections(issues)
    assert [i.key for i in s["features"]] == ["A-1"]
    assert [i.key for i in s["bug_fixes"]] == ["A-2"]
    assert [i.key for i in s["known_issues"]] == ["A-3", "A-4"]


def test_release_notes_html_escapes_summaries():
    issue = make("A-1", "Done", "done")
    issue.summary = "<script>x</script>"
    html = release_notes.build_html("A", "1.0", [issue], readiness.compute([issue]), lambda k: f"https://x/browse/{k}")
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "100% ready" in html
