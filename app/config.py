"""Settings loaded from environment variables (or a .env file)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Config:
    jira_base_url: str
    confluence_base_url: str
    atlassian_email: str
    atlassian_api_token: str
    confluence_space_key: str
    secret_key: str
    cache_seconds: float = 60
    mock_mode: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        email, token = os.getenv("ATLASSIAN_EMAIL", ""), os.getenv("ATLASSIAN_API_TOKEN", "")
        # Without credentials (or with MOCK_MODE=1) the app talks to the local mock server.
        mock_mode = os.getenv("MOCK_MODE", "").lower() in {"1", "true", "yes"} or not (email and token)
        if mock_mode:
            site = os.getenv("MOCK_URL", "http://127.0.0.1:5001").rstrip("/")
            email, token = email or "mock@example.com", token or "mock-token"
        else:
            site = os.getenv("ATLASSIAN_SITE", "").rstrip("/")
        return cls(
            jira_base_url=site,
            confluence_base_url=f"{site}/wiki",
            atlassian_email=email,
            atlassian_api_token=token,
            confluence_space_key=os.getenv("CONFLUENCE_SPACE_KEY", "REL"),
            secret_key=os.getenv("FLASK_SECRET_KEY", "dev-only-change-me"),
            cache_seconds=float(os.getenv("CACHE_SECONDS", "60")),
            mock_mode=mock_mode,
        )
