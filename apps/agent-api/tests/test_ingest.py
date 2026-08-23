"""Tests for the video ingest API endpoints."""
import io

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

MP4_HEADER = b"\x00\x00\x00\x18ftypisom"  # minimal MP4 magic bytes


def _make_upload(
    filename: str = "clip.mp4",
    content_type: str = "video/mp4",
    content: bytes = MP4_HEADER + b"\x00" * 1024,
):
    return {
        "file": (filename, io.BytesIO(content), content_type),
    }


def test_upload_unsupported_format():
    resp = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("doc.pdf", io.BytesIO(b"fake"), "application/pdf")},
    )
    assert resp.status_code == 415
    body = resp.json()
    assert "Unsupported media type" in body["detail"]


def test_upload_mp4_returns_202():
    resp = client.post("/api/v1/ingest/upload", files=_make_upload())
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] in ("queued", "pending_credentials")
    assert body["job_id"].startswith("job_")
    assert body["asset_id"].startswith("asset_")
    assert body["filename"] == "clip.mp4"
    assert body["size_bytes"] > 0


def test_upload_video_quicktime():
    resp = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("scene.mov", io.BytesIO(b"\x00" * 512), "video/quicktime")},
    )
    assert resp.status_code == 202


def test_upload_webm():
    resp = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("clip.webm", io.BytesIO(b"\x00" * 512), "video/webm")},
    )
    assert resp.status_code == 202


def test_status_not_found():
    resp = client.get("/api/v1/ingest/status/job_doesnotexist")
    assert resp.status_code == 404


def test_status_after_upload():
    upload = client.post("/api/v1/ingest/upload", files=_make_upload())
    assert upload.status_code == 202
    job_id = upload.json()["job_id"]

    status = client.get(f"/api/v1/ingest/status/{job_id}")
    assert status.status_code == 200
    body = status.json()
    assert body["job_id"] == job_id
    # "failed" is valid when Gemini rejects the fake test video content
    assert body["status"] in ("queued", "analyzing", "completed", "pending_credentials", "failed")


def test_formats_endpoint():
    resp = client.get("/api/v1/ingest/formats")
    assert resp.status_code == 200
    body = resp.json()
    assert "video/mp4" in body["supported_mime_types"]
    assert body["max_file_size_mb"] > 0


def test_upload_stores_correct_size():
    payload = b"\x00" * 4096
    resp = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("test.mp4", io.BytesIO(payload), "video/mp4")},
    )
    assert resp.status_code == 202
    assert resp.json()["size_bytes"] == 4096
