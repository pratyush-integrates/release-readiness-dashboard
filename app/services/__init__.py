"""Builds the Jira and Confluence services from the app config."""
from flask import current_app

from .confluence_service import ConfluenceService
from .jira_service import JiraService


def jira() -> JiraService:
    cfg = current_app.config["RRD"]
    if "jira" not in current_app.extensions:
        current_app.extensions["jira"] = JiraService(
            cfg.jira_base_url, cfg.atlassian_email, cfg.atlassian_api_token, cfg.cache_seconds
        )
    return current_app.extensions["jira"]


def confluence() -> ConfluenceService:
    cfg = current_app.config["RRD"]
    if "confluence" not in current_app.extensions:
        current_app.extensions["confluence"] = ConfluenceService(
            cfg.confluence_base_url, cfg.atlassian_email, cfg.atlassian_api_token, cfg.confluence_space_key
        )
    return current_app.extensions["confluence"]
