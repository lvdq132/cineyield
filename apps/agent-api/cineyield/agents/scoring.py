"""Deterministic campaign scoring for CineYield.

No LLM involvement. Pure Python math.
Weights mirror the frontend ScoreBreakdown fixture.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScoredCampaign:
    campaign_id: str
    brand: str
    campaign_name: str
    product_line: str
    budget_min_usd: float
    budget_max_usd: float
    territories: list[str]
    # Score components (0–100)
    context_fit: float
    category_fit: float
    visibility_score: float
    brand_safety: float
    territory_score: float
    budget_score: float
    composite: float
    is_blocked: bool
    blocked_reason: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "brand": self.brand,
            "campaign_name": self.campaign_name,
            "product_line": self.product_line,
            "budget_min_usd": self.budget_min_usd,
            "budget_max_usd": self.budget_max_usd,
            "territories": self.territories,
            "context_fit": self.context_fit,
            "category_fit": self.category_fit,
            "visibility_score": self.visibility_score,
            "brand_safety": self.brand_safety,
            "territory_score": self.territory_score,
            "budget_score": self.budget_score,
            "composite": self.composite,
            "is_blocked": self.is_blocked,
            "blocked_reason": self.blocked_reason,
        }


def _score_category_fit(
    opportunity_category: str,
    target_categories: list[str],
) -> float:
    opp_lower = opportunity_category.strip().lower()

    # An empty category must never be treated as a match. Matching is substring
    # based, and "" is a substring of every string, so a blank category would
    # score 100.0 against all 27 campaigns and present them as deterministically
    # validated matches. Failing closed is the honest behaviour: no category
    # means no evidence of fit, not universal fit.
    if not opp_lower:
        return 0.0

    for tc in target_categories:
        tc_lower = tc.strip().lower()
        if not tc_lower:
            continue
        if tc_lower == opp_lower or opp_lower in tc_lower or tc_lower in opp_lower:
            return 100.0
    return 0.0


def _score_context_fit(
    scene_mood: str,
    scene_narrative_weight: str,
    brand_safety_score: float,
    excluded_contexts: list[str],
) -> float:
    mood_lower = scene_mood.strip().lower()
    # An unknown mood is NOT a conflict with everything.
    #
    # Matching is substring based, and "" is a substring of every string, so a
    # blank mood used to match every excluded context and hard-block the
    # campaign. That is the wrong direction: no mood means no evidence of an
    # adjacency problem, so there is nothing to block on. (Contrast the
    # category check, which fails closed on blank -- there, no category means
    # no evidence of *fit*, and matching everything would be the unsafe answer.)
    if mood_lower:
        for ctx in excluded_contexts:
            ctx_lower = ctx.strip().lower()
            if not ctx_lower:
                continue
            if ctx_lower in mood_lower or mood_lower in ctx_lower:
                return 0.0  # hard block via context_fit=0
    # Base: brand_safety_score normalized, boosted by aspirational mood
    base = brand_safety_score
    if scene_narrative_weight.lower() == "high":
        base = min(100.0, base + 3.0)
    return round(base, 1)


def _score_visibility(
    screen_time_seconds: int,
    vis_min: int,
    vis_max: int,
) -> float:
    if screen_time_seconds < vis_min:
        return 0.0
    if screen_time_seconds > vis_max:
        return 80.0  # longer than requested — still ok but not perfect fit
    window = vis_max - vis_min
    if window == 0:
        return 100.0
    return round(100.0 * (screen_time_seconds - vis_min) / window, 1)


def _score_territory(
    opportunity_territories: list[str],
    campaign_territories: list[str],
) -> float:
    if not opportunity_territories:
        return 100.0  # no constraint
    matched = sum(1 for t in opportunity_territories if t in campaign_territories)
    return round(100.0 * matched / len(opportunity_territories), 1)


def _score_budget(
    estimated_value_usd: float | None,
    budget_min: float,
    budget_max: float,
) -> float:
    if estimated_value_usd is None:
        return 80.0  # unknown value — assume ok
    if estimated_value_usd < budget_min:
        return 50.0  # below min but not disqualifying
    if estimated_value_usd <= budget_max:
        return 100.0
    return 70.0  # above budget max — campaign may still negotiate


def _composite(
    context_fit: float,
    category_fit: float,
    visibility: float,
    brand_safety: float,
    territory: float,
    budget: float,
) -> float:
    return round(
        context_fit * 0.25
        + category_fit * 0.25
        + visibility * 0.15
        + brand_safety * 0.20
        + territory * 0.10
        + budget * 0.05,
        1,
    )


def _check_hard_blocks(
    opportunity_category: str,
    scene_mood: str,
    excluded_contexts: list[str],
    target_categories: list[str],
    category_fit: float,
) -> tuple[bool, str | None]:
    """Hard-rule checks — deterministic, not LLM."""
    # Category mismatch block
    if category_fit == 0.0:
        return True, f"Category mismatch: {opportunity_category!r} not in campaign targets"

    # Context exclusion block. Same rule as _score_context_fit: a blank mood is
    # an absence of evidence, not a conflict with every excluded context.
    mood_lower = scene_mood.strip().lower()
    if mood_lower:
        for ctx in excluded_contexts:
            ctx_lower = ctx.strip().lower()
            if not ctx_lower:
                continue
            if ctx_lower in mood_lower or mood_lower in ctx_lower:
                return True, f"Creative Guardian: adjacency conflict — scene mood {scene_mood!r} matches excluded context {ctx!r}"

    return False, None


def score_campaigns(
    campaigns: list[dict[str, Any]],
    *,
    opportunity_category: str,
    opportunity_territories: list[str],
    screen_time_seconds: int,
    estimated_value_usd: float | None,
    brand_safety_score: float,
    scene_mood: str,
    scene_narrative_weight: str,
) -> list[ScoredCampaign]:
    """
    Score and rank campaign rows returned from ClickHouse.

    Deterministic — no LLM calls. Returns sorted by composite desc,
    with blocked campaigns at the end.
    """
    scored: list[ScoredCampaign] = []

    for camp in campaigns:
        target_cats = camp.get("target_categories") or []
        excluded_ctxs = camp.get("excluded_contexts") or []
        territories = camp.get("territories") or []
        vis_min = int(camp.get("visibility_seconds_min") or 0)
        vis_max = int(camp.get("visibility_seconds_max") or 60)

        category_fit = _score_category_fit(opportunity_category, target_cats)
        context_fit = _score_context_fit(
            scene_mood, scene_narrative_weight, brand_safety_score, excluded_ctxs
        )
        visibility = _score_visibility(screen_time_seconds, vis_min, vis_max)
        brand_safety = brand_safety_score
        territory = _score_territory(opportunity_territories, territories)
        budget = _score_budget(
            estimated_value_usd,
            float(camp.get("budget_min_usd") or 0),
            float(camp.get("budget_max_usd") or 0),
        )

        is_blocked, blocked_reason = _check_hard_blocks(
            opportunity_category, scene_mood, excluded_ctxs, target_cats, category_fit
        )

        composite = (
            _composite(context_fit, category_fit, visibility, brand_safety, territory, budget)
            if not is_blocked
            else _composite(context_fit, category_fit, visibility, brand_safety, territory, budget)
        )

        scored.append(
            ScoredCampaign(
                campaign_id=camp.get("id", ""),
                brand=camp.get("brand", ""),
                campaign_name=camp.get("campaign_name", ""),
                product_line=camp.get("product_line", ""),
                budget_min_usd=float(camp.get("budget_min_usd") or 0),
                budget_max_usd=float(camp.get("budget_max_usd") or 0),
                territories=territories,
                context_fit=context_fit,
                category_fit=category_fit,
                visibility_score=visibility,
                brand_safety=brand_safety,
                territory_score=territory,
                budget_score=budget,
                composite=composite,
                is_blocked=is_blocked,
                blocked_reason=blocked_reason,
            )
        )

    # Sort: unblocked by composite desc, then blocked by composite desc
    unblocked = sorted([s for s in scored if not s.is_blocked], key=lambda x: x.composite, reverse=True)
    blocked = sorted([s for s in scored if s.is_blocked], key=lambda x: x.composite, reverse=True)
    return unblocked + blocked
