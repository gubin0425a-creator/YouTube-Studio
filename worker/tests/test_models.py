from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.models import RenderRequest


def valid_payload() -> dict[str, object]:
    return {
        "topic": "AI 생산성",
        "language": "ko-KR",
        "durationSeconds": 45,
        "publishAt": datetime(2030, 1, 2, 9, tzinfo=UTC).isoformat(),
        "idempotencyKey": "main:2030-01-02",
        "channelKey": "main",
    }


def test_camel_case_request_is_accepted() -> None:
    request = RenderRequest.model_validate(valid_payload())
    assert request.duration_seconds == 45
    assert request.publish_at.tzinfo is not None
    assert request.model_dump(by_alias=True)["idempotencyKey"] == "main:2030-01-02"


def test_publish_at_requires_timezone() -> None:
    payload = valid_payload()
    payload["publishAt"] = "2030-01-02T09:00:00"
    with pytest.raises(ValidationError):
        RenderRequest.model_validate(payload)


def test_reviewed_title_and_narration_must_be_supplied_together() -> None:
    payload = valid_payload()
    payload["title"] = "제목만 있음"
    with pytest.raises(ValidationError):
        RenderRequest.model_validate(payload)
