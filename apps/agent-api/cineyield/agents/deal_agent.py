"""Deal Agent — proposal composition.

Fee calculation is DETERMINISTIC (opportunity value × campaign budget signals).
Gemini writes the human-readable brand brief and scene narrative.
Falls back to templated prose when Gemini is unconfigured.

Input ctx.extra keys:
  scene           — SceneAnalysis dict
  opportunity     — PlacementOpportunity dict (with estimated_value_usd)
  campaign_match  — CampaignMatch dict (composite score, campaign details)
  rights_decision — RightsDecision dict
  creative_decision — CreativeDecision dict
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from ..config import get_settings
from ..schemas.decisions import DecisionOutcome
from ..schemas.proposal import Proposal, ProposalTerm
from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

_NARRATIVE_PROMPT = """You are a senior product placement executive writing a brand placement brief.

SCENE:
{scene_json}

PLACEMENT OPPORTUNITY:
{opp_json}

BRAND CAMPAIGN:
{campaign_json}

Write two things — return ONLY a JSON object:
{{
  "brand_brief": "<2-3 sentence why this placement fits the brand's story and audience — no buzzwords>",
  "scene_narrative": "<1 sentence describing the specific placement as a viewer would experience it>"
}}

Be specific. Reference the actual scene content and brand values.
Return ONLY the JSON object.
"""


class DealAgent(BaseAgent):
    name = "deal_agent"

    @property
    def is_configured(self) -> bool:
        return True  # deterministic fee is always available; Gemini prose is a bonus

    async def run(self, ctx: AgentContext) -> dict[str, Any]:
        scene = ctx.extra.get("scene", {})
        opportunity = ctx.extra.get("opportunity", {})
        campaign_match = ctx.extra.get("campaign_match", {})
        rights_decision = ctx.extra.get("rights_decision", {})
        creative_decision = ctx.extra.get("creative_decision", {})

        campaign = campaign_match.get("campaign", {})
        opp_id = opportunity.get("id") or ctx.opportunity_id or f"opp_{uuid.uuid4().hex[:8]}"
        camp_id = campaign.get("id") or ctx.campaign_id or "unknown"

        # 1. Deterministic fee calculation
        fee = _calculate_fee(opportunity, campaign_match)

        # 2. Prose narrative — Gemini if configured, template otherwise
        brand_brief, scene_narrative = await _generate_narrative(scene, opportunity, campaign)

        # 3. Assemble terms
        terms = _build_terms(opportunity, campaign, fee, rights_decision)

        # 4. Collect creative guardrails
        from ..schemas.decisions import GuardrailCheck
        guardrails = [
            GuardrailCheck(**g) for g in creative_decision.get("guardrails", [])
        ]

        proposal = Proposal(
            id=f"prop_{uuid.uuid4().hex[:12]}",
            opportunity_id=opp_id,
            campaign_id=camp_id,
            brand_name=campaign.get("brand", "Unknown Brand"),
            campaign_name=campaign.get("campaign_name", ""),
            brand_brief=brand_brief,
            scene_title=scene.get("name", "Scene"),
            scene_episode=scene.get("episode") or "",
            scene_description=scene_narrative,
            placement_fee_usd=fee,
            terms=terms,
            guardrails=guardrails,
            composed_by="deal_agent_v1",
            composed_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            "DealAgent composed proposal %s: %s × %s @ $%.0f",
            proposal.id, camp_id, opp_id, fee,
        )
        return proposal.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# Fee calculation — deterministic
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_fee(opportunity: dict[str, Any], campaign_match: dict[str, Any]) -> float:
    """Deterministic fee from opportunity value + campaign budget signals."""
    # Base: opportunity estimated value (already computed by SceneAgent)
    base = float(opportunity.get("estimated_value_usd") or 5000.0)

    # Campaign composite score adjusts 80-120% of base
    composite = float(campaign_match.get("composite_score") or 70.0)
    score_mult = 0.80 + (composite / 100.0) * 0.40  # 80% at 0, 120% at 100

    # Budget ceiling: never quote above campaign max budget
    budget_max = float(campaign_match.get("campaign", {}).get("budget_max_usd") or 999_999)
    budget_min = float(campaign_match.get("campaign", {}).get("budget_min_usd") or 0)

    fee = base * score_mult
    fee = max(budget_min, min(budget_max, fee))
    return round(fee, -2)  # round to nearest $100


# ─────────────────────────────────────────────────────────────────────────────
# Narrative — Gemini preferred, template fallback
# ─────────────────────────────────────────────────────────────────────────────

async def _generate_narrative(
    scene: dict, opportunity: dict, campaign: dict,
) -> tuple[str, str]:
    settings = get_settings()
    if settings.gemini_configured:
        try:
            return await _narrative_from_gemini(scene, opportunity, campaign, settings)
        except Exception as exc:
            if settings.is_contest_mode:
                raise RuntimeError(
                    f"DealAgent: Gemini narrative failed in contest mode — no fallback permitted. "
                    f"Original error: {exc}"
                ) from exc
            logger.warning("DealAgent Gemini narrative failed (%s), using template", exc)

    return _narrative_from_template(scene, opportunity, campaign)


async def _narrative_from_gemini(
    scene: dict, opportunity: dict, campaign: dict, settings: Any,
) -> tuple[str, str]:
    from google import genai
    from google.genai import types as gtypes

    if settings.google_cloud_project:
        client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_region or "us-central1",
        )
    else:
        client = genai.Client(api_key=settings.google_api_key)

    prompt = _NARRATIVE_PROMPT.format(
        scene_json=json.dumps(scene, indent=2),
        opp_json=json.dumps(opportunity, indent=2),
        campaign_json=json.dumps(campaign, indent=2),
    )

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[gtypes.Content(role="user", parts=[gtypes.Part(text=prompt)])],
        config=gtypes.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=1024,
            response_mime_type="application/json",
            thinking_config=gtypes.ThinkingConfig(thinking_budget=0),
        ),
    )

    raw = (response.text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:]).strip()

    data = json.loads(raw)
    return data.get("brand_brief", ""), data.get("scene_narrative", "")


def _narrative_from_template(
    scene: dict, opportunity: dict, campaign: dict,
) -> tuple[str, str]:
    brand = campaign.get("brand", "the brand")
    scene_name = scene.get("name", "this scene")
    opp_label = opportunity.get("object_label", "product")
    mood = scene.get("mood", "").lower()
    product_line = campaign.get("product_line", "")

    brand_brief = (
        f"{brand}'s {product_line} aligns naturally with the {mood} tone of {scene_name}. "
        f"The {opp_label} placement reaches an engaged audience in a high-quality editorial context. "
        f"This opportunity offers authentic brand integration without interrupting the viewer experience."
    )
    scene_narrative = (
        f"The {opp_label} appears prominently in {scene_name}, "
        f"visible for an estimated {opportunity.get('screen_time_seconds', 10)} seconds."
    )
    return brand_brief, scene_narrative


# ─────────────────────────────────────────────────────────────────────────────
# Terms assembly
# ─────────────────────────────────────────────────────────────────────────────

def _build_terms(
    opportunity: dict, campaign: dict, fee: float, rights_decision: dict,
) -> list[ProposalTerm]:
    cleared = rights_decision.get("cleared_territory_count", 0)
    total = rights_decision.get("total_territory_count", 0)
    territories = [
        t["territory"] for t in rights_decision.get("territories", [])
        if t.get("outcome") == DecisionOutcome.PASS.value
    ]
    territory_str = ", ".join(territories) if territories else "Global"

    return [
        ProposalTerm(label="Placement Fee", value=f"${fee:,.0f}", is_highlighted=True),
        ProposalTerm(label="Screen Time", value=f"{opportunity.get('screen_time_seconds', 0)}s"),
        ProposalTerm(label="Category", value=opportunity.get("category", "N/A")),
        ProposalTerm(label="Complexity", value=opportunity.get("complexity", "low").title()),
        ProposalTerm(label="Territories", value=territory_str, is_highlighted=bool(territories)),
        ProposalTerm(
            label="Rights Status",
            value=f"{cleared}/{total} territories cleared" if total else "Global clearance pending",
        ),
        ProposalTerm(label="Budget Range", value=(
            f"${campaign.get('budget_min_usd', 0):,.0f}–${campaign.get('budget_max_usd', 0):,.0f}"
        )),
    ]
