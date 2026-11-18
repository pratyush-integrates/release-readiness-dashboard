"""Regenerate the README screenshots in docs/screenshots/.

Start the app in mock mode first (fresh mock data, since this script moves a
ticket, adds a comment and publishes):

    MOCK_MODE=1 python run.py
    pip install playwright
    python scripts/capture_screenshots.py docs/screenshots

Uses the installed Google Chrome (channel="chrome"), so no browser download.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1])
BASE = "http://127.0.0.1:5000"

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1280, "height": 800}, device_scale_factor=1)

    # 1. Pick a project
    page.goto(BASE + "/")
    page.screenshot(path=OUT / "01-pick-project.png")

    # 2. Pick a fix version
    page.select_option("select[name=project]", "WEB")
    page.wait_for_selector("select[name=version]")
    page.select_option("select[name=version]", "2.4.0")
    page.screenshot(path=OUT / "02-pick-version.png")

    # 3. Dashboard overview (KPIs + charts)
    page.click("text=Show readiness")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)  # let Chart.js animations finish
    page.set_viewport_size({"width": 1280, "height": 620})
    page.screenshot(path=OUT / "03-dashboard-overview.png")
    page.set_viewport_size({"width": 1280, "height": 800})

    # 4. Blockers + release notes preview
    blockers = page.locator("section.card", has_text="Blockers").first
    notes = page.locator("section.card", has_text="Release notes preview").first
    blockers.scroll_into_view_if_needed()
    sy = page.evaluate("window.scrollY")
    box_a, box_b = blockers.bounding_box(), notes.bounding_box()
    box_a["y"] += sy; box_b["y"] += sy
    page.screenshot(
        path=OUT / "04-blockers-and-notes.png",
        full_page=True,
        clip={"x": 0, "y": box_a["y"] - 16, "width": 1280,
              "height": box_b["y"] + box_b["height"] - box_a["y"] + 32},
    )

    # 5. Full page
    page.screenshot(path=OUT / "dashboard.png", full_page=True)

    # 6. Move a blocker to Done
    sel = page.locator('select[data-key="WEB-108"]').first
    row = sel.locator("xpath=ancestor::tr")
    sel.focus()
    page.wait_for_function("document.querySelector('select[data-key=\"WEB-108\"]').options.length > 1")
    sel.select_option(value="Done")
    row.get_by_role("button", name="Move").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    page.set_viewport_size({"width": 1280, "height": 420})
    page.screenshot(path=OUT / "05-after-move.png")

    # 7. Comment on the remaining blocker
    page.set_viewport_size({"width": 1280, "height": 800})
    blockers = page.locator("section.card", has_text="Blockers").first
    row = page.locator('select[data-key="WEB-111"]').first.locator("xpath=ancestor::tr")
    row.locator("input[name=body]").fill("Root cause found, fix in review.")
    row.get_by_role("button", name="Comment").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    page.set_viewport_size({"width": 1280, "height": 420})
    page.screenshot(path=OUT / "06-comment-added.png")

    # 8. Publish to Confluence
    page.click("text=Publish release notes to Confluence")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)
    page.screenshot(path=OUT / "07-published.png")

    # 9. The Confluence page itself
    href = page.locator(".flash a").get_attribute("href")
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(href)
    page.screenshot(path=OUT / "08-confluence-page.png")

    browser.close()
print("done")
