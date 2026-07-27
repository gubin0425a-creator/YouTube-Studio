import asyncio
import hmac
import logging
import shutil
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .models import MarkUploadedRequest, RenderRequest, RenderResponse
from .pipeline import PipelineError, render_video
from .store import JobBusyError, JobStore
from .studio_api import build_studio_router
from .studio_store import StudioStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
settings = Settings()
settings.outputs_dir.mkdir(parents=True, exist_ok=True)
settings.chat_images_dir.mkdir(parents=True, exist_ok=True)
store = JobStore(settings.database_path)
studio_store = StudioStore(settings.studio_database_path)
render_lock = asyncio.Lock()
static_root = Path("/app/static")
if not (static_root / "index.html").is_file():
    static_root = Path(__file__).resolve().parents[2]
static_index = static_root / "index.html"


async def cleanup_loop() -> None:
    while True:
        try:
            for job_id in store.expired_job_ids(settings.video_retention_days):
                shutil.rmtree(settings.outputs_dir / job_id, ignore_errors=True)
                store.delete(job_id)
        except Exception:
            logger.exception("scheduled output cleanup failed")
        await asyncio.sleep(24 * 60 * 60)


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(
    title="YouTube Studio Video Worker",
    version="1.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
app.include_router(build_studio_router(settings, studio_store))
app.mount("/assets", StaticFiles(directory=static_root / "assets"), name="assets")


@app.get("/", include_in_schema=False)
async def studio_home() -> FileResponse:
    if not static_index.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="studio UI not installed")
    return FileResponse(static_index, media_type="text/html", headers={"Cache-Control": "no-cache"})


@app.get("/manifest.webmanifest", include_in_schema=False)
async def pwa_manifest() -> FileResponse:
    return FileResponse(
        static_root / "manifest.webmanifest",
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.get("/service-worker.js", include_in_schema=False)
async def pwa_service_worker() -> FileResponse:
    return FileResponse(
        static_root / "service-worker.js",
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"},
    )


def require_token(x_worker_token: str = Header(default="")) -> None:
    if not hmac.compare_digest(x_worker_token, settings.video_worker_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid worker token")


@app.get("/health")
async def health() -> dict[str, object]:
    return {
        "status": "ok",
        "geminiConfigured": bool(settings.gemini_api_key),
        "youtubeDataConfigured": bool(settings.youtube_data_api_key),
        "pexelsConfigured": bool(settings.pexels_api_key),
        "ttsProvider": settings.tts_provider,
    }


@app.post(
    "/v1/render",
    response_model=RenderResponse,
    response_model_by_alias=True,
    dependencies=[Depends(require_token)],
)
async def render(request: RenderRequest) -> RenderResponse:
    request_data = request.model_dump(mode="json", by_alias=True)
    key = f"{request.channel_key}:{request.idempotency_key}"
    try:
        claim = store.claim(key, request_data)
    except JobBusyError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if claim.cached_result is not None:
        return RenderResponse.model_validate(claim.cached_result)

    try:
        async with render_lock:
            result = await render_video(claim.job_id, request, settings)
        store.complete(claim.job_id, result)
        return RenderResponse.model_validate(result)
    except PipelineError as exc:
        store.fail(claim.job_id, str(exc))
        logger.error("render job %s failed: %s", claim.job_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)[:1000]) from exc
    except Exception as exc:
        store.fail(claim.job_id, f"unexpected {type(exc).__name__}")
        logger.exception("render job %s failed unexpectedly", claim.job_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="unexpected video render failure",
        ) from exc


@app.get("/v1/jobs/{job_id}", dependencies=[Depends(require_token)])
async def get_job(job_id: str) -> dict[str, object]:
    result = store.get(job_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return result


@app.post(
    "/v1/jobs/{job_id}/uploaded",
    response_model=RenderResponse,
    response_model_by_alias=True,
    dependencies=[Depends(require_token)],
)
async def mark_uploaded(job_id: str, body: MarkUploadedRequest) -> RenderResponse:
    try:
        result = store.mark_uploaded(job_id, body.youtube_video_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return RenderResponse.model_validate(result)


@app.get("/v1/files/{job_id}", dependencies=[Depends(require_token)])
async def download_video(job_id: str) -> FileResponse:
    job = store.get(job_id)
    if job is None or job["status"] not in {"completed", "uploaded"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="video not found")
    path = settings.outputs_dir / job_id / "video.mp4"
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="video file expired")
    return FileResponse(
        Path(path),
        media_type="video/mp4",
        filename=f"youtube-short-{job_id}.mp4",
        headers={"Cache-Control": "private, no-store"},
    )
