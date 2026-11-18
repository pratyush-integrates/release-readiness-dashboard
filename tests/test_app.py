"""End to end: the Flask app driving the real atlassian-python-api client against the mock server."""


def test_pick_project_and_version(client):
    page = client.get("/").get_data(as_text=True)
    assert "Web Storefront (WEB)" in page
    page = client.get("/?project=WEB").get_data(as_text=True)
    assert "2.4.0" in page and "2.5.0" in page


def test_release_dashboard(client):
    page = client.get("/release/WEB/2.4.0").get_data(as_text=True)
    assert "57%" in page  # 8 of 14 seeded WEB 2.4.0 issues are done
    assert "Payment provider timeout on 3DS challenge" in page
    assert "Blocked by WEB-108" in page


def test_transition_and_comment(client, mock_atlassian):
    mock, _ = mock_atlassian
    transitions = client.get("/api/issue/WEB-104/transitions").get_json()
    assert "Done" in [t["to"] for t in transitions]

    res = client.post("/issue/WEB-104/transition", data={"status": "Done", "next": "/release/WEB/2.4.0"})
    assert res.status_code == 302
    assert next(i for i in mock.state["issues"] if i["key"] == "WEB-104")["status"] == "Done"
    # The cache is cleared after an action, so the score moves straight away.
    assert "64%" in client.get("/release/WEB/2.4.0").get_data(as_text=True)

    client.post("/issue/WEB-104/comment", data={"body": "Verified on staging", "next": "/"})
    assert next(i for i in mock.state["issues"] if i["key"] == "WEB-104")["comments"] == ["Verified on staging"]


def test_publish_creates_then_updates_page(client, mock_atlassian):
    mock, _ = mock_atlassian
    res = client.post("/release/WEB/2.4.0/publish", follow_redirects=True)
    assert "Release notes page created" in res.get_data(as_text=True)
    res = client.post("/release/WEB/2.4.0/publish", follow_redirects=True)
    assert "Release notes page updated" in res.get_data(as_text=True)

    (page,) = mock.pages.values()
    assert page["title"] == "WEB 2.4.0 Release Notes"
    assert page["version"] == 2
    assert "<h2>Known issues</h2>" in page["body"] and "WEB-108" in page["body"]
