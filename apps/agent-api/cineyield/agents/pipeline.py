"""CineYield Pipeline Orchestrator using Google ADK LlmAgent.

The orchestrator is a real ADK LlmAgent — not a wrapper around non-ADK code.
It uses tools that call the canonical Python agents, so each tool is a single
callable step in the placement pipeline. Gemini drives routing; the tools do
the real work.

Usage:
  from cineyield.agents.pipeline import run_pipeline

  result = await run_pipeline(
      video_input={"gcs_uri": "gs://bucket/video.mp4", "asset_id": "asset_abc"},
  )

The orchestrator delegates to:
  SceneAgent → MarketAgent → RightsAgent → CreativeGuardian → DealAgent
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import logging
import threading
import time
import uuid
from typing import Any

from ..config import get_settings

logger = logging.getLogger(__name__)


def _run_async_in_thread(coro) -> Any:
    """Run a coroutine in a dedicated thread with its own event loop.

    Safe to call from both sync contexts and async contexts (even when an
    event loop is already running in the calling thread, e.g. FastAPI
    background tasks or ADK runner coroutines).
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


# ─────────────────────────────────────────────────────────────────────────────
# Thread-local pipeline state — one dict per call, safe for concurrent runs.
# ─────────────────────────────────────────────────────────────────────────────

_local = threading.local()


def _state() -> dict[str, Any]:
    if not hasattr(_local, "run"):
        _local.run = {}
    return _local.run


def _init_state() -> None:
    _local.run = {}


# ─────────────────────────────────────────────────────────────────────────────
# ADK agent construction — lazy so imports fail gracefully when ADK missing
# ─────────────────────────────────────────────────────────────────────────────

def _build_adk_agent(model: str):
    """Build a Google ADK LlmAgent with CineYield pipeline tools."""
    from google.adk.agents import LlmAgent

    return LlmAgent(
        name="cineyield_orchestrator",
        model=model,
        description="CineYield product placement pipeline orchestrator",
        instruction=_ORCHESTRATOR_INSTRUCTION,
        tools=[
            analyze_scene_tool,
            discover_campaigns_tool,
            check_rights_tool,
            check_creative_tool,
            compose_proposal_tool,
        ],
    )


_ORCHESTRATOR_INSTRUCTION = """You are the CineYield pipeline orchestrator.
Your job: coordinate the product placement analysis pipeline for a video scene.

Execute these tools IN ORDER for each pipeline run:
1. analyze_scene — analyze the video for placement opportunities
2. discover_campaigns — find matching brand campaigns via MCP/ClickHouse
3. check_rights — verify territory rights for the best match
4. check_creative — evaluate narrative integrity of the placement
5. compose_proposal — assemble the final proposal with fee

Rules:
- If analyze_scene fails, stop and report the error. Do not continue.
- If no campaigns match (discover_campaigns returns empty ranked list), stop after step 2.
- If rights check rejects, do not call compose_proposal.
- If creative check rejects, do not call compose_proposal.
- Always call the tools in sequence; never skip a step.
- Return a JSON summary of all results at the end.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Tool functions — called by the ADK LlmAgent
# ─────────────────────────────────────────────────────────────────────────────

def analyze_scene_tool(gcs_uri: str = "", video_path: str = "", asset_id: str = "") -> dict:
    """Analyze a video scene for product placement opportunities using Gemini.

    Args:
        gcs_uri: gs:// URI of video (preferred)
        video_path: local file path (fallback)
        asset_id: content asset identifier

    Returns:
        Scene analysis with detected objects and placement opportunities.
    """
    from .base import AgentContext
    from .scene_agent import SceneAgent

    t0 = time.monotonic()
    effective_asset_id = asset_id or f"asset_{uuid.uuid4().hex[:8]}"
    agent = SceneAgent()
    ctx = AgentContext(
        asset_id=effective_asset_id,
        extra={
            "gcs_uri": gcs_uri or None,
            "video_path": video_path or None,
        },
    )

    result = _run_async_in_thread(agent.run(ctx))

    latency_ms = int((time.monotonic() - t0) * 1000)
    scene = result.get("scene", {})
    opportunities = result.get("opportunities", [])

    st = _state()
    st["scene"] = scene
    st["opportunities"] = opportunities
    st["asset_id"] = effective_asset_id

    # Persist to ClickHouse
    try:
        from ..config import get_settings
        from ..db import repository
        if get_settings().clickhouse_configured and scene:
            repository.upsert_scene(scene)
            repository.upsert_opportunities(opportunities)
            repository.write_agent_event(
                agent_name="scene_agent",
                kind="completed",
                summary=f"Scene analyzed: {scene.get('name','?')} · {len(opportunities)} opportunities",
                asset_id=effective_asset_id,
                scene_id=scene.get("scene_id"),
                tool_name="gemini.video_understand",
                latency_ms=latency_ms,
                success=True,
            )
    except Exception as exc:
        logger.warning("ClickHouse persist failed in analyze_scene_tool: %s", exc)

    return {
        "scene_id": scene.get("scene_id"),
        "name": scene.get("name"),
        "opportunities_count": len(opportunities),
        "brand_safety_score": scene.get("brand_safety_score"),
        "latency_ms": latency_ms,
    }


def discover_campaigns_tool(category: str = "", territories: str = "US,CA,GB") -> dict:
    """Discover matching brand campaigns from ClickHouse via mcp-clickhouse.

    Args:
        category: placement opportunity category
        territories: comma-separated territory codes

    Returns:
        Ranked campaign matches with scores.
    """
    from .base import AgentContext
    from .market_agent import MarketAgent

    t0 = time.monotonic()
    st = _state()
    scene = st.get("scene", {})
    opportunities = st.get("opportunities", [])
    asset_id = st.get("asset_id", "")

    if not opportunities:
        return {"matches": [], "ranked_count": 0, "blocked_count": 0, "note": "no opportunities from scene analysis"}

    def _apply_overrides(candidate: dict) -> dict:
        # The analyzed opportunity's own category is AUTHORITATIVE; the
        # model's argument is only a fallback.
        #
        # `category` here is free text chosen by the ADK orchestrator's LLM.
        # In a real run it passed the detected object label ("Smartphone")
        # instead of the taxonomy category ("Mobile devices"). Because
        # scoring hard-blocks on category mismatch, that override silently
        # blocked all 27 campaigns, so the pipeline produced a scene and
        # then no match, no proposal and no deal -- the demo dead-ended at
        # exactly the point that matters. Measured: "Mobile devices" ->
        # 1/27 unblocked, "Smartphone" -> 0/27.
        #
        # The orchestrator's job is to sequence the tools, not to supply the
        # data the deterministic scorer reasons over. Only fall back to its
        # argument if scene analysis genuinely produced no category.
        merged = candidate
        if category and not merged.get("category"):
            merged = {**merged, "category": category}
        # PlacementOpportunity (schemas/placement.py) carries no
        # `territories` field, so `opp.get("territories")` on a
        # scene-analysis opportunity is always falsy -- the old
        # `territories and not opp.get("territories")` guard could never
        # actually skip this. Being honest about that: territories is
        # unconditionally taken from the tool argument.
        if territories:
            merged = {**merged, "territories": [t.strip() for t in territories.split(",")]}
        return merged

    agent = MarketAgent()

    # Only opportunities[0] used to be tried. A single scene can yield
    # several detected placement opportunities (e.g. a kitchen scene:
    # appliance + cookware + beverage), and the first one Gemini listed is
    # not necessarily the one with real campaign demand -- a bad first
    # detection could sink a scene that had a good match right behind it.
    # Try each candidate, in the order scene analysis returned them, and
    # stop at the first that finds an unblocked match. Bounded by the
    # scene's opportunity count (the analysis prompt asks for 1-5), so this
    # adds at most a few extra MCP round trips, and none at all in the
    # common case where opportunities[0] already matches.
    opp = opportunities[0]
    result: dict[str, Any] | None = None
    for candidate in opportunities:
        candidate_opp = _apply_overrides(candidate)
        candidate_ctx = AgentContext(
            asset_id=asset_id,
            scene_id=scene.get("scene_id"),
            opportunity_id=candidate_opp.get("id"),
            extra={"opportunity": candidate_opp, "scene": scene},
        )
        candidate_result = _run_async_in_thread(agent.run(candidate_ctx))
        if result is None:
            # Always keep the first candidate's result so a total dead end
            # (nothing unblocked anywhere) still reports something concrete
            # instead of silently discarding every attempt.
            result = candidate_result
            opp = candidate_opp
        if candidate_result.get("ranked_count", 0) > 0:
            result = candidate_result
            opp = candidate_opp
            break

    assert result is not None  # loop runs at least once: opportunities is non-empty here

    latency_ms = int((time.monotonic() - t0) * 1000)
    st["market_result"] = result
    st["opportunity"] = opp

    try:
        from ..config import get_settings
        from ..db import repository
        if get_settings().clickhouse_configured:
            repository.write_agent_event(
                agent_name="market_agent",
                kind="completed",
                summary=(
                    f"Scanned {result.get('total_scanned', '?')} campaigns · "
                    f"{result.get('ranked_count', 0)} ranked · "
                    f"mcp latency {result.get('mcp_latency_ms', '?')}ms"
                ),
                asset_id=asset_id,
                scene_id=scene.get("scene_id"),
                opportunity_id=opp.get("id"),
                tool_name="mcp-clickhouse.query",
                latency_ms=latency_ms,
                success=True,
            )
            # Persist so /analytics/summary's total_matches reflects real
            # scans instead of a table nothing ever wrote to. Safe to call
            # repeatedly: the analytics query dedupes to the latest write
            # per (opportunity_id, campaign_id) pair.
            matches = result.get("matches", [])
            if matches:
                from .market_agent import matches_to_event_dicts
                repository.write_match_events(matches_to_event_dicts(matches))
    except Exception as exc:
        logger.warning("ClickHouse event write failed in discover_campaigns_tool: %s", exc)

    return {
        "ranked_count": result.get("ranked_count", 0),
        "blocked_count": result.get("blocked_count", 0),
        "total_scanned": result.get("total_scanned", 0),
        "mcp_latency_ms": result.get("mcp_latency_ms"),
        "top_match": _top_match_summary(result),
        "summary": result.get("summary", ""),
        "latency_ms": latency_ms,
    }


def check_rights_tool(territory: str = "US") -> dict:
    """Check territory rights clearance for the top campaign match.

    Args:
        territory: primary territory to check (others inferred from match)

    Returns:
        Rights decision with per-territory outcomes.
    """
    from .base import AgentContext
    from .rights_agent import RightsAgent

    t0 = time.monotonic()
    st = _state()
    opportunity = st.get("opportunity", {})
    market_result = st.get("market_result", {})
    matches = market_result.get("matches", [])
    top = _find_top_match(matches)
    campaign = top if top else {}

    if not campaign:
        return {"overall_outcome": "review", "note": "no ranked campaign to check rights for"}

    agent = RightsAgent()
    ctx = AgentContext(
        opportunity_id=opportunity.get("id"),
        campaign_id=campaign.get("id"),
        extra={"opportunity": opportunity, "campaign": campaign},
    )

    result = _run_async_in_thread(agent.run(ctx))

    latency_ms = int((time.monotonic() - t0) * 1000)
    st["rights_decision"] = result
    st["top_campaign"] = campaign
    st["top_match"] = top

    try:
        from ..config import get_settings
        from ..db import repository
        scene = st.get("scene", {})
        if get_settings().clickhouse_configured:
            repository.write_agent_event(
                agent_name="rights_agent",
                kind="completed",
                summary=f"Rights: {result.get('overall_outcome','?')} for {campaign.get('brand','?')}",
                scene_id=scene.get("scene_id"),
                opportunity_id=opportunity.get("id"),
                campaign_id=campaign.get("id"),
                tool_name="rules.evaluate",
                latency_ms=latency_ms,
                success=result.get("overall_outcome") != "reject",
            )
    except Exception as exc:
        logger.warning("ClickHouse event write failed in check_rights_tool: %s", exc)

    return result if isinstance(result, dict) else {"overall_outcome": "review"}


def check_creative_tool() -> dict:
    """Evaluate narrative integrity of the top placement using Gemini.

    Returns:
        Creative decision with guardrail outcomes.
    """
    from .base import AgentContext
    from .creative_guardian import CreativeGuardian

    t0 = time.monotonic()
    st = _state()
    scene = st.get("scene", {})
    opportunity = st.get("opportunity", {})
    campaign = st.get("top_campaign", {})

    if not campaign:
        return {"overall_outcome": "review", "note": "no campaign to evaluate creative for"}

    agent = CreativeGuardian()
    ctx = AgentContext(
        opportunity_id=opportunity.get("id"),
        campaign_id=campaign.get("id"),
        extra={"scene": scene, "opportunity": opportunity, "campaign": campaign},
    )

    result = _run_async_in_thread(agent.run(ctx))

    latency_ms = int((time.monotonic() - t0) * 1000)
    st["creative_decision"] = result

    try:
        from ..config import get_settings
        from ..db import repository
        if get_settings().clickhouse_configured:
            repository.write_agent_event(
                agent_name="creative_guardian",
                kind="completed",
                summary=f"Creative: {result.get('overall_outcome','?')} for {campaign.get('brand','?')}",
                scene_id=scene.get("scene_id"),
                opportunity_id=opportunity.get("id"),
                campaign_id=campaign.get("id"),
                tool_name="gemini.narrative_guard",
                latency_ms=latency_ms,
                success=result.get("overall_outcome") != "reject",
            )
    except Exception as exc:
        logger.warning("ClickHouse event write failed in check_creative_tool: %s", exc)

    return result


def compose_proposal_tool() -> dict:
    """Compose the final placement proposal with fee calculation and narrative.

    Returns:
        Complete proposal ready for producer review.
    """
    from .base import AgentContext
    from .deal_agent import DealAgent

    t0 = time.monotonic()
    st = _state()
    scene = st.get("scene", {})
    opportunity = st.get("opportunity", {})
    top_match = st.get("top_match", {})
    rights_decision = st.get("rights_decision", {})
    creative_decision = st.get("creative_decision", {})

    if not top_match:
        return {"error": "no campaign match available to compose proposal"}

    agent = DealAgent()
    ctx = AgentContext(
        opportunity_id=opportunity.get("id"),
        campaign_id=top_match.get("campaign_id"),
        extra={
            "scene": scene,
            "opportunity": opportunity,
            "campaign_match": top_match,
            "rights_decision": rights_decision,
            "creative_decision": creative_decision,
        },
    )

    result = _run_async_in_thread(agent.run(ctx))

    latency_ms = int((time.monotonic() - t0) * 1000)
    st["proposal"] = result

    campaign = st.get("top_campaign", {})

    # Persist proposal to ClickHouse
    try:
        from ..config import get_settings
        from ..db import repository
        if get_settings().clickhouse_configured and result.get("id"):
            repository.upsert_proposal({
                **result,
                "brand_name": campaign.get("brand", ""),
                "campaign_name": campaign.get("campaign_name", ""),
                "opportunity_id": opportunity.get("id", ""),
                "campaign_id": campaign.get("id", ""),
                "scene_title": scene.get("name", ""),
                "scene_description": scene.get("summary", ""),
            })
            repository.write_agent_event(
                agent_name="deal_agent",
                kind="proposal_created",
                summary=(
                    f"Proposal {result['id']} · {campaign.get('brand','?')} · "
                    f"${result.get('placement_fee_usd', 0):,.0f}"
                ),
                scene_id=scene.get("scene_id"),
                opportunity_id=opportunity.get("id"),
                campaign_id=campaign.get("id"),
                tool_name="deal.compose",
                latency_ms=latency_ms,
                success=True,
            )
    except Exception as exc:
        logger.warning("ClickHouse persist failed in compose_proposal_tool: %s", exc)

    return {**result, "latency_ms": latency_ms}


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(
    video_input: dict[str, Any],
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Run the full CineYield pipeline using the ADK LlmAgent orchestrator.

    Args:
        video_input: {"gcs_uri": "gs://...", "asset_id": "...", "video_path": "..."}
        correlation_id: optional trace ID

    Returns:
        Pipeline result with scene, matches, rights, creative, proposal.

    Raises:
        RuntimeError: in contest mode if Gemini or ADK is unavailable.
    """
    settings = get_settings()
    corr_id = correlation_id or uuid.uuid4().hex
    is_contest = settings.is_contest_mode

    if not settings.gemini_configured:
        raise RuntimeError(
            "Pipeline requires GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT. "
            "Run: gcloud auth application-default login"
        )

    logger.info("Pipeline starting: corr_id=%s gcs_uri=%s", corr_id, video_input.get("gcs_uri"))
    t_start = time.monotonic()

    # Initialise thread-local state for this run
    _init_state()

    final_text = ""
    adk_used = False

    try:
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.genai import types as gtypes

        adk_agent = _build_adk_agent(settings.gemini_model)
        session_svc = InMemorySessionService()
        runner = Runner(
            app_name="cineyield",
            agent=adk_agent,
            session_service=session_svc,
            auto_create_session=True,
        )

        gcs_uri = video_input.get("gcs_uri", "")
        video_path = video_input.get("video_path", "")
        asset_id = video_input.get("asset_id", f"asset_{corr_id[:8]}")

        user_message = (
            f"Run the full product placement analysis pipeline. "
            f"Video: gcs_uri={gcs_uri!r}, video_path={video_path!r}, asset_id={asset_id!r}. "
            f"Execute all pipeline steps in order and return a complete summary."
        )

        new_message = gtypes.Content(
            role="user",
            parts=[gtypes.Part(text=user_message)],
        )

        session_id = f"session_{corr_id}"
        user_id = "pipeline_runner"

        async for event in runner.run_async(
            session_id=session_id,
            user_id=user_id,
            new_message=new_message,
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts or []:
                    if hasattr(part, "text") and part.text:
                        final_text = part.text

        adk_used = True

    except Exception as exc:
        if is_contest:
            raise RuntimeError(
                f"ADK pipeline failed in contest mode — no fallback permitted. Error: {exc}"
            ) from exc
        logger.warning("ADK runner failed (%s), falling back to direct pipeline", exc)
        final_text = await _run_pipeline_direct(video_input)

    total_ms = int((time.monotonic() - t_start) * 1000)
    st = _state()

    return {
        "correlation_id": corr_id,
        "total_latency_ms": total_ms,
        "adk_used": adk_used,
        "scene": st.get("scene"),
        "opportunities": st.get("opportunities", []),
        "market_result": {
            "ranked_count": st.get("market_result", {}).get("ranked_count", 0),
            "total_scanned": st.get("market_result", {}).get("total_scanned", 0),
            "mcp_latency_ms": st.get("market_result", {}).get("mcp_latency_ms"),
            "summary": st.get("market_result", {}).get("summary", ""),
        },
        "rights_decision": st.get("rights_decision"),
        "creative_decision": st.get("creative_decision"),
        "proposal": st.get("proposal"),
        "orchestrator_summary": final_text,
        "pipeline_version": "adk_llmagent_v1" if adk_used else "direct_fallback_v1",
    }


async def _run_pipeline_direct(video_input: dict[str, Any]) -> str:
    """Direct pipeline execution (no ADK runner) — used when ADK fails to init."""
    gcs_uri = video_input.get("gcs_uri", "")
    video_path = video_input.get("video_path", "")
    asset_id = video_input.get("asset_id", f"asset_{uuid.uuid4().hex[:8]}")

    analyze_scene_tool(gcs_uri=gcs_uri, video_path=video_path, asset_id=asset_id)
    discover_campaigns_tool()
    rights = check_rights_tool()
    if rights.get("overall_outcome") == "reject":
        return f"Pipeline stopped: rights rejected — {rights}"
    creative = check_creative_tool()
    if creative.get("overall_outcome") == "reject":
        return f"Pipeline stopped: creative rejected — {creative}"
    compose_proposal_tool()
    return "Pipeline completed via direct execution (ADK unavailable)"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _top_match_summary(market_result: dict) -> dict:
    top = _find_top_match(market_result.get("matches", []))
    if not top:
        return {}
    return {
        "brand": top.get("brand", ""),
        "campaign_name": top.get("campaign_name", ""),
        "composite_score": top.get("score") or top.get("composite_score"),
    }


def _find_top_match(matches: list) -> dict | None:
    """Return the highest-scoring non-blocked match as a plain dict."""
    def _is_blocked(m) -> bool:
        return m.is_blocked if hasattr(m, "is_blocked") else bool(m.get("is_blocked"))

    def _score(m) -> float:
        return m.score if hasattr(m, "score") else float(m.get("score") or m.get("composite_score") or 0.0)

    unblocked = [m for m in matches if not _is_blocked(m)]
    if not unblocked:
        return None

    best = max(unblocked, key=_score)
    if hasattr(best, "model_dump"):
        d = best.model_dump()
        # Normalize: add "id" alias for "campaign_id" (expected by downstream agents)
        d.setdefault("id", d.get("campaign_id", ""))
        return d
    # Already a dict — ensure "id" alias exists
    if isinstance(best, dict):
        best.setdefault("id", best.get("campaign_id", ""))
    return best
