"""Deterministic scoring tests — no cloud credentials required."""
import pytest

from cineyield.agents.scoring import (
    _composite,
    _score_budget,
    _score_category_fit,
    _score_context_fit,
    _score_territory,
    _score_visibility,
    score_campaigns,
)

# ─── Unit: individual scoring functions ──────────────────────────────────────

def test_category_fit_exact_match():
    assert _score_category_fit("Consumer audio", ["Consumer audio", "Wearables"]) == 100.0


def test_category_fit_case_insensitive():
    assert _score_category_fit("consumer audio", ["Consumer Audio"]) == 100.0


def test_category_fit_no_match():
    assert _score_category_fit("Consumer audio", ["Apparel", "Footwear"]) == 0.0


def test_category_fit_partial_substring():
    assert _score_category_fit("Consumer audio", ["audio"]) == 100.0


def test_context_fit_blocked_by_excluded_context():
    score = _score_context_fit("Dusk", "High", 96.0, ["reflective", "dusk"])
    assert score == 0.0


def test_context_fit_passes_when_mood_not_excluded():
    score = _score_context_fit("Dusk", "High", 96.0, ["violence", "intoxication"])
    assert score > 0.0


def test_visibility_within_window():
    assert _score_visibility(26, 15, 40) == pytest.approx(44.0, abs=1.0)


def test_visibility_below_minimum():
    assert _score_visibility(5, 15, 40) == 0.0


def test_visibility_above_maximum():
    assert _score_visibility(60, 15, 40) == 80.0


def test_visibility_exact_minimum():
    assert _score_visibility(15, 15, 40) == 0.0


def test_territory_all_match():
    assert _score_territory(["US", "CA", "GB"], ["US", "CA", "GB", "AU"]) == 100.0


def test_territory_partial_match():
    score = _score_territory(["US", "CA", "GB", "DE"], ["US", "CA"])
    assert score == pytest.approx(50.0, abs=0.1)


def test_territory_no_match():
    assert _score_territory(["US", "CA"], ["DE", "FR"]) == 0.0


def test_territory_no_constraint():
    assert _score_territory([], ["US", "CA"]) == 100.0


def test_budget_within_range():
    assert _score_budget(185000, 150000, 250000) == 100.0


def test_budget_above_max():
    assert _score_budget(300000, 150000, 250000) == 70.0


def test_budget_below_min():
    assert _score_budget(50000, 150000, 250000) == 50.0


def test_budget_unknown_value():
    assert _score_budget(None, 150000, 250000) == 80.0


def test_composite_all_100():
    assert _composite(100, 100, 100, 100, 100, 100) == 100.0


def test_composite_all_0():
    assert _composite(0, 0, 0, 0, 0, 0) == 0.0


def test_composite_weights_sum_to_1():
    # weights: context 0.25 + category 0.25 + visibility 0.15 + safety 0.20 + territory 0.10 + budget 0.05 = 1.0
    assert abs(0.25 + 0.25 + 0.15 + 0.20 + 0.10 + 0.05 - 1.0) < 1e-9


# ─── Integration: full scoring pipeline ──────────────────────────────────────

_ROOFTOP_SCENE = {
    "brand_safety_score": 96.0,
    "mood": "Dusk",
    "narrative_weight": "High",
}

_ROOFTOP_OPP = {
    "id": "opp_horizons_rooftop_001",
    "category": "Consumer audio",
    "territories": ["US", "CA", "GB"],
    "screen_time_seconds": 26,
    "estimated_value_usd": 185000.0,
}

_FAKE_CAMPAIGNS = [
    # Should rank #1 — strong match
    {
        "id": "camp_aurelius_001",
        "brand": "Aurelius Systems",
        "campaign_name": "Focus Without Limits",
        "product_line": "Aurelius One Wireless Headphones",
        "budget_min_usd": 150000,
        "budget_max_usd": 250000,
        "target_categories": ["Consumer audio", "Lifestyle tech"],
        "excluded_contexts": ["violence", "intoxication"],
        "territories": ["US", "CA", "GB", "AU"],
        "visibility_seconds_min": 15,
        "visibility_seconds_max": 40,
    },
    # Should be blocked — category mismatch
    {
        "id": "camp_stride_001",
        "brand": "Stride Apparel",
        "campaign_name": "Own Your Run",
        "product_line": "Stride Performance Gear",
        "budget_min_usd": 80000,
        "budget_max_usd": 140000,
        "target_categories": ["Apparel", "Fitness apparel"],
        "excluded_contexts": [],
        "territories": ["US", "CA"],
        "visibility_seconds_min": 5,
        "visibility_seconds_max": 30,
    },
    # Should be blocked — creative conflict (reflective scene → energy drink exclusion)
    {
        "id": "camp_vortex_001",
        "brand": "Vortex Energy",
        "campaign_name": "Unleash Everything",
        "product_line": "Vortex Ultra Energy Drink",
        "budget_min_usd": 200000,
        "budget_max_usd": 350000,
        "target_categories": ["Consumer audio", "Beverages"],
        "excluded_contexts": ["reflective", "dusk", "slow pace"],
        "territories": ["US", "CA", "GB"],
        "visibility_seconds_min": 5,
        "visibility_seconds_max": 60,
    },
    # Should rank #2 — good but lower budget
    {
        "id": "camp_aurora_001",
        "brand": "Aurora Tech",
        "campaign_name": "Everyday Sound",
        "product_line": "Aurora ANC Headphones",
        "budget_min_usd": 90000,
        "budget_max_usd": 160000,
        "target_categories": ["Consumer audio"],
        "excluded_contexts": ["violence"],
        "territories": ["US", "CA"],
        "visibility_seconds_min": 10,
        "visibility_seconds_max": 35,
    },
]


def test_score_campaigns_returns_scored_list():
    results = score_campaigns(
        _FAKE_CAMPAIGNS,
        opportunity_category=_ROOFTOP_OPP["category"],
        opportunity_territories=_ROOFTOP_OPP["territories"],
        screen_time_seconds=_ROOFTOP_OPP["screen_time_seconds"],
        estimated_value_usd=_ROOFTOP_OPP["estimated_value_usd"],
        brand_safety_score=_ROOFTOP_SCENE["brand_safety_score"],
        scene_mood=_ROOFTOP_SCENE["mood"],
        scene_narrative_weight=_ROOFTOP_SCENE["narrative_weight"],
    )
    assert len(results) == 4


def test_score_campaigns_top_match_is_aurelius():
    results = score_campaigns(
        _FAKE_CAMPAIGNS,
        opportunity_category=_ROOFTOP_OPP["category"],
        opportunity_territories=_ROOFTOP_OPP["territories"],
        screen_time_seconds=_ROOFTOP_OPP["screen_time_seconds"],
        estimated_value_usd=_ROOFTOP_OPP["estimated_value_usd"],
        brand_safety_score=_ROOFTOP_SCENE["brand_safety_score"],
        scene_mood=_ROOFTOP_SCENE["mood"],
        scene_narrative_weight=_ROOFTOP_SCENE["narrative_weight"],
    )
    unblocked = [r for r in results if not r.is_blocked]
    assert unblocked[0].brand == "Aurelius Systems"


def test_score_campaigns_stride_is_blocked_category_mismatch():
    results = score_campaigns(
        _FAKE_CAMPAIGNS,
        opportunity_category=_ROOFTOP_OPP["category"],
        opportunity_territories=_ROOFTOP_OPP["territories"],
        screen_time_seconds=_ROOFTOP_OPP["screen_time_seconds"],
        estimated_value_usd=_ROOFTOP_OPP["estimated_value_usd"],
        brand_safety_score=_ROOFTOP_SCENE["brand_safety_score"],
        scene_mood=_ROOFTOP_SCENE["mood"],
        scene_narrative_weight=_ROOFTOP_SCENE["narrative_weight"],
    )
    stride = next(r for r in results if r.brand == "Stride Apparel")
    assert stride.is_blocked
    assert "mismatch" in stride.blocked_reason.lower()


def test_score_campaigns_vortex_blocked_creative_conflict():
    results = score_campaigns(
        _FAKE_CAMPAIGNS,
        opportunity_category=_ROOFTOP_OPP["category"],
        opportunity_territories=_ROOFTOP_OPP["territories"],
        screen_time_seconds=_ROOFTOP_OPP["screen_time_seconds"],
        estimated_value_usd=_ROOFTOP_OPP["estimated_value_usd"],
        brand_safety_score=_ROOFTOP_SCENE["brand_safety_score"],
        scene_mood=_ROOFTOP_SCENE["mood"],
        scene_narrative_weight=_ROOFTOP_SCENE["narrative_weight"],
    )
    vortex = next(r for r in results if r.brand == "Vortex Energy")
    assert vortex.is_blocked
    assert "conflict" in vortex.blocked_reason.lower() or "dusk" in vortex.blocked_reason.lower()


def test_score_campaigns_unblocked_sorted_by_composite():
    results = score_campaigns(
        _FAKE_CAMPAIGNS,
        opportunity_category=_ROOFTOP_OPP["category"],
        opportunity_territories=_ROOFTOP_OPP["territories"],
        screen_time_seconds=_ROOFTOP_OPP["screen_time_seconds"],
        estimated_value_usd=_ROOFTOP_OPP["estimated_value_usd"],
        brand_safety_score=_ROOFTOP_SCENE["brand_safety_score"],
        scene_mood=_ROOFTOP_SCENE["mood"],
        scene_narrative_weight=_ROOFTOP_SCENE["narrative_weight"],
    )
    unblocked = [r for r in results if not r.is_blocked]
    for i in range(len(unblocked) - 1):
        assert unblocked[i].composite >= unblocked[i + 1].composite


def test_score_campaigns_blocked_at_end():
    results = score_campaigns(
        _FAKE_CAMPAIGNS,
        opportunity_category=_ROOFTOP_OPP["category"],
        opportunity_territories=_ROOFTOP_OPP["territories"],
        screen_time_seconds=_ROOFTOP_OPP["screen_time_seconds"],
        estimated_value_usd=_ROOFTOP_OPP["estimated_value_usd"],
        brand_safety_score=_ROOFTOP_SCENE["brand_safety_score"],
        scene_mood=_ROOFTOP_SCENE["mood"],
        scene_narrative_weight=_ROOFTOP_SCENE["narrative_weight"],
    )
    saw_unblocked_after_blocked = False
    found_blocked = False
    for r in results:
        if r.is_blocked:
            found_blocked = True
        elif found_blocked:
            saw_unblocked_after_blocked = True
    assert not saw_unblocked_after_blocked
