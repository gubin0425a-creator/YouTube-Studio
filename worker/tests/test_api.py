import os
import tempfile

from fastapi.testclient import TestClient

os.environ.setdefault("VIDEO_WORKER_TOKEN", "test-token-that-is-definitely-longer-than-32-characters")
os.environ.setdefault("STUDIO_ACCESS_PASSWORD", "test-studio-password-long-enough")
os.environ.setdefault("STUDIO_SESSION_SECRET", "test-session-secret-that-is-definitely-longer-than-32")
os.environ.setdefault("STUDIO_SECURE_COOKIE", "false")
os.environ.setdefault("STUDIO_HOST", "testserver")
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="youtube-worker-test-"))

from app.main import app  # noqa: E402


client = TestClient(app)


def test_health_is_public_but_does_not_expose_secrets() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "video_worker_token" not in response.text


def test_studio_ui_and_pwa_assets_are_served() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="pane-youtubot"' in response.text
    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.json()["display"] == "standalone"
    worker = client.get("/service-worker.js")
    assert worker.status_code == 200
    assert worker.headers["service-worker-allowed"] == "/"
    assert client.get("/assets/icon-192.png").status_code == 200


def test_job_routes_require_worker_token() -> None:
    response = client.get("/v1/jobs/unknown")
    assert response.status_code == 401


def test_valid_worker_token_reaches_route() -> None:
    response = client.get(
        "/v1/jobs/unknown",
        headers={"X-Worker-Token": os.environ["VIDEO_WORKER_TOKEN"]},
    )
    assert response.status_code == 404


def login() -> None:
    response = client.post(
        "/v1/auth/login", json={"password": os.environ["STUDIO_ACCESS_PASSWORD"]}
    )
    assert response.status_code == 200


def test_studio_login_and_persistent_conversation_api() -> None:
    login()
    created = client.post(
        "/v1/chat/conversations",
        json={
            "title": "채널 분석",
            "profile": {
                "ownChannelUrl": "https://youtube.com/@mine",
                "benchmarkChannelUrl": "https://youtube.com/@benchmark",
                "ownVideoUrls": [],
                "benchmarkVideoUrls": [],
            },
        },
    )
    assert created.status_code == 200
    conversation_id = created.json()["id"]
    listed = client.get("/v1/chat/conversations")
    assert any(item["id"] == conversation_id for item in listed.json())
    exported = client.get(f"/v1/chat/conversations/{conversation_id}/export")
    assert exported.status_code == 200
    assert exported.json()["conversation"]["title"] == "채널 분석"


def test_automation_config_accepts_worker_or_session() -> None:
    worker = client.get(
        "/v1/automation/config",
        headers={"X-Worker-Token": os.environ["VIDEO_WORKER_TOKEN"]},
    )
    assert worker.status_code == 200
    assert worker.json()["timezone"] == "Asia/Seoul"

    login()
    config = worker.json()
    config["publishHour"] = 20
    updated = client.put("/v1/automation/config", json=config)
    assert updated.status_code == 200
    assert updated.json()["publishHour"] == 20
