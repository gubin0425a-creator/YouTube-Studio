from pathlib import Path

import pytest

from app.store import JobBusyError, JobStore


def test_job_is_idempotent_and_tracks_upload(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    request = {"topic": "테스트"}

    claim = store.claim("main:2030-01-01", request)
    assert claim.cached_result is None

    with pytest.raises(JobBusyError):
        store.claim("main:2030-01-01", request)

    result = {
        "jobId": claim.job_id,
        "status": "completed",
        "title": "테스트",
        "description": "설명",
        "tags": ["Shorts"],
        "publishAt": "2030-01-01T09:00:00+00:00",
        "videoUrl": "http://worker/v1/files/id",
        "jobUrl": "http://worker/v1/jobs/id",
        "durationSeconds": 30,
        "alreadyUploaded": False,
        "youtubeVideoId": None,
        "attribution": None,
    }
    store.complete(claim.job_id, result)

    cached = store.claim("main:2030-01-01", request).cached_result
    assert cached is not None
    assert cached["alreadyUploaded"] is False

    marked = store.mark_uploaded(claim.job_id, "dQw4w9WgXcQ")
    assert marked is not None
    assert marked["alreadyUploaded"] is True

    uploaded = store.claim("main:2030-01-01", request).cached_result
    assert uploaded is not None
    assert uploaded["youtubeVideoId"] == "dQw4w9WgXcQ"
