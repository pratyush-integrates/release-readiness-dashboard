"""Start the dashboard. In mock mode the fake Jira/Confluence starts alongside it."""
import threading

from werkzeug.serving import make_server

from app import create_app

app = create_app()

if __name__ == "__main__":
    cfg = app.config["RRD"]
    if cfg.mock_mode:
        from urllib.parse import urlparse

        from mock.server import create_mock_app

        mock_url = urlparse(cfg.jira_base_url)
        mock = make_server(mock_url.hostname, mock_url.port, create_mock_app())
        threading.Thread(target=mock.serve_forever, daemon=True).start()
        print(f"Mock Jira + Confluence running at {cfg.jira_base_url}")
    app.run(port=5000, debug=True, use_reloader=False)
