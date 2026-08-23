import pytest
from pydantic import ValidationError

from cineyield.schemas import (
    AnalysisStatus,
    ContentAsset,
    ContentFormat,
    DecisionOutcome,
    DetectedObject,
    GuardrailCheck,
    RevenueEvent,
    SceneAnalysis,
    ScoreBreakdown,
)


def test_content_asset_valid():
    asset = ContentAsset(
        id="horizons",
        title="HORIZONS",
        subtitle="Sci-Fi Drama · S2",
        format=ContentFormat.TV_SERIES,
        status=AnalysisStatus.ANALYZED,
        scene_count=312,
        opportunity_count=47,
        estimated_value_usd=2_840_000.0,
    )
    assert asset.id == "horizons"
    assert asset.format == ContentFormat.TV_SERIES


def test_detected_object_confidence_bounds():
    obj = DetectedObject(label="Wireless Headphones", category="Consumer audio", confidence=94.0, is_primary=True)
    assert obj.confidence == 94.0

    with pytest.raises(ValidationError):
        DetectedObject(label="X", category="Y", confidence=101.0)

    with pytest.raises(ValidationError):
        DetectedObject(label="X", category="Y", confidence=-1.0)


def test_scene_analysis_valid():
    analysis = SceneAnalysis(
        scene_id="rooftop-reflection",
        asset_id="horizons",
        name="Rooftop Reflection",
        brand_safety_score=96.0,
        detected_objects=[
            DetectedObject(label="Wireless Headphones", category="Consumer audio", confidence=94.0, is_primary=True),
        ],
    )
    assert analysis.brand_safety_score == 96.0
    assert len(analysis.detected_objects) == 1


def test_score_breakdown_composite():
    sb = ScoreBreakdown(
        context_fit=100.0,
        category_fit=100.0,
        visibility=100.0,
        brand_safety=100.0,
        territory=100.0,
        budget_and_terms=100.0,
    )
    assert sb.composite == 100.0

    sb_zero = ScoreBreakdown(
        context_fit=0.0,
        category_fit=0.0,
        visibility=0.0,
        brand_safety=0.0,
        territory=0.0,
        budget_and_terms=0.0,
    )
    assert sb_zero.composite == 0.0


def test_score_breakdown_weighted():
    sb = ScoreBreakdown(
        context_fit=100.0,
        category_fit=0.0,
        visibility=0.0,
        brand_safety=0.0,
        territory=0.0,
        budget_and_terms=0.0,
    )
    assert abs(sb.composite - 25.0) < 0.001


def test_revenue_event_nonnegative():
    with pytest.raises(ValidationError):
        RevenueEvent(
            event_id="evt_001",
            proposal_id="prop_001",
            opportunity_id="opp_001",
            campaign_id="camp_001",
            asset_id="horizons",
            amount_usd=-100.0,
            occurred_at="2026-08-17T00:00:00Z",
        )


def test_guardrail_check_outcomes():
    g = GuardrailCheck(name="Rights Agent", outcome=DecisionOutcome.PASS, detail="3 of 4 cleared")
    assert g.outcome == DecisionOutcome.PASS
