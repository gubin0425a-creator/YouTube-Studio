import base64
import json
import logging
from typing import Any

import httpx

from .config import Settings
from .models import AutomationConfig, ChatProposal

logger = logging.getLogger(__name__)


class ChatServiceError(RuntimeError):
    pass


async def generate_chat_response(
    *,
    history: list[dict[str, Any]],
    image_parts: list[dict[str, Any]],
    channel_data: dict[str, Any],
    automation_config: AutomationConfig,
    settings: Settings,
) -> ChatProposal:
    if not settings.gemini_api_key:
        raise ChatServiceError("GEMINI_API_KEY가 없어 유투봇을 실행할 수 없습니다.")

    config_json = json.dumps(
        automation_config.model_dump(mode="json", by_alias=True), ensure_ascii=False
    )
    channel_json = json.dumps(channel_data, ensure_ascii=False)
    system_instruction = f"""
당신은 이 서비스 전용 한국어 AI 어시스턴트 '유투봇'입니다.
YouTube 채널 운영, n8n 자동화, 영상 기획, 제목·설명·대본 교정, 업로드 사진 분석을 돕습니다.

원칙:
1. 제공된 YouTube API 데이터만 실데이터라고 부르고, 데이터가 없으면 추정임을 명시하세요.
2. 조회수 조작, 스팸, 저작권 침해, 기만적 메타데이터를 권하지 마세요.
3. 사용자가 보낸 사진을 분석하되 민감한 개인 정보나 불확실한 인물 식별을 단정하지 마세요.
4. 코드·문구·대본 수정 요청에는 바로 사용할 수 있는 수정본을 답변에 포함하세요.
5. 실제 배포/업로드/설정 변경을 완료했다고 거짓말하지 마세요.
6. 자동화 설정 변경을 명시적으로 요청한 경우에만 suggestedAutomationConfig를 채우세요.
   현재 설정 전체를 복사한 뒤 요청한 필드만 바꾸고, 그 외에는 null로 두세요.
7. 공개 게시 전에는 사용자가 사실성·저작권·아동용·합성 콘텐츠 표시를 확인하도록 안내하세요.

현재 자동화 설정:
{config_json}

현재 채널/영상 실데이터(JSON, 없으면 빈 객체):
{channel_json}
""".strip()

    contents: list[dict[str, Any]] = []
    for message in history:
        role = "model" if message.get("role") == "model" else "user"
        text = str(message.get("text") or "").strip()
        if not text:
            continue
        parts: list[dict[str, Any]] = [{"text": text}]
        parts.extend(message.get("_imageParts") or [])
        contents.append({"role": role, "parts": parts})
    if not contents or contents[-1]["role"] != "user":
        raise ChatServiceError("마지막 사용자 메시지가 없습니다.")
    contents[-1]["parts"].extend(image_parts)

    config_schema = {
        "type": "OBJECT",
        "nullable": True,
        "properties": {
            "topicPool": {"type": "STRING"},
            "timezone": {"type": "STRING"},
            "publishHour": {"type": "INTEGER"},
            "publishMinute": {"type": "INTEGER"},
            "minimumLeadMinutes": {"type": "INTEGER"},
            "durationSeconds": {"type": "INTEGER"},
            "language": {"type": "STRING"},
            "voice": {"type": "STRING"},
            "channelKey": {"type": "STRING"},
        },
        "required": [
            "topicPool",
            "timezone",
            "publishHour",
            "publishMinute",
            "minimumLeadMinutes",
            "durationSeconds",
            "language",
            "voice",
            "channelKey",
        ],
    }
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "reply": {"type": "STRING"},
            "suggestedAutomationConfig": config_schema,
        },
        "required": ["reply", "suggestedAutomationConfig"],
    }
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.65,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
            "responseSchema": response_schema,
        },
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.gemini_api_key},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        candidates = body.get("candidates") or []
        if not candidates:
            raise ChatServiceError("안전 필터 또는 빈 응답으로 답변을 만들지 못했습니다.")
        text = candidates[0]["content"]["parts"][0]["text"]
        return ChatProposal.model_validate_json(text)
    except ChatServiceError:
        raise
    except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Gemini chat failed: %s", type(exc).__name__)
        raise ChatServiceError("유투봇 응답 생성에 실패했습니다. API 키·모델·할당량을 확인하세요.") from exc


def inline_image_part(data: bytes, mime_type: str) -> dict[str, Any]:
    return {
        "inlineData": {
            "mimeType": mime_type,
            "data": base64.b64encode(data).decode("ascii"),
        }
    }
