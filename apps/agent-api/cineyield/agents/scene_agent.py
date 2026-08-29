"""Scene Agent — multimodal scene understanding via Gemini.

Uses Application Default Credentials (ADC) with google-genai 2.x.
Supports both direct API key (GOOGLE_API_KEY) and Vertex AI (GOOGLE_CLOUD_PROJECT + ADC).

Input:
  ctx.extra["gcs_uri"]    — gs:// URI of video (preferred for large files)
  ctx.extra["video_path"] — local file path (auto-uploaded to GCS if GCS configured)
  ctx.extra["asset_id"]   — content asset identifier

Output: dict matching SceneAnalysis schema + detected PlacementOpportunities
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..schemas.analysis import DetectedObject, SceneAnalysis
from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Gemini prompt — requests structured JSON scene analysis
# ─────────────────────────────────────────────────────────────────────────────
_SCENE_ANALYSIS_PROMPT = """
You are a professional product placement analyst reviewing a video scene.
Analyze this scene for commercial product placement opportunities.

Return a JSON object with EXACTLY this structure (no markdown, no explanation):

{
  "name": "<concise scene name, 2-5 words>",
  "summary": "<1-2 sentence description of what happens in the scene>",
  "setting": "<indoor/outdoor/vehicle/other>",
  "time_of_day": "<morning/afternoon/evening/dusk/night/unknown>",
  "mood": "<single word: Reflective/Energetic/Romantic/Tense/Dusk/Hopeful/Action/Dramatic/Comedic/Melancholic>",
  "narrative_weight": "<Low/Medium/High — how pivotal is this scene to the story>",
  "brand_safety_score": <integer 0-100>,
  "duration_seconds": <estimated integer seconds>,
  "detected_objects": [
    {
      "label": "<specific product/object name>",
      "category": "<one of: Consumer audio, Mobile devices, Automotive, Apparel, Beverages, Food & dining, Home & living, Sports & fitness, Beauty & wellness, Technology, Jewelry & accessories, Travel & luggage, Other>",
      "confidence": <float 0-100>,
      "is_primary": <true if prominently featured / in foreground>,
      "placement_natural": <true if placement would feel organic in this scene>,
      "timecode_start": "<MM:SS or null>",
      "timecode_end": "<MM:SS or null>"
    }
  ],
  "placement_opportunities": [
    {
      "object_label": "<what product would go here>",
      "category": "<same category list as above>",
      "naturalness_score": <float 0-100>,
      "screen_time_estimate_seconds": <integer>,
      "complexity": "<low/medium/high — production complexity of this placement>",
      "placement_zone": "<specific physical zone such as foreground table, passenger seat, wall shelf>",
      "notes": "<one sentence on why this placement works>"
    }
  ]
}

Brand safety scoring:
- 90-100: Family-friendly, aspirational, premium — any brand suitable
- 70-89:  General audience, minor mature themes
- 50-69:  Mature but not explicit
- 30-49:  Potentially controversial (violence, conflict, risk)
- 0-29:   Explicit or extreme — most brands unsuitable

Focus on objects that are actually visible or strongly implied.
Identify 1-5 genuine placement opportunities — do not invent implausible ones.
Return ONLY the JSON object.
"""

# Scene analysis schema for Gemini structured output (response_schema)
_SCENE_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "summary": {"type": "string"},
        "setting": {"type": "string"},
        "time_of_day": {"type": "string"},
        "mood": {"type": "string"},
        "narrative_weight": {"type": "string"},
        "brand_safety_score": {"type": "integer"},
        "duration_seconds": {"type": "integer"},
        "detected_objects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "category": {"type": "string"},
                    "confidence": {"type": "number"},
                    "is_primary": {"type": "boolean"},
                    "placement_natural": {"type": "boolean"},
                    "timecode_start": {"type": "string"},
                    "timecode_end": {"type": "string"},
                },
                "required": ["label", "category", "confidence", "is_primary"],
            },
        },
        "placement_opportunities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "object_label": {"type": "string"},
                    "category": {"type": "string"},
                    "naturalness_score": {"type": "number"},
                    "screen_time_estimate_seconds": {"type": "integer"},
                    "complexity": {"type": "string"},
                    "placement_zone": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["object_label", "category", "naturalness_score", "screen_time_estimate_seconds"],
            },
        },
    },
    "required": ["name", "summary", "mood", "narrative_weight", "brand_safety_score",
                 "duration_seconds", "detected_objects"],
}


class SceneAgent(BaseAgent):
    """Gemini-powered scene analysis for product placement opportunities."""

    name = "scene_agent"

    @property
    def is_configured(self) -> bool:
        return get_settings().gemini_configured

    async def run(self, ctx: AgentContext) -> dict[str, Any]:
        settings = get_settings()
        if not self.is_configured:
            raise RuntimeError(
                "SceneAgent requires GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT. "
                "Set credentials in .env and authenticate with: "
                "gcloud auth application-default login"
            )

        gcs_uri: str | None = ctx.extra.get("gcs_uri")
        video_path: str | None = ctx.extra.get("video_path")
        asset_id: str = ctx.asset_id or ctx.extra.get("asset_id", f"asset_{uuid.uuid4().hex[:8]}")
        scene_id: str = ctx.scene_id or f"scene_{uuid.uuid4().hex[:12]}"

        # Upload to GCS if we have a local file and GCS is configured
        if not gcs_uri and video_path and settings.gcs_configured:
            from ..gcs import upload_video_file
            logger.info("Uploading %s to GCS before Gemini analysis", video_path)
            gcs_uri = upload_video_file(video_path, asset_id=asset_id)

        if not gcs_uri and not video_path:
            raise ValueError("SceneAgent requires gcs_uri or video_path in ctx.extra")

        t_start = time.monotonic()
        raw = await _call_gemini(settings, gcs_uri, video_path)
        latency_ms = int((time.monotonic() - t_start) * 1000)

        data = _parse_response(raw)
        scene = _build_scene_analysis(data, scene_id, asset_id, settings.gemini_model, latency_ms)
        opportunities = _build_opportunities(data, scene_id, asset_id)

        logger.info(
            "SceneAgent completed: scene=%s mood=%s safety=%s objects=%d opps=%d latency=%dms",
            scene_id, scene.mood, scene.brand_safety_score,
            len(scene.detected_objects), len(opportunities), latency_ms,
        )

        return {
            "scene": scene.model_dump(),
            "opportunities": [o.model_dump() for o in opportunities],
            "latency_ms": latency_ms,
            "model": settings.gemini_model,
            "gcs_uri": gcs_uri,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Gemini API call
# ─────────────────────────────────────────────────────────────────────────────

async def _call_gemini(settings: Any, gcs_uri: str | None, video_path: str | None) -> str:
    """Call Gemini multimodal and return raw text response."""
    from google import genai
    from google.genai import types as gtypes

    # Build client — Vertex AI (ADC) preferred when project is set, API key fallback
    if settings.google_cloud_project:
        client = genai.Client(
            vertexai=True,  # also accepted as enterprise=True in SDK 2.x
            project=settings.google_cloud_project,
            location=settings.google_cloud_region or "us-central1",
        )
    else:
        client = genai.Client(api_key=settings.google_api_key)

    model = settings.gemini_model or "gemini-2.0-flash"

    # Build the video part
    if gcs_uri:
        video_part = gtypes.Part(
            file_data=gtypes.FileData(
                file_uri=gcs_uri,
                mime_type=_infer_mime(gcs_uri),
            )
        )
    else:
        assert video_path is not None
        path = Path(video_path)
        size_mb = path.stat().st_size / (1024 * 1024)

        if size_mb < 50:
            # Inline for small clips
            video_part = gtypes.Part(
                inline_data=gtypes.Blob(
                    data=path.read_bytes(),
                    mime_type=_infer_mime(video_path),
                )
            )
        else:
            # File API for medium files (up to 2 GB free)
            logger.info("Uploading %s via Gemini File API (%.1f MB)", path.name, size_mb)
            uploaded = client.files.upload(file=video_path)  # type: ignore[call-arg]
            video_part = gtypes.Part(
                file_data=gtypes.FileData(
                    file_uri=uploaded.uri,
                    mime_type=uploaded.mime_type,
                )
            )

    contents = [
        gtypes.Content(
            role="user",
            parts=[video_part, gtypes.Part(text=_SCENE_ANALYSIS_PROMPT)],
        )
    ]

    # gemini-2.5-flash: disable thinking tokens — they consume budget before output
    _thinking = gtypes.ThinkingConfig(thinking_budget=0)
    # 16384 tokens: enough for video analysis JSON with detected objects
    _tokens = 16384

    # Primary: response_mime_type=application/json with prompt-based schema
    # NOTE: response_json_schema causes 400 with video inputs on Vertex AI;
    # we rely on the prompt's explicit JSON template instead.
    try:
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=gtypes.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=_tokens,
                response_mime_type="application/json",
                thinking_config=_thinking,
            ),
        )
    except Exception as mime_exc:
        logger.warning("JSON mime type failed (%s), retrying plain text", mime_exc)
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=gtypes.GenerateContentConfig(
                temperature=0.1, max_output_tokens=_tokens, thinking_config=_thinking,
            ),
        )

    if not response.text:
        raise RuntimeError("Gemini returned empty response — check safety filters or media format")

    return response.text


# ─────────────────────────────────────────────────────────────────────────────
# Response parsing and model construction
# ─────────────────────────────────────────────────────────────────────────────

def _parse_response(raw: str) -> dict[str, Any]:
    """Parse Gemini's JSON response. Strips markdown fences if present.

    Handles truncated JSON (Gemini can hit token limits mid-object) by
    extracting the top-level fields that were fully written before truncation.
    """
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        inner = lines[1:] if not lines[-1].startswith("```") else lines[1:-1]
        text = "\n".join(inner).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt to recover from truncated output by closing open brackets/braces
        recovered = _recover_truncated_json(text)
        if recovered is not None:
            logger.warning("Gemini response was truncated; recovered partial JSON")
            return recovered
        logger.error("Failed to parse Gemini response as JSON.\nRaw: %r", text[:500])
        raise RuntimeError(
            f"Gemini returned non-JSON response. Snippet: {text[:200]!r}"
        )


def _recover_truncated_json(text: str) -> dict[str, Any] | None:
    """Try to recover top-level string/number fields from truncated JSON.

    Gemini sometimes hits max_output_tokens mid-string. We can still extract
    the fields that completed before truncation by closing the JSON structure.
    """
    # Try progressively shorter prefixes — drop incomplete last key/value
    # by truncating at the last complete key-value separator (comma or opening brace)
    for end_char in [",", "{"]:
        last = text.rfind(end_char)
        if last > 0:
            candidate = text[:last] + "}"
            # Close any open arrays
            open_arrays = candidate.count("[") - candidate.count("]")
            if open_arrays > 0:
                candidate = candidate[:last] + "]" * open_arrays + "}"
            try:
                result = json.loads(candidate)
                if isinstance(result, dict) and result:
                    return result
            except json.JSONDecodeError:
                continue
    return None


def _parse_scene_json(raw: str, scene_id: str, asset_id: str, model: str) -> SceneAnalysis:
    """Parse Gemini response + build SceneAnalysis. Returns safe fallback on bad JSON."""
    try:
        data = _parse_response(raw)
        return _build_scene_analysis(data, scene_id, asset_id, model, latency_ms=0)
    except (RuntimeError, Exception):
        return SceneAnalysis(
            scene_id=scene_id,
            asset_id=asset_id,
            name="Unknown Scene",
            summary="",
            mood="Unknown",
            narrative_weight="Low",
            brand_safety_score=50.0,
            duration_seconds=0,
            detected_objects=[],
            gemini_model_used=model,
            analyzed_at=datetime.now(timezone.utc).isoformat(),
        )


def _build_scene_analysis(
    data: dict[str, Any],
    scene_id: str,
    asset_id: str,
    model: str,
    latency_ms: int,
) -> SceneAnalysis:
    objects = [
        DetectedObject(
            label=obj.get("label", "unknown"),
            category=obj.get("category", "Other"),
            confidence=max(0.0, min(100.0, float(obj.get("confidence", 0.0)))),
            is_primary=bool(obj.get("is_primary", False)),
            timecode_start=obj.get("timecode_start"),
            timecode_end=obj.get("timecode_end"),
        )
        for obj in data.get("detected_objects", [])
    ]

    return SceneAnalysis(
        scene_id=scene_id,
        asset_id=asset_id,
        name=data.get("name", "Scene"),
        summary=data.get("summary", ""),
        mood=data.get("mood", ""),
        narrative_weight=data.get("narrative_weight", "Low"),
        brand_safety_score=max(0.0, min(100.0, float(data.get("brand_safety_score", 50.0)))),
        duration_seconds=int(data.get("duration_seconds", 0)),
        detected_objects=objects,
        gemini_model_used=model,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )


def _build_opportunities(data: dict[str, Any], scene_id: str, asset_id: str) -> list[Any]:
    """Convert Gemini-detected opportunities into Pydantic models."""
    from ..schemas.placement import PlacementOpportunity
    from .category_taxonomy import normalize_category

    opps = []
    for i, opp in enumerate(data.get("placement_opportunities", []), 1):
        screen_time = int(opp.get("screen_time_estimate_seconds", 10))
        naturalness = max(0.0, min(100.0, float(opp.get("naturalness_score", 50.0))))
        opp_id = f"{scene_id}_opp_{i:02d}"
        opps.append(
            PlacementOpportunity(
                id=opp_id,
                scene_id=scene_id,
                asset_id=asset_id,
                # Normalized onto the seeded campaign taxonomy -- see
                # category_taxonomy.py. Two of Gemini's 13 prompt values
                # ("Home & living" and the omitted-category default "Other")
                # otherwise match zero of the 27 seeded campaigns and
                # dead-end the pipeline before scoring ever runs.
                category=normalize_category(opp.get("category", "Other")),
                object_label=opp.get("object_label", "unknown"),
                screen_time_seconds=screen_time,
                naturalness_score=naturalness,
                brand_safety_score=float(data.get("brand_safety_score", 50.0)),
                complexity=opp.get("complexity", "low"),
                rights_status="clear",  # type: ignore[arg-type]
                estimated_value_usd=_estimate_value(naturalness, screen_time),
                is_primary=(i == 1),
                placement_zone=opp.get("placement_zone", "Natural prop position"),
                placement_notes=opp.get("notes", ""),
            )
        )
    return opps


def _estimate_value(naturalness: float, screen_time: int) -> float:
    """Rough fee estimate from naturalness and screen time. Not binding."""
    base = 5000.0
    naturalness_mult = naturalness / 100.0
    time_mult = min(screen_time / 30.0, 3.0)
    return round(base * (1 + naturalness_mult * 8) * time_mult, -2)


def _infer_mime(uri: str) -> str:
    uri_lower = uri.lower()
    if uri_lower.endswith(".mp4"):
        return "video/mp4"
    if uri_lower.endswith((".mov", ".qt")):
        return "video/quicktime"
    if uri_lower.endswith(".avi"):
        return "video/avi"
    if uri_lower.endswith(".webm"):
        return "video/webm"
    if uri_lower.endswith(".mkv"):
        return "video/x-matroska"
    return "video/mp4"
