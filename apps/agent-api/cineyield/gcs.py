"""Google Cloud Storage adapter for CineYield video ingestion.

Uses Application Default Credentials (ADC) — no service account JSON needed.
Authenticate via: gcloud auth application-default login

Never makes media publicly readable.
"""
from __future__ import annotations

import logging
import mimetypes
import uuid
from pathlib import Path

from .config import get_settings

logger = logging.getLogger(__name__)

SUPPORTED_VIDEO_TYPES = {
    "video/mp4", "video/quicktime", "video/avi",
    "video/webm", "video/x-matroska",
}
MAX_VIDEO_BYTES = 500 * 1024 * 1024  # 500 MB


def _get_bucket():
    """Return the GCS bucket object (lazy import — only when GCS is configured)."""
    from google.cloud import storage  # type: ignore[import-untyped]
    settings = get_settings()
    if not settings.gcs_configured:
        raise RuntimeError(
            "GCS is not configured. Set GCS_BUCKET_NAME in .env."
        )
    client = storage.Client(project=settings.google_cloud_project or None)
    return client.bucket(settings.gcs_bucket_name)


def upload_video(
    data: bytes,
    filename: str,
    content_type: str,
    asset_id: str | None = None,
) -> str:
    """Upload video bytes to GCS. Returns the gs:// URI.

    Object is private (no ACL). A generated object name is used — the original
    filename is stored as metadata only.
    """
    if content_type not in SUPPORTED_VIDEO_TYPES:
        raise ValueError(f"Unsupported video type: {content_type}")
    if len(data) > MAX_VIDEO_BYTES:
        raise ValueError(f"File too large: {len(data) / 1024**2:.1f} MB > 500 MB")

    ext = mimetypes.guess_extension(content_type) or ".mp4"
    ext = ext.replace(".jpe", ".jpg")  # mimetypes quirk
    prefix = asset_id or uuid.uuid4().hex[:12]
    object_name = f"cineyield/videos/{prefix}/{uuid.uuid4().hex[:8]}{ext}"

    bucket = _get_bucket()
    blob = bucket.blob(object_name)
    blob.metadata = {
        "original_filename": filename,
        "cineyield_asset_id": prefix,
        "uploaded_by": "cineyield-ingest-api",
    }
    blob.upload_from_string(data, content_type=content_type)

    gcs_uri = f"gs://{bucket.name}/{object_name}"
    logger.info("Uploaded %s → %s (%d bytes)", filename, gcs_uri, len(data))
    return gcs_uri


def upload_video_file(path: str | Path, asset_id: str | None = None) -> str:
    """Upload a local video file to GCS. Returns the gs:// URI."""
    path = Path(path)
    content_type, _ = mimetypes.guess_type(str(path))
    content_type = content_type or "video/mp4"
    data = path.read_bytes()
    return upload_video(data, path.name, content_type, asset_id=asset_id)


def gcs_uri_exists(gcs_uri: str) -> bool:
    """Check whether a gs:// URI is accessible."""
    try:
        from google.cloud import storage  # type: ignore[import-untyped, attr-defined]
        settings = get_settings()
        client = storage.Client(project=settings.google_cloud_project or None)
        if not gcs_uri.startswith("gs://"):
            return False
        without_scheme = gcs_uri[5:]
        bucket_name, _, object_name = without_scheme.partition("/")
        blob = client.bucket(bucket_name).blob(object_name)
        return blob.exists()
    except Exception:
        return False


def delete_video(gcs_uri: str) -> bool:
    """Delete a video from GCS. Returns True on success."""
    try:
        from google.cloud import storage  # type: ignore[import-untyped, attr-defined]
        settings = get_settings()
        client = storage.Client(project=settings.google_cloud_project or None)
        without_scheme = gcs_uri[5:]
        bucket_name, _, object_name = without_scheme.partition("/")
        client.bucket(bucket_name).blob(object_name).delete()
        logger.info("Deleted GCS object: %s", gcs_uri)
        return True
    except Exception as exc:
        logger.warning("GCS delete failed for %s: %s", gcs_uri, exc)
        return False
