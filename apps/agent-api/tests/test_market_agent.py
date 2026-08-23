"""Tests for MarketAgent's match_events shaping helper.

FIX 1 (P0 review): cineyield.db.match_events had zero callers before this
fix, so /analytics/summary's total_matches was structurally always 0 while
the very next screen (/marketplace) reported real scanned/ranked counts --
a direct on-screen contradiction on the demo's first screen. This tests the
shared dict-shaping helper both persistence call sites
(routers/v1/opportunities.py, agents/pipeline.py) use.
"""
from cineyield.agents.market_agent import matches_to_event_dicts
from cineyield.schemas.matching import CampaignMatch, ScoreBreakdown


def _match(campaign_id: str, is_blocked: bool = False, blocked_reason: str | None = None) -> CampaignMatch:
    return CampaignMatch(
        campaign_id=campaign_id,
        opportunity_id="opp_1",
        brand="Aurelius Systems",
        campaign_name="Focus Without Limits",
        product_line="Aurelius One Wireless Headphones",
        score=88.5,
        score_breakdown=ScoreBreakdown(
            context_fit=90.0,
            category_fit=100.0,
            visibility=80.0,
            brand_safety=96.0,
            territory=100.0,
            budget_and_terms=100.0,
        ),
        is_blocked=is_blocked,
        blocked_reason=blocked_reason,
        estimated_fee_usd=185_000.0,
        budget_min_usd=150_000.0,
        budget_max_usd=250_000.0,
        territories=["US", "CA", "GB"],
    )


def test_matches_to_event_dicts_maps_all_required_write_match_events_fields():
    dicts = matches_to_event_dicts([_match("camp_a")])
    assert len(dicts) == 1
    d = dicts[0]
    # Exactly the keys repository.write_match_events reads.
    assert d["opportunity_id"] == "opp_1"
    assert d["campaign_id"] == "camp_a"
    assert d["brand"] == "Aurelius Systems"
    assert d["composite_score"] == 88.5
    assert d["context_fit"] == 90.0
    assert d["category_fit"] == 100.0
    assert d["visibility_score"] == 80.0
    assert d["brand_safety"] == 96.0
    assert d["territory_score"] == 100.0
    assert d["budget_score"] == 100.0
    assert d["is_blocked"] is False
    assert d["blocked_reason"] is None


def test_matches_to_event_dicts_preserves_blocked_state():
    dicts = matches_to_event_dicts([_match("camp_b", is_blocked=True, blocked_reason="Category mismatch")])
    assert dicts[0]["is_blocked"] is True
    assert dicts[0]["blocked_reason"] == "Category mismatch"


def test_matches_to_event_dicts_handles_empty_list():
    assert matches_to_event_dicts([]) == []


def test_matches_to_event_dicts_preserves_order_and_count():
    dicts = matches_to_event_dicts([_match("camp_a"), _match("camp_b"), _match("camp_c")])
    assert [d["campaign_id"] for d in dicts] == ["camp_a", "camp_b", "camp_c"]
