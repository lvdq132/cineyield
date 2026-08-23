"""Tests for deterministic agents — no Gemini or ClickHouse required."""

from cineyield.agents.creative_guardian import _evaluate_deterministic
from cineyield.agents.deal_agent import _calculate_fee, _narrative_from_template
from cineyield.agents.rights_agent import check_rights
from cineyield.schemas.decisions import DecisionOutcome

# ─────────────────────────────────────────────────────────────────────────────
# RightsAgent
# ─────────────────────────────────────────────────────────────────────────────

def test_rights_pass_when_territory_matches():
    opp = {"id": "opp_1", "territories": ["US", "CA"], "category": "Consumer audio"}
    campaign = {"id": "camp_1", "territories": ["US", "CA", "GB"]}
    result = check_rights(opp, campaign)
    assert result.overall_outcome == DecisionOutcome.PASS
    assert result.cleared_territory_count == 2


def test_rights_review_when_territory_not_in_campaign():
    opp = {"id": "opp_1", "territories": ["AU"], "category": "Consumer audio"}
    campaign = {"id": "camp_1", "territories": ["US", "CA"]}
    result = check_rights(opp, campaign)
    assert result.overall_outcome == DecisionOutcome.REVIEW


def test_rights_reject_restricted_category():
    opp = {"id": "opp_1", "territories": ["US"], "category": "tobacco"}
    campaign = {"id": "camp_1", "territories": []}
    result = check_rights(opp, campaign)
    assert result.overall_outcome == DecisionOutcome.REJECT


def test_rights_pass_when_no_campaign_territory_restriction():
    opp = {"id": "opp_1", "territories": ["DE", "FR"], "category": "Beverages"}
    campaign = {"id": "camp_1", "territories": []}
    result = check_rights(opp, campaign)
    assert result.overall_outcome == DecisionOutcome.PASS
    assert result.cleared_territory_count == 2


def test_rights_fields_populated():
    opp = {"id": "opp_abc", "territories": ["US"], "category": "Technology"}
    campaign = {"id": "camp_xyz", "territories": []}
    result = check_rights(opp, campaign)
    assert result.opportunity_id == "opp_abc"
    assert result.campaign_id == "camp_xyz"
    assert result.decided_at is not None
    assert "rights_agent" in result.agent_version


# ─────────────────────────────────────────────────────────────────────────────
# CreativeGuardian (deterministic path)
# ─────────────────────────────────────────────────────────────────────────────

def test_creative_pass_clean_scene():
    scene = {"mood": "Hopeful", "summary": "Hero celebrates success.", "brand_safety_score": 85.0}
    opp = {"id": "opp_1", "category": "Consumer audio", "screen_time_seconds": 20}
    campaign = {"id": "camp_1", "excluded_contexts": ["violence", "conflict"]}
    result = _evaluate_deterministic(scene, opp, campaign, "opp_1", "camp_1")
    assert result.overall_outcome == DecisionOutcome.PASS


def test_creative_reject_mood_matches_excluded_context():
    scene = {"mood": "Reflective", "summary": "A quiet moment.", "brand_safety_score": 80.0}
    opp = {"id": "opp_1", "category": "Energy drinks", "screen_time_seconds": 10}
    campaign = {"id": "camp_1", "excluded_contexts": ["reflective", "melancholic"]}
    result = _evaluate_deterministic(scene, opp, campaign, "opp_1", "camp_1")
    assert result.overall_outcome == DecisionOutcome.REJECT
    tone = next(g for g in result.guardrails if g.name == "tone_alignment")
    assert tone.outcome == DecisionOutcome.REJECT


def test_creative_review_low_brand_safety():
    scene = {"mood": "Action", "summary": "Car chase.", "brand_safety_score": 45.0}
    opp = {"id": "opp_1", "category": "Automotive", "screen_time_seconds": 15}
    campaign = {"id": "camp_1", "excluded_contexts": []}
    result = _evaluate_deterministic(scene, opp, campaign, "opp_1", "camp_1")
    adj = next(g for g in result.guardrails if g.name == "adjacency_safety")
    assert adj.outcome == DecisionOutcome.REVIEW


def test_creative_reject_very_low_brand_safety():
    scene = {"mood": "Dramatic", "summary": "Violent confrontation.", "brand_safety_score": 20.0}
    opp = {"id": "opp_1", "category": "Food", "screen_time_seconds": 5}
    campaign = {"id": "camp_1", "excluded_contexts": []}
    result = _evaluate_deterministic(scene, opp, campaign, "opp_1", "camp_1")
    adj = next(g for g in result.guardrails if g.name == "adjacency_safety")
    assert adj.outcome == DecisionOutcome.REJECT
    assert result.overall_outcome == DecisionOutcome.REJECT


# ─────────────────────────────────────────────────────────────────────────────
# DealAgent fee calculation
# ─────────────────────────────────────────────────────────────────────────────

def test_fee_calculation_basic():
    opp = {"estimated_value_usd": 10000.0}
    match = {"composite_score": 80.0, "campaign": {"budget_min_usd": 0, "budget_max_usd": 50000}}
    fee = _calculate_fee(opp, match)
    # 80% base + (80/100 * 40%) = 80 + 32 = 112% → 10000 * 1.12 = 11200
    assert 10000 < fee < 20000


def test_fee_capped_at_budget_max():
    opp = {"estimated_value_usd": 50000.0}
    match = {"composite_score": 100.0, "campaign": {"budget_min_usd": 0, "budget_max_usd": 5000}}
    fee = _calculate_fee(opp, match)
    assert fee == 5000


def test_fee_at_least_budget_min():
    opp = {"estimated_value_usd": 100.0}
    match = {"composite_score": 0.0, "campaign": {"budget_min_usd": 2000, "budget_max_usd": 50000}}
    fee = _calculate_fee(opp, match)
    assert fee == 2000


def test_fee_rounded_to_nearest_hundred():
    opp = {"estimated_value_usd": 7777.0}
    match = {"composite_score": 50.0, "campaign": {"budget_min_usd": 0, "budget_max_usd": 999999}}
    fee = _calculate_fee(opp, match)
    assert fee % 100 == 0


# ─────────────────────────────────────────────────────────────────────────────
# DealAgent narrative template
# ─────────────────────────────────────────────────────────────────────────────

def test_narrative_template_contains_brand():
    scene = {"name": "Rooftop Scene", "mood": "Reflective"}
    opp = {"object_label": "Wireless headphones", "screen_time_seconds": 25}
    campaign = {"brand": "Aurelius", "product_line": "Focus series"}
    brief, narrative = _narrative_from_template(scene, opp, campaign)
    assert "Aurelius" in brief
    assert "Wireless headphones" in narrative or "Rooftop Scene" in narrative


def test_narrative_template_not_empty():
    scene = {}
    opp = {}
    campaign = {}
    brief, narrative = _narrative_from_template(scene, opp, campaign)
    assert len(brief) > 10
    assert len(narrative) > 10
