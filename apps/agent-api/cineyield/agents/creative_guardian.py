"""Creative Guardian — narrative integrity review.

Uses Gemini to evaluate whether a placement would compromise plot, character
motivation, or editorial tone. Falls back to a deterministic adjacency check
when Gemini is unconfigured (contest mode: explicit error, no silent fallback).

Input ctx.extra keys:
  scene       — SceneAnalysis dict
  opportunity — PlacementOpportunity dict
  campaign    — BrandCampaign dict
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from ..config import get_settings
from ..schemas.decisions import CreativeDecision, DecisionOutcome, GuardrailCheck
from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

_GUARDIAN_PROMPT = """You are a senior entertainment creative consultant.
Your job: decide if this product placement would compromise the creative integrity of this scene.

SCENE:
{scene_json}

PLACEMENT OPPORTUNITY:
{opp_json}

BRAND CAMPAIGN:
{campaign_json}

Evaluate these four guardrails and return ONLY a JSON object — no markdown:
{{
  "narrative_impact": "<one sentence on whether placement affects story or character>",
  "guardrails": [
    {{"name": "plot_integrity", "outcome": "pass|review|reject", "detail": "<reasoning>"}},
    {{"name": "tone_alignment", "outcome": "pass|review|reject", "detail": "<reasoning>"}},
    {{"name": "brand_context_conflict", "outcome": "pass|review|reject", "detail": "<reasoning>"}},
    {{"name": "adjacency_safety", "outcome": "pass|review|reject", "detail": "<reasoning>"}}
  ],
  "overall_outcome": "pass|review|reject"
}}

Rules:
- reject if the brand explicitly excludes a context that appears in this scene
- reject if placement would change character motivation or plot
- review if tone mismatch is moderate (e.g. energy drink in funeral scene)
- pass only if placement is invisible to the story
Return ONLY the JSON object.
"""


class CreativeGuardian(BaseAgent):
    name = "creative_guardian"

    @property
    def is_configured(self) -> bool:
        return get_settings().gemini_configured

    async def run(self, ctx: AgentContext) -> dict[str, Any]:
        scene = ctx.extra.get("scene", {})
        opportunity = ctx.extra.get("opportunity", {})
        campaign = ctx.extra.get("campaign", {})
        opp_id = opportunity.get("id") or ctx.opportunity_id or "unknown"
        camp_id = campaign.get("id") or ctx.campaign_id or "unknown"

        settings = get_settings()

        if self.is_configured:
            try:
                decision = await _evaluate_with_gemini(scene, opportunity, campaign, opp_id, camp_id)
                return decision.model_dump()
            except Exception as exc:
                if settings.is_contest_mode:
                    # Contest mode: no silent fallback — real Gemini failure must be visible
                    raise RuntimeError(
                        f"CreativeGuardian: Gemini call failed in contest mode — no fallback permitted. "
                        f"Original error: {exc}"
                    ) from exc
                logger.warning("CreativeGuardian Gemini call failed (%s), using deterministic fallback", exc)

        if settings.is_contest_mode and not self.is_configured:
            raise RuntimeError(
                "CreativeGuardian: Gemini is required in contest mode but not configured. "
                "Set GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT."
            )

        # Deterministic adjacency fallback (development mode only)
        decision = _evaluate_deterministic(scene, opportunity, campaign, opp_id, camp_id)
        return decision.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# Gemini path
# ─────────────────────────────────────────────────────────────────────────────

async def _evaluate_with_gemini(
    scene: dict, opportunity: dict, campaign: dict, opp_id: str, camp_id: str,
) -> CreativeDecision:
    from google import genai
    from google.genai import types as gtypes

    settings = get_settings()
    if settings.google_cloud_project:
        client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region or "us-central1",
        )
    else:
        client = genai.Client(api_key=settings.google_api_key)

    prompt = _GUARDIAN_PROMPT.format(
        scene_json=json.dumps(scene, indent=2),
        opp_json=json.dumps(opportunity, indent=2),
        campaign_json=json.dumps(campaign, indent=2),
    )

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
        config=gtypes.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=2048,
            response_mime_type="application/json",
            thinking_config=gtypes.ThinkingConfig(thinking_budget=0),
        ),
    )

    raw = response.text or ""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()

    data = json.loads(text)
    return _build_creative_decision(data, opp_id, camp_id, gemini_reasoning=data.get("narrative_impact", ""))


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic fallback
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_deterministic(
    scene: dict, opportunity: dict, campaign: dict, opp_id: str, camp_id: str,
) -> CreativeDecision:
    scene_mood = (scene.get("mood") or "").lower()
    scene_summary = (scene.get("summary") or "").lower()
    excluded: list[str] = [c.lower() for c in campaign.get("excluded_contexts", [])]
    opp_category = (opportunity.get("category") or "").lower()
    brand_safety = float(scene.get("brand_safety_score") or 70.0)

    guardrails: list[GuardrailCheck] = []

    # Plot integrity — can't determine without LLM, default pass
    guardrails.append(GuardrailCheck(
        name="plot_integrity",
        outcome=DecisionOutcome.PASS,
        detail="Deterministic check cannot evaluate plot impact — assumed benign",
    ))

    # Tone alignment — reject if mood or scene text matches any excluded context
    tone_outcome = DecisionOutcome.PASS
    tone_detail = "No tone conflict detected"
    for excluded_ctx in excluded:
        if excluded_ctx in scene_mood or excluded_ctx in scene_summary:
            tone_outcome = DecisionOutcome.REJECT
            tone_detail = f"Scene mood '{scene_mood}' conflicts with excluded context '{excluded_ctx}'"
            break

    guardrails.append(GuardrailCheck(
        name="tone_alignment", outcome=tone_outcome, detail=tone_detail,
    ))

    # Brand context conflict — if campaign has excluded contexts that match placement category
    ctx_outcome = DecisionOutcome.PASS
    ctx_detail = "No brand context conflict"
    for excluded_ctx in excluded:
        if excluded_ctx in opp_category:
            ctx_outcome = DecisionOutcome.REJECT
            ctx_detail = f"Placement category '{opp_category}' matches excluded context '{excluded_ctx}'"
            break
    guardrails.append(GuardrailCheck(
        name="brand_context_conflict", outcome=ctx_outcome, detail=ctx_detail,
    ))

    # Adjacency safety — low brand_safety_score means risk
    if brand_safety < 40:
        adj_outcome = DecisionOutcome.REJECT
        adj_detail = f"Brand safety score {brand_safety:.0f}/100 is too low for most brands"
    elif brand_safety < 60:
        adj_outcome = DecisionOutcome.REVIEW
        adj_detail = f"Brand safety score {brand_safety:.0f}/100 — manual review recommended"
    else:
        adj_outcome = DecisionOutcome.PASS
        adj_detail = f"Brand safety score {brand_safety:.0f}/100 is acceptable"
    guardrails.append(GuardrailCheck(
        name="adjacency_safety", outcome=adj_outcome, detail=adj_detail,
    ))

    overall = _overall_from_guardrails(guardrails)
    return CreativeDecision(
        opportunity_id=opp_id,
        campaign_id=camp_id,
        overall_outcome=overall,
        guardrails=guardrails,
        narrative_impact="Deterministic check — no LLM narrative evaluation",
        gemini_reasoning="",
        agent_version="creative_guardian_v1_deterministic",
        decided_at=datetime.now(timezone.utc).isoformat(),
    )


def _build_creative_decision(
    data: dict, opp_id: str, camp_id: str, gemini_reasoning: str = "",
) -> CreativeDecision:
    guardrails = [
        GuardrailCheck(
            name=g["name"],
            outcome=DecisionOutcome(g["outcome"]),
            detail=g.get("detail", ""),
        )
        for g in data.get("guardrails", [])
    ]
    overall_raw = data.get("overall_outcome", "review")
    try:
        overall = DecisionOutcome(overall_raw)
    except ValueError:
        overall = _overall_from_guardrails(guardrails)

    return CreativeDecision(
        opportunity_id=opp_id,
        campaign_id=camp_id,
        overall_outcome=overall,
        guardrails=guardrails,
        narrative_impact=data.get("narrative_impact", ""),
        gemini_reasoning=gemini_reasoning,
        agent_version="creative_guardian_v1_gemini",
        decided_at=datetime.now(timezone.utc).isoformat(),
    )


def _overall_from_guardrails(guardrails: list[GuardrailCheck]) -> DecisionOutcome:
    if any(g.outcome == DecisionOutcome.REJECT for g in guardrails):
        return DecisionOutcome.REJECT
    if any(g.outcome == DecisionOutcome.REVIEW for g in guardrails):
        return DecisionOutcome.REVIEW
    return DecisionOutcome.PASS
