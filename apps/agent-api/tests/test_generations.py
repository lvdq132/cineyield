"""Regression coverage for the producer-controlled generative-media workflow."""
from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _settings() -> MagicMock:
    settings = MagicMock()
    settings.clickhouse_configured = True
    settings.nano_banana_model = "gemini-3.1-flash-image"
    settings.veo_model = "veo-3.1-generate-001"
    return settings


def _context(*, approved: bool = True) -> dict:
    return {
        "proposal_id": "prop_1",
        "scene_id": "scene_1",
        "opportunity_id": "opp_1",
        "campaign_id": "camp_1",
        "workflow_state": "APPROVED" if approved else "PRODUCER_REVIEW",
        "brand_name": "Aurelius Systems",
        "product_line": "Aurelius One Wireless Headphones",
        "media": {
            "frame_uri": "gs://bucket/frame.jpg",
            "segment_video_uri": "gs://bucket/segment.mp4",
        },
    }


def test_workflow_exposes_exact_source_media_and_generation_gate():
    with patch(
        "cineyield.routers.v1.generations.get_settings", return_value=_settings()
    ), patch(
        "cineyield.routers.v1.generations._resolve_deal_id", return_value="prop_1"
    ), patch(
        "cineyield.routers.v1.generations.repository.get_generation_context",
        return_value=_context(),
    ), patch(
        "cineyield.routers.v1.generations.repository.list_generation_jobs", return_value=[]
    ):
        response = client.get("/api/v1/generations/proposals/prop_1")

    assert response.status_code == 200
    body = response.json()
    assert body["original_frame_url"] == "/api/v1/scenes/scene_1/media/frame"
    assert body["original_video_url"] == "/api/v1/scenes/scene_1/media/segment"
    assert body["deal_approved"] is True
    assert body["video_unlocked"] is False


def test_nano_banana_is_blocked_until_commercial_terms_are_approved():
    with patch(
        "cineyield.routers.v1.generations.get_settings", return_value=_settings()
    ), patch(
        "cineyield.routers.v1.generations._resolve_deal_id", return_value="prop_1"
    ), patch(
        "cineyield.routers.v1.generations.repository.get_generation_context",
        return_value=_context(approved=False),
    ), patch(
        "cineyield.routers.v1.generations.generate_branded_frame"
    ) as generate:
        response = client.post(
            "/api/v1/generations/proposals/prop_1/image",
            json={"placement_instructions": "Keep the actor unobstructed."},
        )

    assert response.status_code == 409
    generate.assert_not_called()


def test_generation_job_query_avoids_clickhouse_nested_aggregate_alias():
    fake_client = MagicMock()
    result = MagicMock()
    now = datetime(2026, 8, 29, 12, 0, 0)
    result.column_names = [
        "id", "proposal_id", "scene_id", "opportunity_id", "campaign_id",
        "kind", "status", "decision", "model", "prompt",
        "placement_instructions", "creative_guardrails", "source_video_uri",
        "source_frame_uri", "output_uri", "operation_name", "generation_number",
        "error", "created_at", "latest_updated_at",
    ]
    result.result_rows = [[
        "img_1", "prop_1", "scene_1", "opp_1", "camp_1", "IMAGE",
        "COMPLETED", "APPROVED", "gemini-3.1-flash-image", "prompt", "place it",
        "[]", "gs://bucket/segment.mp4", "gs://bucket/frame.jpg",
        "gs://bucket/output.png", "", 1, "", now, now,
    ]]
    fake_client.query.return_value = result

    with patch(
        "cineyield.db.repository.get_clickhouse_client", return_value=fake_client
    ):
        from cineyield.db.repository import get_generation_job

        job = get_generation_job("img_1")

    sql = fake_client.query.call_args[0][0]
    assert "max(updated_at) AS latest_updated_at" in sql
    assert "max(updated_at) AS updated_at" not in sql
    assert job is not None
    assert job["updated_at"] == now.isoformat()
    assert job["decision"] == "APPROVED"
