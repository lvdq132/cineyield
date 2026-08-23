"""Tests for contest-mode fallback guards and canonical score consistency.

These tests require no Gemini or ClickHouse — they're pure Python.
"""
# ruff: noqa: E402  # imports split into sections by test group
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Score canonical — 96.0 must be reproducible from seeded data
# ─────────────────────────────────────────────────────────────────────────────
from cineyield.agents.scoring import score_campaigns


def _aurelius_campaign() -> dict:
    return {
        "id": "aurelius-systems",
        "brand": "Aurelius Systems",
        "campaign_name": "Focus Without Limits",
        "product_line": "Aurelius One Wireless Headphones",
        "budget_min_usd": 150_000,
        "budget_max_usd": 250_000,
        "target_categories": ["Consumer Audio"],
        "excluded_contexts": [],
        "territories": ["US", "CA", "GB", "DE", "FR"],
        "visibility_seconds_min": 10,
        "visibility_seconds_max": 30,
    }


def _canonical_opportunity() -> dict:
    return {
        "id": "opp_horizons_rooftop_001",
        "category": "Consumer Audio",
        "screen_time_seconds": 26,
        "brand_safety_score": 96.0,
        "estimated_value_usd": 185_000.0,
        "territories": ["US", "CA", "GB"],
    }


def _canonical_scene() -> dict:
    return {
        "brand_safety_score": 96.0,
        "narrative_weight": "High",
        "mood": "Reflective",
    }


def _score_canonical() -> list:
    opp = _canonical_opportunity()
    scene = _canonical_scene()
    return score_campaigns(
        [_aurelius_campaign()],
        opportunity_category=opp["category"],
        opportunity_territories=opp["territories"],
        screen_time_seconds=opp["screen_time_seconds"],
        estimated_value_usd=opp["estimated_value_usd"],
        brand_safety_score=scene["brand_safety_score"],
        scene_mood=scene["mood"],
        scene_narrative_weight=scene["narrative_weight"],
    )


def test_canonical_aurelius_score_is_96():
    """Deterministic scoring must yield 96.0 for the HORIZONS/Aurelius pair."""
    scored = _score_canonical()
    assert scored, "Expected at least one scored campaign"
    top = scored[0]
    assert not top.is_blocked
    assert abs(top.composite - 96.0) < 0.5, (
        f"Expected Aurelius composite ≈ 96.0, got {top.composite}"
    )


def test_canonical_score_breakdown():
    """Each score component must be in the expected range."""
    top = _score_canonical()[0]
    assert top.context_fit >= 95, f"context_fit={top.context_fit}"
    assert top.category_fit == 100.0, f"category_fit={top.category_fit}"
    assert top.visibility_score >= 70, f"visibility={top.visibility_score}"
    assert top.brand_safety >= 90, f"brand_safety={top.brand_safety}"
    assert top.territory_score == 100.0, f"territory={top.territory_score}"


# ─────────────────────────────────────────────────────────────────────────────
# Contest-mode: CreativeGuardian must not fall back when Gemini fails
# ─────────────────────────────────────────────────────────────────────────────

from cineyield.agents.base import AgentContext
from cineyield.agents.creative_guardian import CreativeGuardian


def _make_ctx(scene=None, opportunity=None, campaign=None) -> AgentContext:
    return AgentContext(extra={
        "scene": scene or {"brand_safety_score": 90, "mood": "Reflective"},
        "opportunity": opportunity or {"id": "opp_1", "category": "Consumer Audio"},
        "campaign": campaign or {"id": "camp_1", "excluded_contexts": []},
    })


@pytest.mark.asyncio
async def test_creative_guardian_contest_mode_no_fallback():
    """In contest mode, a Gemini failure must raise — no silent deterministic fallback."""
    with patch("cineyield.agents.creative_guardian.get_settings") as mock_settings, \
         patch("cineyield.agents.creative_guardian._evaluate_with_gemini", new_callable=AsyncMock) as mock_gemini:

        settings = MagicMock()
        settings.gemini_configured = True
        settings.is_contest_mode = True
        mock_settings.return_value = settings

        mock_gemini.side_effect = RuntimeError("Vertex AI unavailable")

        with pytest.raises(RuntimeError, match="contest mode"):
            await CreativeGuardian().run(_make_ctx())


@pytest.mark.asyncio
async def test_creative_guardian_dev_mode_falls_back():
    """In dev mode (is_contest_mode=False), Gemini failure → deterministic fallback, no raise."""
    with patch("cineyield.agents.creative_guardian.get_settings") as mock_settings, \
         patch("cineyield.agents.creative_guardian._evaluate_with_gemini", new_callable=AsyncMock) as mock_gemini:

        settings = MagicMock()
        settings.gemini_configured = True
        settings.is_contest_mode = False
        mock_settings.return_value = settings

        mock_gemini.side_effect = RuntimeError("Gemini failed")

        result = await CreativeGuardian().run(_make_ctx())
        assert "overall_outcome" in result
        assert result["agent_version"] == "creative_guardian_v1_deterministic"


# ─────────────────────────────────────────────────────────────────────────────
# Contest-mode: DealAgent must not fall back on Gemini narrative failure
# ─────────────────────────────────────────────────────────────────────────────

from cineyield.agents.deal_agent import _generate_narrative


@pytest.mark.asyncio
async def test_deal_agent_narrative_contest_mode_raises():
    """In contest mode, failed Gemini narrative must raise rather than template fallback."""
    with patch("cineyield.agents.deal_agent.get_settings") as mock_settings, \
         patch("cineyield.agents.deal_agent._narrative_from_gemini", new_callable=AsyncMock) as mock_gemini:

        settings = MagicMock()
        settings.gemini_configured = True
        settings.is_contest_mode = True
        mock_settings.return_value = settings

        mock_gemini.side_effect = RuntimeError("Gemini timeout")

        with pytest.raises(RuntimeError, match="contest mode"):
            await _generate_narrative(
                scene={"name": "Scene"},
                opportunity={"object_label": "headphones"},
                campaign={"brand": "Aurelius", "product_line": "One"},
            )


@pytest.mark.asyncio
async def test_deal_agent_narrative_dev_mode_falls_back():
    """In dev mode, failed Gemini narrative returns template strings."""
    with patch("cineyield.agents.deal_agent.get_settings") as mock_settings, \
         patch("cineyield.agents.deal_agent._narrative_from_gemini", new_callable=AsyncMock) as mock_gemini:

        settings = MagicMock()
        settings.gemini_configured = True
        settings.is_contest_mode = False
        mock_settings.return_value = settings

        mock_gemini.side_effect = RuntimeError("Gemini timeout")

        brief, narrative = await _generate_narrative(
            scene={"name": "Rooftop", "mood": "reflective"},
            opportunity={"object_label": "wireless headphones", "screen_time_seconds": 26},
            campaign={"brand": "Aurelius", "product_line": "One"},
        )
        assert "Aurelius" in brief
        assert "wireless headphones" in narrative


# ─────────────────────────────────────────────────────────────────────────────
# Producer approval persistence (contract test — no real ClickHouse)
# ─────────────────────────────────────────────────────────────────────────────

from cineyield.db.repository import write_agent_event, write_revenue_event


def test_write_revenue_event_calls_insert(tmp_path):
    """write_revenue_event must call client.insert with the right table."""
    with patch("cineyield.db.repository.get_clickhouse_client") as mock_client:
        mock_insert = MagicMock()
        mock_client.return_value.insert = mock_insert

        event_id = write_revenue_event(
            proposal_id="prop_test_001",
            opportunity_id="opp_horizons_rooftop_001",
            campaign_id="aurelius-systems",
            asset_id="horizons",
            amount_usd=185_000.0,
            revenue_type="placement_fee",
        )

        assert isinstance(event_id, str) and len(event_id) == 36
        mock_insert.assert_called_once()
        call_args = mock_insert.call_args
        assert call_args[0][0] == "cineyield.revenue_events"
        row = call_args[0][1][0]
        assert row[1] == "prop_test_001"
        assert row[4] == "horizons"
        assert row[5] == 185_000.0


def test_write_agent_event_approved_persists():
    """write_agent_event for a producer approval must persist kind='approved'."""
    with patch("cineyield.db.repository.get_clickhouse_client") as mock_client:
        mock_insert = MagicMock()
        mock_client.return_value.insert = mock_insert

        event_id = write_agent_event(
            agent_name="producer",
            kind="approved",
            summary="Deal prop_test_001 approved by alice",
            opportunity_id="opp_horizons_rooftop_001",
            campaign_id="aurelius-systems",
            success=True,
        )

        assert isinstance(event_id, str) and len(event_id) == 36
        mock_insert.assert_called_once()
        row = mock_insert.call_args[0][1][0]
        assert "producer" in row
        assert "approved" in row


from cineyield.db.repository import approve_proposal


def test_approve_proposal_uses_parameterized_binding_not_fstring():
    """approve_proposal must bind proposal_id via ClickHouse parameters, never
    interpolate it into the SQL string (SQL injection guard)."""
    with patch("cineyield.db.repository.get_clickhouse_client") as mock_client:
        mock_command = MagicMock()
        mock_client.return_value.command = mock_command

        malicious_id = "x'; DROP TABLE cineyield.proposals; --"
        approve_proposal(malicious_id)

        mock_command.assert_called_once()
        call_args, call_kwargs = mock_command.call_args
        sql = call_args[0]
        # The raw id must never be interpolated into the SQL text itself.
        assert malicious_id not in sql
        assert "{proposal_id:String}" in sql
        assert call_kwargs.get("parameters") == {"proposal_id": malicious_id}


# ─────────────────────────────────────────────────────────────────────────────
# CampaignMatch schema — budget + territories pass through
# ─────────────────────────────────────────────────────────────────────────────

from cineyield.schemas.matching import CampaignMatch, ScoreBreakdown


def test_campaign_match_includes_budget_and_territories():
    """CampaignMatch must expose budget_min/max_usd and territories for frontend wiring."""
    m = CampaignMatch(
        campaign_id="camp_1",
        opportunity_id="opp_1",
        brand="Aurelius Systems",
        campaign_name="Focus Without Limits",
        product_line="Aurelius One",
        score=96.0,
        score_breakdown=ScoreBreakdown(
            context_fit=99, category_fit=100, visibility=80,
            brand_safety=96, territory=100, budget_and_terms=100,
        ),
        budget_min_usd=150_000,
        budget_max_usd=250_000,
        territories=["US", "CA", "GB"],
    )
    d = m.model_dump()
    assert d["budget_min_usd"] == 150_000
    assert d["budget_max_usd"] == 250_000
    assert d["territories"] == ["US", "CA", "GB"]


# ─────────────────────────────────────────────────────────────────────────────
# CINEYIELD_MODE=contest activates is_contest_mode
# ─────────────────────────────────────────────────────────────────────────────

from cineyield.config import Settings


def test_cineyield_mode_contest_activates_is_contest_mode():
    """CINEYIELD_MODE=contest must set is_contest_mode=True."""
    s = Settings(cineyield_mode="contest", contest_mode=False)
    assert s.is_contest_mode is True


def test_cineyield_mode_development_is_not_contest():
    """CINEYIELD_MODE=development (default) must NOT be contest mode."""
    s = Settings(cineyield_mode="development", contest_mode=False)
    assert s.is_contest_mode is False


def test_legacy_contest_mode_bool_activates_is_contest_mode():
    """Legacy contest_mode=True must still activate is_contest_mode for backwards compat."""
    s = Settings(cineyield_mode="development", contest_mode=True)
    assert s.is_contest_mode is True


# ─────────────────────────────────────────────────────────────────────────────
# Proposal approval source of truth — workflow_state, not revenue_events
# ─────────────────────────────────────────────────────────────────────────────

from cineyield.db.repository import get_proposal


def test_approve_proposal_runs_alter_table_update():
    """approve_proposal must issue ALTER TABLE UPDATE, not a revenue_events lookup.

    The proposal_id is bound via ClickHouse `parameters`, not interpolated into
    the SQL text (see test_approve_proposal_uses_parameterized_binding_not_fstring).
    """
    with patch("cineyield.db.repository.get_clickhouse_client") as mock_client:
        mock_cmd = MagicMock()
        mock_client.return_value.command = mock_cmd

        approve_proposal("prop_test_001")

        mock_cmd.assert_called_once()
        call_args, call_kwargs = mock_cmd.call_args
        sql = call_args[0]
        assert "ALTER TABLE" in sql
        assert "UPDATE" in sql
        assert "workflow_state" in sql
        assert "APPROVED" in sql
        assert call_kwargs.get("parameters") == {"proposal_id": "prop_test_001"}


def test_get_proposal_is_approved_reads_workflow_state_not_revenue_events():
    """is_approved must derive from workflow_state = 'APPROVED', not revenue_events count."""
    with patch("cineyield.db.repository.get_clickhouse_client") as mock_client:
        mock_query = MagicMock()
        mock_client.return_value.query = mock_query

        # Main row: workflow_state = APPROVED (no revenue_events lookup needed)
        def _query_side_effect(sql, **_kwargs):
            result = MagicMock()
            if "brand_brief" in sql:
                result.result_rows = []
            else:
                result.column_names = [
                    "id", "opportunity_id", "campaign_id", "brand_name",
                    "campaign_name", "placement_fee_usd", "workflow_state", "composed_at",
                ]
                result.result_rows = [
                    ["prop_001", "opp_1", "camp_1", "Aurelius", "Focus", 185000.0, "APPROVED", "2026-01-01"]
                ]
            return result

        mock_query.side_effect = _query_side_effect

        proposal = get_proposal("prop_001")
        assert proposal is not None
        assert proposal["is_approved"] is True
        assert proposal["workflow_state"] == "APPROVED"

        # Verify revenue_events was NOT queried
        for call in mock_query.call_args_list:
            sql = call[0][0] if call[0] else ""
            assert "revenue_events" not in sql, (
                "is_approved must not derive from revenue_events — use workflow_state"
            )


def test_get_proposal_not_approved_when_workflow_state_is_producer_review():
    """Proposal with workflow_state=PRODUCER_REVIEW must have is_approved=False."""
    with patch("cineyield.db.repository.get_clickhouse_client") as mock_client:
        mock_query = MagicMock()
        mock_client.return_value.query = mock_query

        def _query_side_effect(sql, **_kwargs):
            result = MagicMock()
            if "brand_brief" in sql:
                result.result_rows = []
            else:
                result.column_names = [
                    "id", "opportunity_id", "campaign_id", "brand_name",
                    "campaign_name", "placement_fee_usd", "workflow_state", "composed_at",
                ]
                result.result_rows = [
                    ["prop_002", "opp_1", "camp_1", "Aurelius", "Focus", 185000.0, "PRODUCER_REVIEW", "2026-01-01"]
                ]
            return result

        mock_query.side_effect = _query_side_effect

        proposal = get_proposal("prop_002")
        assert proposal is not None
        assert proposal["is_approved"] is False


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline thread-local state isolation
# ─────────────────────────────────────────────────────────────────────────────

def test_pipeline_state_is_isolated_between_runs():
    """_state() must return a fresh dict per run, not bleed between concurrent calls."""
    from cineyield.agents.pipeline import _init_state, _state

    _init_state()
    _state()["scene"] = {"scene_id": "run_1_scene"}

    # Simulate a second run in the same thread (would clobber with module-level global)
    _init_state()
    s2 = _state()
    assert "scene" not in s2, "State from previous run must not bleed into next run"


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline contest-mode: ADK failure must raise, not silently fall back
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_contest_mode_raises_on_adk_failure():
    """In contest mode, run_pipeline must raise if ADK fails — no direct-execution fallback."""
    from cineyield.agents.pipeline import run_pipeline

    with patch("cineyield.agents.pipeline.get_settings") as mock_settings, \
         patch("cineyield.agents.pipeline._build_adk_agent") as mock_build:

        settings = MagicMock()
        settings.gemini_configured = True
        settings.is_contest_mode = True
        settings.gemini_model = "gemini-2.0-flash"
        mock_settings.return_value = settings

        mock_build.side_effect = ImportError("google.adk not installed")

        with pytest.raises(RuntimeError, match="contest mode"):
            await run_pipeline({"video_path": "/tmp/fake.mp4", "asset_id": "test"})


@pytest.mark.asyncio
async def test_pipeline_dev_mode_falls_back_on_adk_failure():
    """In dev mode, run_pipeline falls back to direct execution when ADK fails."""
    from cineyield.agents.pipeline import run_pipeline

    with patch("cineyield.agents.pipeline.get_settings") as mock_settings, \
         patch("cineyield.agents.pipeline._build_adk_agent") as mock_build, \
         patch("cineyield.agents.pipeline._run_pipeline_direct") as mock_direct:

        settings = MagicMock()
        settings.gemini_configured = True
        settings.is_contest_mode = False
        settings.gemini_model = "gemini-2.0-flash"
        mock_settings.return_value = settings

        mock_build.side_effect = ImportError("google.adk not installed")
        mock_direct.return_value = "Pipeline completed via direct execution"

        result = await run_pipeline({"video_path": "/tmp/fake.mp4", "asset_id": "test"})
        mock_direct.assert_called_once()
        assert result["pipeline_version"] == "direct_fallback_v1"
