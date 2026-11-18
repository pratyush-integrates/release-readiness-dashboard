import threading

import pytest
from werkzeug.serving import make_server

from app import create_app
from app.config import Config
from mock.server import create_mock_app


@pytest.fixture
def mock_atlassian():
    """A fresh mock Jira + Confluence on a free port, for each test."""
    mock = create_mock_app()
    server = make_server("127.0.0.1", 0, mock)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield mock, f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def client(mock_atlassian):
    _, url = mock_atlassian
    config = Config(
        jira_base_url=url,
        confluence_base_url=f"{url}/wiki",
        atlassian_email="test@example.com",
        atlassian_api_token="token",
        confluence_space_key="REL",
        secret_key="test",
        cache_seconds=60,
        mock_mode=True,
    )
    app = create_app(config)
    app.testing = True
    return app.test_client()
