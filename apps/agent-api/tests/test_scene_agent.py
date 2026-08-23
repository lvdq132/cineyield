"""Tests for SceneAgent JSON parsing — no Gemini credentials required."""

from cineyield.agents.scene_agent import _infer_mime, _parse_scene_json


def test_parse_valid_gemini_json():
    raw = """
{
  "name": "Rooftop Sunrise",
  "summary": "Two characters share a quiet moment on a rooftop at dawn.",
  "mood": "Reflective",
  "narrative_weight": "High",
  "brand_safety_score": 94,
  "duration_seconds": 45,
  "detected_objects": [
    {
      "label": "Wireless headphones",
      "category": "Electronics",
      "confidence": 92.5,
      "is_primary": true,
      "timecode_start": "00:00:05",
      "timecode_end": "00:00:30"
    }
  ]
}
"""
    result = _parse_scene_json(raw, "scene_001", "asset_001", "gemini-2.0-flash")
    assert result.name == "Rooftop Sunrise"
    assert result.mood == "Reflective"
    assert result.brand_safety_score == 94.0
    assert result.duration_seconds == 45
    assert result.narrative_weight == "High"
    assert len(result.detected_objects) == 1
    assert result.detected_objects[0].label == "Wireless headphones"
    assert result.detected_objects[0].is_primary is True
    assert result.gemini_model_used == "gemini-2.0-flash"


def test_parse_json_with_markdown_fences():
    raw = """```json
{
  "name": "Chase Scene",
  "summary": "Action sequence.",
  "mood": "Tense",
  "narrative_weight": "High",
  "brand_safety_score": 40,
  "duration_seconds": 30,
  "detected_objects": []
}
```"""
    result = _parse_scene_json(raw, "scene_002", "asset_002", "gemini-2.0-flash")
    assert result.name == "Chase Scene"
    assert result.mood == "Tense"


def test_parse_malformed_json_returns_safe_fallback():
    raw = "This is not JSON at all."
    result = _parse_scene_json(raw, "scene_003", "asset_003", "gemini-2.0-flash")
    assert result.scene_id == "scene_003"
    assert result.brand_safety_score == 50.0
    assert result.mood == "Unknown"


def test_parse_empty_detected_objects():
    raw = '{"name": "Empty", "summary": "Nothing detected.", "mood": "Calm", "narrative_weight": "Low", "brand_safety_score": 80, "duration_seconds": 10, "detected_objects": []}'
    result = _parse_scene_json(raw, "s", "a", "gemini-flash")
    assert result.detected_objects == []


def test_brand_safety_score_clamped():
    raw = '{"name": "X", "summary": "", "mood": "", "narrative_weight": "Low", "brand_safety_score": 150, "duration_seconds": 0, "detected_objects": []}'
    result = _parse_scene_json(raw, "s", "a", "gemini-flash")
    assert result.brand_safety_score == 100.0


def test_infer_mime_mp4():
    assert _infer_mime("gs://bucket/video.mp4") == "video/mp4"


def test_infer_mime_mov():
    assert _infer_mime("/tmp/clip.MOV") == "video/quicktime"


def test_infer_mime_webm():
    assert _infer_mime("scene.webm") == "video/webm"


def test_infer_mime_default():
    assert _infer_mime("unknown_file") == "video/mp4"
