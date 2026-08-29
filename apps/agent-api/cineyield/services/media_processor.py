"""Deterministic source-video preprocessing for the judged CineYield flow.

The upload is preserved verbatim. FFmpeg then creates a bounded source segment
for replacement generation and extracts a representative frame from that exact
segment. No stock or fixture image enters the live path.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..gcs import upload_media_file, upload_video_file


@dataclass(frozen=True)
class PreparedSceneMedia:
    source_video_uri: str
    segment_video_uri: str
    frame_uri: str
    frame_time_seconds: float
    segment_start_seconds: float
    segment_duration_seconds: float
    source_duration_seconds: float
    source_mime_type: str


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("FFmpeg is required for real frame extraction") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "FFmpeg failed").strip()[-800:]
        raise RuntimeError(f"Video preprocessing failed: {detail}") from exc


def probe_duration(video_path: str | Path) -> float:
    result = _run([
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(video_path),
    ])
    try:
        return max(0.1, float(json.loads(result.stdout)["format"]["duration"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("Could not determine uploaded video duration") from exc


def prepare_scene_media(
    video_path: str | Path,
    *,
    asset_id: str,
    source_mime_type: str = "video/mp4",
    max_segment_seconds: float = 8.0,
) -> PreparedSceneMedia:
    """Upload source, isolate its central <=8s scene window, and extract a frame."""
    source_path = Path(video_path)
    duration = probe_duration(source_path)
    segment_duration = min(max_segment_seconds, duration)
    segment_start = max(0.0, (duration - segment_duration) / 2.0)
    frame_offset = min(max(0.25, segment_duration * 0.42), max(0.25, segment_duration - 0.1))
    frame_time = segment_start + frame_offset

    source_uri = upload_video_file(source_path, asset_id=asset_id)

    with tempfile.TemporaryDirectory(prefix="cineyield-media-") as temp_dir:
        segment_path = Path(temp_dir) / "source-segment.mp4"
        frame_path = Path(temp_dir) / "analysis-frame.jpg"

        _run([
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{segment_start:.3f}",
            "-i",
            str(source_path),
            "-t",
            f"{segment_duration:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(segment_path),
        ])
        _run([
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{frame_time:.3f}",
            "-i",
            str(source_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(frame_path),
        ])

        metadata = {
            "cineyield_asset_id": asset_id,
            "derived_from": source_uri,
        }
        segment_uri = upload_media_file(
            segment_path,
            f"cineyield/scenes/{asset_id}/source-segment.mp4",
            "video/mp4",
            metadata={**metadata, "cineyield_media_role": "source-segment"},
        )
        frame_uri = upload_media_file(
            frame_path,
            f"cineyield/scenes/{asset_id}/analysis-frame.jpg",
            "image/jpeg",
            metadata={**metadata, "cineyield_media_role": "analysis-frame"},
        )

    return PreparedSceneMedia(
        source_video_uri=source_uri,
        segment_video_uri=segment_uri,
        frame_uri=frame_uri,
        frame_time_seconds=round(frame_time, 3),
        segment_start_seconds=round(segment_start, 3),
        segment_duration_seconds=round(segment_duration, 3),
        source_duration_seconds=round(duration, 3),
        source_mime_type=source_mime_type,
    )
