"""Google generative-media adapters for branded placement approval.

Nano Banana edits the real extracted frame. Veo animates only an approved
reference frame, after Gemini has re-read the real source segment to derive a
continuity brief. This matches the capabilities Google exposes: Veo is not
misrepresented as an arbitrary in-place video editor.
"""
from __future__ import annotations

import logging
from typing import Any

from ..config import get_settings
from ..gcs import download_media_bytes, upload_media_bytes

logger = logging.getLogger(__name__)

CREATIVE_GUARDRAILS = [
    "Preserve every person, face, wardrobe detail, set element, and narrative action.",
    "Add only the approved sponsor product; do not redesign or restyle the scene.",
    "Match the source camera angle, perspective, focal length, depth of field, and scale.",
    "Match practical lighting, color temperature, reflections, contact shadows, and occlusion.",
    "Keep logos physically printed on the product; never add captions, callouts, or floating text.",
    "Keep the placement natural and secondary to the story; no character endorsement is implied.",
    "Maintain the approved brand-safety context and avoid competitor marks.",
]


def _client(*, location: str):
    from google import genai

    settings = get_settings()
    if settings.google_cloud_project:
        return genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=location,
        )
    return genai.Client(api_key=settings.google_api_key)


def build_placement_instructions(context: dict[str, Any], custom: str = "") -> str:
    product = context.get("product_line") or context.get("object_label") or "sponsor product"
    category = context.get("category") or "product"
    base = (
        f"Place one {context.get('brand_name', 'sponsor')} {product} in the natural "
        f"{category.lower()} opportunity represented by the existing "
        f"{context.get('object_label', 'prop')} area. Keep it plausible for the action, "
        "with correct physical scale and without covering faces, hands, or story-critical objects."
    )
    return f"{base} Producer direction: {custom.strip()}" if custom.strip() else base


def build_image_prompt(
    context: dict[str, Any],
    placement_instructions: str,
    *,
    generation_number: int,
) -> str:
    guardrails = "\n".join(f"- {rule}" for rule in CREATIVE_GUARDRAILS)
    return f"""You are finishing a premium film frame for an approved product-placement review.

SOURCE SCENE
Title: {context.get('scene_name', 'Scene')}
Description: {context.get('scene_summary', '')}
Mood: {context.get('mood', '')}
Narrative weight: {context.get('narrative_weight', '')}

SPONSOR BRIEF
Sponsor: {context.get('brand_name', '')}
Campaign: {context.get('campaign_name', '')}
Product: {context.get('product_line', '')}
Commercial brief: {context.get('brand_brief', '')}

PLACEMENT DIRECTION
{placement_instructions}

NON-NEGOTIABLE CREATIVE GUARDRAILS
{guardrails}

Return one complete 16:9 photorealistic edited frame. Treat the supplied image as the
locked plate: preserve its composition and edit only what is necessary to integrate the
sponsor product. The product must have believable geometry, contact, reflections, focus,
lighting, and occlusion. No presentation board, split screen, label, frame, crop, outline,
glow, arrow, UI, watermark, or explanatory text. Revision {generation_number}."""


def generate_branded_frame(
    context: dict[str, Any],
    *,
    placement_instructions: str,
    generation_id: str,
    generation_number: int,
) -> tuple[str, str]:
    """Run Nano Banana 2 against the extracted source frame and upload its output."""
    from google.genai import types

    settings = get_settings()
    media = context.get("media") or {}
    frame_uri = str(media.get("frame_uri") or "")
    if not frame_uri:
        raise RuntimeError("The selected scene has no extracted source frame")
    frame_bytes = download_media_bytes(frame_uri)
    prompt = build_image_prompt(
        context,
        placement_instructions,
        generation_number=generation_number,
    )
    client = _client(location=settings.nano_banana_region)
    response = client.models.generate_content(
        model=settings.nano_banana_model,
        contents=[
            types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg"),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
            image_config=types.ImageConfig(
                aspect_ratio="16:9",
                image_size="2K",
                output_mime_type="image/png",
            ),
        ),
    )
    image_bytes: bytes | None = None
    for candidate in response.candidates or []:
        if not candidate.content:
            continue
        for part in candidate.content.parts or []:
            if part.inline_data and part.inline_data.data:
                image_bytes = part.inline_data.data
                break
        if image_bytes:
            break
    if not image_bytes:
        raise RuntimeError("Nano Banana returned no image output")

    output_uri = upload_media_bytes(
        image_bytes,
        f"cineyield/generations/{context['proposal_id']}/{generation_id}/branded-frame.png",
        "image/png",
        metadata={
            "cineyield_generation_id": generation_id,
            "cineyield_model": settings.nano_banana_model,
            "cineyield_media_role": "branded-reference-frame",
        },
    )
    return output_uri, prompt


def build_continuity_brief(context: dict[str, Any], approved_frame_uri: str) -> str:
    """Use Gemini to convert the real source segment into Veo continuity constraints."""
    from google.genai import types

    settings = get_settings()
    media = context.get("media") or {}
    segment_uri = str(media.get("segment_video_uri") or "")
    if not segment_uri:
        raise RuntimeError("The selected scene has no source segment")
    client = _client(location=settings.google_cloud_region or "us-central1")
    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=[
            types.Part.from_uri(file_uri=segment_uri, mime_type="video/mp4"),
            types.Part.from_uri(file_uri=approved_frame_uri, mime_type="image/png"),
            """Analyze the uploaded source segment as a continuity supervisor. The image is an
approved branded first-frame proposal. Return a concise production brief describing only:
camera position and motion, subject motion, timing, environment motion, lighting continuity,
depth/focus behavior, and how the approved product should remain physically stable. Do not
invent new shots, cuts, people, dialogue, logos, or actions. Plain text only, maximum 140 words.""",
        ],
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=350),
    )
    brief = (response.text or "").strip()
    if not brief:
        raise RuntimeError("Gemini returned no source-clip continuity brief")
    return brief


def build_video_prompt(
    context: dict[str, Any],
    placement_instructions: str,
    continuity_brief: str,
) -> str:
    return f"""Create a seamless branded replacement shot that begins exactly from the supplied
approved frame. Preserve the original scene, cast, environment, composition, mood, and color.

SOURCE-SEGMENT CONTINUITY SUPERVISION:
{continuity_brief}

APPROVED SPONSOR PLACEMENT:
Sponsor: {context.get('brand_name', '')}
Product: {context.get('product_line', '')}
Direction: {placement_instructions}

The product stays geometrically stable, correctly occluded, naturally lit, and subordinate to
the story for the entire shot. No new shot, cut, camera angle, character, wardrobe, dialogue,
music, floating logo, caption, title, or graphic overlay. Photorealistic live-action cinema."""


def start_replacement_video(
    context: dict[str, Any],
    *,
    approved_frame_uri: str,
    placement_instructions: str,
    generation_id: str,
) -> tuple[str, str]:
    """Start a Veo 3.1 operation and return (operation_name, prompt)."""
    from google.genai import types

    settings = get_settings()
    continuity = build_continuity_brief(context, approved_frame_uri)
    prompt = build_video_prompt(context, placement_instructions, continuity)
    client = _client(location=settings.veo_region)
    output_prefix = (
        f"gs://{settings.gcs_bucket_name}/cineyield/generations/"
        f"{context['proposal_id']}/{generation_id}/video/"
    )
    operation = client.models.generate_videos(
        model=settings.veo_model,
        prompt=prompt,
        image=types.Image(gcs_uri=approved_frame_uri, mime_type="image/png"),
        config=types.GenerateVideosConfig(
            number_of_videos=1,
            output_gcs_uri=output_prefix,
            duration_seconds=8,
            aspect_ratio="16:9",
            resolution="1080p",
            generate_audio=True,
            person_generation="allow_adult",
            negative_prompt=(
                "new shot, jump cut, camera discontinuity, altered face, altered wardrobe, "
                "duplicate product, floating object, warped logo, caption, title, UI, watermark"
            ),
        ),
    )
    if not operation.name:
        raise RuntimeError("Veo started without an operation identifier")
    return operation.name, prompt


def poll_replacement_video(operation_name: str) -> tuple[str, str | None, str | None]:
    """Return (status, output_uri, error) for a persisted Veo operation."""
    from google.genai import types

    settings = get_settings()
    client = _client(location=settings.veo_region)
    operation = client.operations.get(types.GenerateVideosOperation(name=operation_name))
    if not operation.done:
        return "PROCESSING", None, None
    if operation.error:
        return "FAILED", None, str(operation.error)
    payload = operation.result or operation.response
    videos = payload.generated_videos if payload else None
    if not videos or not videos[0].video:
        reasons = payload.rai_media_filtered_reasons if payload else None
        return "FAILED", None, f"Veo returned no video. Safety reasons: {reasons or 'none provided'}"
    video = videos[0].video
    if video.uri:
        return "COMPLETED", video.uri, None
    if video.video_bytes:
        uri = upload_media_bytes(
            video.video_bytes,
            f"cineyield/generations/veo/{operation_name.rsplit('/', 1)[-1]}.mp4",
            video.mime_type or "video/mp4",
        )
        return "COMPLETED", uri, None
    return "FAILED", None, "Veo completed without a downloadable video"
