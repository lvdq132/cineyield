"""Regression tests for the real sponsor-brief discovery endpoint."""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _settings(configured: bool) -> MagicMock:
    settings = MagicMock()
    settings.clickhouse_configured = configured
    return settings


def _result() -> dict:
    return {
        "opportunity_id": "opp_horizons_rooftop_001",
        "scene_id": "rooftop-reflection",
        "asset_id": "horizons",
        "asset_title": "HORIZONS",
        "asset_subtitle": "Sci-Fi Drama Series · S2",
        "episode": "S2E3",
        "scene_name": "Rooftop Reflection",
        "scene_summary": "A protagonist looks over a city at dusk.",
        "mood": "Dusk",
        "narrative_weight": "High",
        "category": "Consumer Audio",
        "object_label": "Wireless Headphones",
        "timecode_start": "00:12",
        "timecode_end": "00:38",
        "screen_time_seconds": 26,
        "naturalness_score": 94.0,
        "brand_safety_score": 96.0,
        "rights_status": "clear",
        "estimated_value_usd": 185_000.0,
        "fit_score": 91.4,
    }


def test_sponsor_search_returns_clickhouse_inventory_with_provenance():
    with patch(
        "cineyield.routers.v1.sponsor_search.get_settings",
        return_value=_settings(True),
    ), patch(
        "cineyield.routers.v1.sponsor_search.repository.search_sponsor_ready_scenes",
        return_value=[_result()],
    ) as search:
        response = client.get(
            "/api/v1/sponsor-search",
            params={
                "category": "Consumer Audio",
                "objective": "Launch a product",
                "budget": 200000,
                "territory": "CA",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["qualified_count"] == 1
    assert body["results"][0]["opportunity_id"] == "opp_horizons_rooftop_001"
    assert body["results"][0]["marketplace_path"].startswith("/marketplace?")
    assert "94% naturalness" in body["results"][0]["rationale"]
    assert body["provenance"]["retrieval"] == "ClickHouse"
    search.assert_called_once_with(
        category="Consumer Audio", working_budget_usd=200000.0, limit=8
    )


def test_sponsor_search_rejects_unsupported_category():
    with patch(
        "cineyield.routers.v1.sponsor_search.get_settings",
        return_value=_settings(True),
    ):
        response = client.get(
            "/api/v1/sponsor-search", params={"category": "Space tourism"}
        )

    assert response.status_code == 422
    assert "Consumer Audio" in response.json()["detail"]["supported_categories"]


def test_sponsor_search_requires_clickhouse():
    with patch(
        "cineyield.routers.v1.sponsor_search.get_settings",
        return_value=_settings(False),
    ):
        response = client.get("/api/v1/sponsor-search")

    assert response.status_code == 503
