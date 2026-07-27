import asyncio
import hashlib
import hmac
import io
import json
import secrets
import shutil
import time
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageOps, UnidentifiedImageError

from .chat_service import ChatServiceError, generate_chat_response, inline_image_part
from .config import Settings
from .models import (
    AutomationConfig,
    ChannelProfile,
    ChatResponse,
    ConversationCreate,
    ConversationUpdate,
    LoginRequest,
)
from .studio_store import StudioStore
from .youtube_data import YouTubeDataClient, YouTubeDataError

SESSION_COOKIE = "youtubot_session"
_failed_logins: dict[str, list[float]] = {}
_youtube_cache: dict[str, tuple[float, dict[str, Any], list[str]]] = {}


def build_studio_router(settings: Settings, store: StudioStore) -> APIRouter:
    router = APIRouter()

    def issue_session() -> str:
        expires = int(time.time()) + settings.studio_session_days * 86400
        payload = f"{expires}.{secrets.token_urlsafe(24)}"
        signature = hmac.new(
            settings.studio_session_secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return f"{payload}.{signature}"

    def session_valid(token: str | None) -> bool:
        if not token:
            return False
        try:
            expires_text, nonce, signature = token.split(".", 2)
            payload = f"{expires_text}.{nonce}"
            expected = hmac.new(
                settings.studio_session_secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected) and int(expires_text) > int(time.time())
        except (ValueError, TypeError):
            return False

    async def require_session(request: Request) -> None:
        if not session_valid(request.cookies.get(SESSION_COOKIE)):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="login required")
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and origin.rstrip("/") != settings.studio_origin:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid origin")

    async def require_worker_or_session(
        request: Request, x_worker_token: str = Header(default="")
    ) -> None:
        if hmac.compare_digest(x_worker_token, settings.video_worker_token):
            return
        await require_session(request)

    @router.get("/v1/auth/status")
    async def auth_status(request: Request) -> dict[str, bool]:
        return {"authenticated": session_valid(request.cookies.get(SESSION_COOKIE))}

    @router.post("/v1/auth/login")
    async def login(request: Request, body: LoginRequest) -> dict[str, bool]:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        failures = [stamp for stamp in _failed_logins.get(client_ip, []) if stamp > now - 900]
        _failed_logins[client_ip] = failures
        if len(failures) >= 10:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="try later")
        if not hmac.compare_digest(body.password, settings.studio_access_password):
            failures.append(now)
            await asyncio.sleep(0.6)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="wrong password")
        _failed_logins.pop(client_ip, None)
        response = JSONResponse({"authenticated": True})
        response.set_cookie(
            SESSION_COOKIE,
            issue_session(),
            max_age=settings.studio_session_days * 86400,
            httponly=True,
            secure=settings.studio_secure_cookie,
            samesite="strict",
            path="/",
        )
        return response

    @router.post("/v1/auth/logout", dependencies=[Depends(require_session)])
    async def logout() -> JSONResponse:
        response = JSONResponse({"authenticated": False})
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    @router.get("/v1/chat/conversations", dependencies=[Depends(require_session)])
    async def list_conversations() -> list[dict[str, Any]]:
        return store.list_conversations()

    @router.post("/v1/chat/conversations", dependencies=[Depends(require_session)])
    async def create_conversation(body: ConversationCreate) -> dict[str, Any]:
        return store.create_conversation(body.title, body.profile)

    @router.patch(
        "/v1/chat/conversations/{conversation_id}", dependencies=[Depends(require_session)]
    )
    async def update_conversation(
        conversation_id: str, body: ConversationUpdate
    ) -> dict[str, Any]:
        updated = store.update_conversation(
            conversation_id, title=body.title, profile=body.profile
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
        return updated

    @router.delete(
        "/v1/chat/conversations/{conversation_id}", dependencies=[Depends(require_session)]
    )
    async def delete_conversation(conversation_id: str) -> dict[str, bool]:
        deleted = store.delete_conversation(conversation_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
        shutil.rmtree(settings.chat_images_dir / conversation_id, ignore_errors=True)
        return {"deleted": True}

    @router.get(
        "/v1/chat/conversations/{conversation_id}/messages",
        dependencies=[Depends(require_session)],
    )
    async def get_messages(conversation_id: str) -> list[dict[str, Any]]:
        if store.get_conversation(conversation_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
        return store.get_messages(conversation_id)

    @router.get(
        "/v1/chat/conversations/{conversation_id}/export",
        dependencies=[Depends(require_session)],
    )
    async def export_conversation(conversation_id: str) -> JSONResponse:
        conversation = store.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
        response = JSONResponse(
            {"conversation": conversation, "messages": store.get_messages(conversation_id)}
        )
        response.headers["Content-Disposition"] = (
            f'attachment; filename="youtubot-{conversation_id}.json"'
        )
        return response

    @router.get(
        "/v1/chat/images/{conversation_id}/{filename}", dependencies=[Depends(require_session)]
    )
    async def get_chat_image(conversation_id: str, filename: str) -> FileResponse:
        if not _valid_uuidish(conversation_id) or not _valid_image_name(filename):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="image not found")
        path = settings.chat_images_dir / conversation_id / filename
        if not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="image not found")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private"})

    @router.post(
        "/v1/chat/conversations/{conversation_id}/messages",
        response_model=ChatResponse,
        response_model_by_alias=True,
        dependencies=[Depends(require_session)],
    )
    async def send_message(
        conversation_id: str,
        message: Annotated[str, Form(max_length=12000)] = "",
        images: Annotated[list[UploadFile] | None, File()] = None,
    ) -> ChatResponse:
        images = images or []
        conversation = store.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
        text = message.strip()
        if not text and not images:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="empty message")
        if len(images) > settings.max_chat_images:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"up to {settings.max_chat_images} images are allowed",
            )

        image_records: list[dict[str, Any]] = []
        image_parts: list[dict[str, Any]] = []
        for upload in images:
            record, encoded = await _save_image(upload, conversation_id, settings)
            image_records.append(record)
            image_parts.append(inline_image_part(encoded, "image/jpeg"))

        stored_text = text or "업로드한 사진을 분석해 주세요."
        store.add_message(
            conversation_id, "user", stored_text, images=image_records
        )
        if conversation["title"] == "새 대화":
            store.update_conversation(conversation_id, title=stored_text[:40])

        profile = ChannelProfile.model_validate(conversation["profile"])
        warnings: list[str] = []
        channel_data: dict[str, Any] = {}
        cache_key = json.dumps(profile.model_dump(mode="json", by_alias=True), sort_keys=True)
        cached = _youtube_cache.get(cache_key)
        if cached and cached[0] > time.time():
            _, channel_data, cached_warnings = cached
            warnings.extend(cached_warnings)
        else:
            try:
                channel_data, youtube_warnings = await YouTubeDataClient(
                    settings.youtube_data_api_key
                ).enrich_profile(profile)
                warnings.extend(youtube_warnings)
                _youtube_cache[cache_key] = (time.time() + 900, channel_data, youtube_warnings)
            except YouTubeDataError as exc:
                warnings.append(str(exc))

        history = store.get_messages(conversation_id, limit=settings.chat_history_messages)
        # Keep follow-up questions about recently uploaded photos useful without
        # resending an unlimited image archive (and its token cost) every turn.
        previous_image_budget = 3
        for historical in reversed(history[:-1]):
            if previous_image_budget <= 0 or historical.get("role") != "user":
                continue
            parts: list[dict[str, Any]] = []
            for record in historical.get("images") or []:
                filename = str(record.get("filename") or "")
                if not _valid_image_name(filename):
                    continue
                image_path = settings.chat_images_dir / conversation_id / filename
                if image_path.is_file():
                    parts.append(inline_image_part(image_path.read_bytes(), "image/jpeg"))
                    previous_image_budget -= 1
                if previous_image_budget <= 0:
                    break
            if parts:
                historical["_imageParts"] = parts
        try:
            proposal = await generate_chat_response(
                history=history,
                image_parts=image_parts,
                channel_data=channel_data,
                automation_config=store.get_automation_config(),
                settings=settings,
            )
        except ChatServiceError as exc:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

        metadata = {
            "suggestedAutomationConfig": proposal.suggested_automation_config.model_dump(
                mode="json", by_alias=True
            )
            if proposal.suggested_automation_config
            else None,
            "youtubeDataUsed": bool(channel_data),
            "warnings": warnings,
        }
        assistant_message = store.add_message(
            conversation_id, "model", proposal.reply, metadata=metadata
        )
        return ChatResponse(
            message_id=assistant_message["id"],
            reply=proposal.reply,
            suggested_automation_config=proposal.suggested_automation_config,
            youtube_data_used=bool(channel_data),
            warnings=warnings,
        )

    @router.get(
        "/v1/automation/config",
        response_model=AutomationConfig,
        response_model_by_alias=True,
        dependencies=[Depends(require_worker_or_session)],
    )
    async def get_automation_config() -> AutomationConfig:
        return store.get_automation_config()

    @router.put(
        "/v1/automation/config",
        response_model=AutomationConfig,
        response_model_by_alias=True,
        dependencies=[Depends(require_session)],
    )
    async def set_automation_config(config: AutomationConfig) -> AutomationConfig:
        if config.duration_seconds > settings.max_video_seconds:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"durationSeconds exceeds MAX_VIDEO_SECONDS={settings.max_video_seconds}",
            )
        return store.set_automation_config(config)

    return router


async def _save_image(
    upload: UploadFile, conversation_id: str, settings: Settings
) -> tuple[dict[str, Any], bytes]:
    maximum = settings.max_chat_image_mb * 1024 * 1024
    raw = await upload.read(maximum + 1)
    if len(raw) > maximum:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"each image must be <= {settings.max_chat_image_mb} MB",
        )
    try:
        with Image.open(io.BytesIO(raw)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise UnidentifiedImageError("unsupported image format")
            source.seek(0)
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=88, optimize=True)
            encoded = output.getvalue()
            width, height = image.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="JPEG, PNG, or WEBP image required",
        ) from exc

    filename = f"{secrets.token_hex(16)}.jpg"
    directory = settings.chat_images_dir / conversation_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_bytes(encoded)
    record = {
        "url": f"/v1/chat/images/{conversation_id}/{filename}",
        "filename": filename,
        "originalName": Path(upload.filename or "image").name[:200],
        "mimeType": "image/jpeg",
        "width": width,
        "height": height,
        "bytes": len(encoded),
    }
    return record, encoded


def _valid_uuidish(value: str) -> bool:
    return len(value) == 36 and all(char in "0123456789abcdef-" for char in value.lower())


def _valid_image_name(value: str) -> bool:
    return len(value) == 36 and value.endswith(".jpg") and value[:-4].isalnum()
