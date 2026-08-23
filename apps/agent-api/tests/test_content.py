"""Tests for the content library API — GET /api/v1/content[/{asset_id}]."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

_ASSET_ROW = {
    "id": "horizons",
    "title": "HORIZONS",
    "subtitle": "Sci-Fi Drama Series · S2",
    "format": "tv_series",
    "status": "analyzed",
    "scene_count": 312,
    "opportunity_count": 47,
    "estimated_value_usd": 2_840_000.0,
    "updated_at": None,
}

_SCENE_ROW = {
    "id": "rooftop-reflection",
    "asset_id": "horizons",
    "episode": "S2E3",
    "name": "Rooftop Reflection",
    "summary": "A protagonist finishes a long day and looks over a futuristic city at dusk.",
    "brand_safety_score": 96.0,
    "narrative_weight": "High",
    "mood": "Dusk",
    "duration_seconds": 44,
}


def _mock_settings(configured: bool) -> MagicMock:
    settings = MagicMock()
    settings.clickhouse_configured = configured
    return settings


def test_list_content_returns_503_when_clickhouse_not_configured():
    with patch(
        "cineyield.routers.v1.content.get_settings",
        return_value=_mock_settings(False),
    ):
        resp = client.get("/api/v1/content")
    assert resp.status_code == 503


def test_get_content_returns_503_when_clickhouse_not_configured():
    with patch(
        "cineyield.routers.v1.content.get_settings",
        return_value=_mock_settings(False),
    ):
        resp = client.get("/api/v1/content/horizons")
    assert resp.status_code == 503


def test_list_content_returns_real_assets_with_scenes():
    with patch(
        "cineyield.routers.v1.content.get_settings",
        return_value=_mock_settings(True),
    ), patch(
        "cineyield.db.repository.list_content_assets",
        return_value=[_ASSET_ROW],
    ), patch(
        "cineyield.db.repository.get_scenes_for_asset",
        return_value=[_SCENE_ROW],
    ):
        resp = client.get("/api/v1/content")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == "horizons"
    assert "scenes" in item
    assert item["scenes"][0]["id"] == "rooftop-reflection"


def test_get_content_asset_not_found():
    with patch(
        "cineyield.routers.v1.content.get_settings",
        return_value=_mock_settings(True),
    ), patch(
        "cineyield.db.repository.get_content_asset",
        return_value=None,
    ):
        resp = client.get("/api/v1/content/does-not-exist")
    assert resp.status_code == 404


def test_get_content_asset_returns_asset_with_scenes():
    with patch(
        "cineyield.routers.v1.content.get_settings",
        return_value=_mock_settings(True),
    ), patch(
        "cineyield.db.repository.get_content_asset",
        return_value=_ASSET_ROW,
    ), patch(
        "cineyield.db.repository.get_scenes_for_asset",
        return_value=[_SCENE_ROW],
    ):
        resp = client.get("/api/v1/content/horizons")

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == "horizons"
    assert body["title"] == "HORIZONS"
    assert len(body["scenes"]) == 1
    assert body["scenes"][0]["name"] == "Rooftop Reflection"
