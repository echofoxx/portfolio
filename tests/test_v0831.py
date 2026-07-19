from pathlib import Path

from bs4 import BeautifulSoup

from conftest import login


ROOT = Path(__file__).resolve().parents[1]


def test_linked_map_index_has_dedicated_height_sync_hook(client):
    login(client, "admin")
    response = client.get("/travel")
    assert response.status_code == 200
    page = BeautifulSoup(response.text, "html.parser")
    assert page.select_one("[data-travel-map] [data-map-index]") is not None


def test_linked_map_index_matches_canvas_and_scrolls_internally():
    script = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    stylesheet = (ROOT / "app/static/app.css").read_text(encoding="utf-8")
    assert "function syncMapIndexHeight()" in script
    assert "--map-canvas-height" in script
    assert "mapSizeObserver.observe(canvas)" in script
    assert "height:var(--map-canvas-height,410px)" in stylesheet
    assert ".travel-location-card>.top-location-list" in stylesheet
    assert "overflow-y:auto" in stylesheet
