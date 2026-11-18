"""Confluence Cloud access through atlassian-python-api (REST API v2)."""
from atlassian import ConfluenceV2


class ConfluenceService:
    def __init__(self, url: str, email: str, token: str, space_key: str):
        self.base_url = url
        self.space_key = space_key
        self.client = ConfluenceV2(url=url, username=email, password=token, cloud=True)

    def publish(self, title: str, body_html: str) -> dict:
        """Create the page, or update it if a page with this title already exists in the space."""
        space_id = self.client.get_space_by_key(self.space_key)["id"]
        page_id = self.client.get_page_id(self.space_key, title)
        if page_id:
            page = self.client.update_page(
                page_id, title=title, body=body_html, status="current", representation="storage"
            )
            created = False
        else:
            page = self.client.create_page(space_id=space_id, title=title, body=body_html, representation="storage")
            created = True
        return {"id": page["id"], "created": created, "url": f"{self.base_url}/pages/viewpage.action?pageId={page['id']}"}
