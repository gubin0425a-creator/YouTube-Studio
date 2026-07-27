import asyncio
import base64
import hashlib
import json
import logging
import math
import re
import shutil
from pathlib import Path
from typing import Any

import edge_tts
import httpx
from PIL import Image, ImageDraw, ImageFont

from .config import Settings
from .models import ContentPlan, RenderRequest

logger = logging.getLogger(__name__)
FONT_REGULAR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONTS_DIR = "/usr/share/fonts/opentype/noto"


class PipelineError(RuntimeError):
    pass


async def render_video(job_id: str, request: RenderRequest, settings: Settings) -> dict[str, Any]:
    job_dir = settings.outputs_dir / job_id
    if job_dir.exists():
        shutil.rmtree(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)

    plan = await build_content_plan(request, settings)
    audio_path = job_dir / "narration.mp3"
    await synthesize_speech(plan.narration, request, settings, audio_path)
    duration = await media_duration(audio_path)
    if duration < 3:
        raise PipelineError("TTS returned an unexpectedly short audio file")
    duration = await constrain_audio_duration(audio_path, duration, settings.max_video_seconds)

    captions_path = job_dir / "captions.srt"
    captions_path.write_text(build_srt(plan.narration, duration), encoding="utf-8")

    background_path, attribution = await fetch_pexels_video(
        plan.visual_search_query, settings, job_dir
    )
    artwork_path = job_dir / ("overlay.png" if background_path else "background.png")
    create_artwork(plan, artwork_path, transparent=background_path is not None)

    output_path = job_dir / "video.mp4"
    await compose_video(
        background_path=background_path,
        artwork_path=artwork_path,
        audio_path=audio_path,
        captions_path=captions_path,
        output_path=output_path,
        duration=duration,
    )
    final_duration = await media_duration(output_path)

    description = plan.description.strip()
    if "#Shorts" not in description:
        description = f"{description}\n\n#Shorts".strip()
    if attribution:
        description += f"\n\n영상 소스: {attribution}"

    tags = list(dict.fromkeys([*plan.tags, "Shorts"]))[:15]
    result = {
        "jobId": job_id,
        "status": "completed",
        "title": plan.title[:100],
        "description": description[:4000],
        "tags": tags,
        "publishAt": request.publish_at.isoformat(),
        "videoUrl": f"{settings.video_worker_base_url}/v1/files/{job_id}",
        "jobUrl": f"{settings.video_worker_base_url}/v1/jobs/{job_id}",
        "durationSeconds": round(final_duration, 3),
        "alreadyUploaded": False,
        "youtubeVideoId": None,
        "attribution": attribution,
    }
    (job_dir / "metadata.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


async def build_content_plan(request: RenderRequest, settings: Settings) -> ContentPlan:
    if request.title and request.narration:
        return ContentPlan(
            title=request.title,
            hook=request.title,
            narration=request.narration,
            description=request.description or f"{request.topic} 핵심 내용을 짧게 정리했습니다.",
            visual_search_query=request.topic,
            tags=request.tags or [request.topic, "쇼츠"],
        )

    if not settings.gemini_api_key:
        raise PipelineError(
            "GEMINI_API_KEY is not configured. A real Gemini key starts with 'AIza'."
        )

    target_chars = max(100, min(500, int(request.duration_seconds * 5.2)))
    prompt = f"""
주제: {request.topic}
언어: {request.language}
목표 길이: 약 {request.duration_seconds}초, 내레이션 약 {target_chars}자

세로형 YouTube Shorts용 독창적인 콘텐츠 기획을 작성하세요.
- 첫 문장에서 시선을 끌고, 핵심 3가지를 짧고 자연스럽게 전달하세요.
- 확인할 수 없는 수치, 최신 뉴스인 척하는 표현, 과장된 효능을 만들지 마세요.
- 저작권 문구나 다른 영상 대본을 복제하지 말고 광고 친화적으로 작성하세요.
- 제목은 100자 미만, 내레이션은 한 사람이 그대로 읽을 수 있는 문장만 작성하세요.
- visual_search_query만 Pexels 검색에 적합한 짧은 영어 구문으로 작성하세요.
- description에는 핵심 요약을 넣고 해시태그는 tags에 분리하세요.
""".strip()
    schema = {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "hook": {"type": "STRING"},
            "narration": {"type": "STRING"},
            "description": {"type": "STRING"},
            "visual_search_query": {"type": "STRING"},
            "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
        },
        "required": [
            "title",
            "hook",
            "narration",
            "description",
            "visual_search_query",
            "tags",
        ],
    }
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 1600,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent"
    )
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                url,
                headers={"x-goog-api-key": settings.gemini_api_key},
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
        candidates = body.get("candidates") or []
        if not candidates:
            raise PipelineError("Gemini returned no content (possibly blocked by safety filters)")
        text = candidates[0]["content"]["parts"][0]["text"]
        return ContentPlan.model_validate_json(text)
    except PipelineError:
        raise
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("Gemini content generation failed: %s", type(exc).__name__)
        raise PipelineError("Gemini content generation failed; check the key, model, and quota") from exc


async def synthesize_speech(
    text: str, request: RenderRequest, settings: Settings, output_path: Path
) -> None:
    if settings.tts_provider == "google":
        await synthesize_google(text, request, settings, output_path)
        return
    voice = request.voice or settings.tts_voice
    try:
        communication = edge_tts.Communicate(text=text, voice=voice, rate="+5%")
        await communication.save(str(output_path))
    except Exception as exc:  # edge-tts raises several transport-specific types
        logger.warning("Edge TTS failed: %s", type(exc).__name__)
        raise PipelineError("Edge TTS failed; verify TTS_VOICE or switch TTS_PROVIDER") from exc


async def synthesize_google(
    text: str, request: RenderRequest, settings: Settings, output_path: Path
) -> None:
    if not settings.google_tts_api_key:
        raise PipelineError("GOOGLE_TTS_API_KEY is required when TTS_PROVIDER=google")
    # The workflow's `voice` field is an Edge voice by default. Google uses its
    # own explicitly configured voice to avoid sending an incompatible name.
    voice_name = settings.google_tts_voice
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": request.language, "name": voice_name},
        "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.05},
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://texttospeech.googleapis.com/v1/text:synthesize",
                headers={"x-goog-api-key": settings.google_tts_api_key},
                json=payload,
            )
            response.raise_for_status()
            output_path.write_bytes(base64.b64decode(response.json()["audioContent"]))
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        logger.warning("Google Cloud TTS failed: %s", type(exc).__name__)
        raise PipelineError("Google Cloud TTS failed; check API access, billing, and voice") from exc


async def fetch_pexels_video(
    query: str, settings: Settings, job_dir: Path
) -> tuple[Path | None, str | None]:
    if not settings.pexels_api_key:
        return None, None
    try:
        async with httpx.AsyncClient(timeout=90, follow_redirects=True) as client:
            response = await client.get(
                "https://api.pexels.com/videos/search",
                headers={"Authorization": settings.pexels_api_key},
                params={
                    "query": query,
                    "orientation": "portrait",
                    "size": "medium",
                    "per_page": 5,
                },
            )
            response.raise_for_status()
            videos = response.json().get("videos") or []
            if not videos:
                return None, None
            video = videos[0]
            choices = [
                item
                for item in video.get("video_files", [])
                if item.get("file_type") == "video/mp4"
                and (item.get("height") or 0) > (item.get("width") or 0)
                and 540 <= (item.get("width") or 0) <= 1440
            ]
            if not choices:
                return None, None
            selected = min(choices, key=lambda item: abs((item.get("width") or 0) - 1080))
            background_path = job_dir / "pexels-background.mp4"
            async with client.stream("GET", selected["link"]) as download:
                download.raise_for_status()
                size = 0
                with background_path.open("wb") as output:
                    async for chunk in download.aiter_bytes():
                        size += len(chunk)
                        if size > 250 * 1024 * 1024:
                            raise PipelineError("Pexels footage exceeded the 250 MB safety limit")
                        output.write(chunk)
            creator = video.get("user") or {}
            name = creator.get("name") or "Pexels creator"
            page = video.get("url") or creator.get("url") or "https://www.pexels.com"
            return background_path, f"{name} / Pexels ({page})"
    except PipelineError:
        raise
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        # Stock footage is an enhancement. Rendering must remain available without it.
        logger.warning("Pexels unavailable; using generated background: %s", type(exc).__name__)
        return None, None


def create_artwork(plan: ContentPlan, output_path: Path, transparent: bool) -> None:
    width, height = 1080, 1920
    seed = int(hashlib.sha256(plan.title.encode("utf-8")).hexdigest()[:8], 16)
    if transparent:
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    else:
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        c1 = (10 + seed % 20, 16, 35 + seed % 35)
        c2 = (100 + seed % 90, 12, 65 + seed % 50)
        for y in range(height):
            ratio = y / (height - 1)
            color = tuple(int(a * (1 - ratio) + b * ratio) for a, b in zip(c1, c2))
            for x in range(width):
                pixels[x, y] = color

    draw = ImageDraw.Draw(image, "RGBA")
    accent = (255, 0, 72, 220)
    if not transparent:
        draw.ellipse((-300, -250, 650, 700), fill=(255, 0, 72, 38))
        draw.ellipse((650, 1150, 1450, 2050), fill=(38, 99, 235, 55))
        for index in range(7):
            x = (seed * (index + 3)) % width
            y = 420 + ((seed // (index + 1)) % 900)
            radius = 8 + (index * 3)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(255, 255, 255, 28))
    else:
        draw.rectangle((0, 0, width, height), fill=(0, 0, 0, 55))
        draw.rounded_rectangle((65, 105, 1015, 530), radius=42, fill=(5, 8, 18, 185))

    draw.rounded_rectangle((70, 120, 270, 184), radius=28, fill=accent)
    badge_font = ImageFont.truetype(FONT_BOLD, 30)
    draw.text((105, 133), "60초 핵심", font=badge_font, fill=(255, 255, 255, 255))

    title_font = _fit_font(plan.title, 82, 50, max_width=900, max_lines=4)
    title = _wrap_text(plan.title, max_chars=14, max_lines=4)
    title_y = 245 if transparent else 340
    draw.multiline_text(
        (90, title_y),
        title,
        font=title_font,
        fill=(255, 255, 255, 255),
        spacing=22,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 130),
    )
    if not transparent:
        hook_font = ImageFont.truetype(FONT_REGULAR, 39)
        hook = _wrap_text(plan.hook, max_chars=21, max_lines=3)
        draw.rounded_rectangle((75, 1110, 1005, 1395), radius=34, fill=(0, 0, 0, 90))
        draw.multiline_text(
            (115, 1160), hook, font=hook_font, fill=(235, 240, 255, 235), spacing=15
        )

    draw.rounded_rectangle((70, 1760, 450, 1832), radius=30, fill=(5, 8, 18, 170))
    footer_font = ImageFont.truetype(FONT_BOLD, 29)
    draw.text((105, 1778), "YouTube Studio+", font=footer_font, fill=(255, 255, 255, 225))
    image.save(output_path)


def _fit_font(text: str, start: int, minimum: int, max_width: int, max_lines: int) -> ImageFont.FreeTypeFont:
    scratch = Image.new("RGB", (10, 10))
    draw = ImageDraw.Draw(scratch)
    for size in range(start, minimum - 1, -2):
        font = ImageFont.truetype(FONT_BOLD, size)
        wrapped = _wrap_text(text, max_chars=max(8, int(max_width / (size * 0.95))), max_lines=max_lines)
        box = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=20)
        if box[2] - box[0] <= max_width:
            return font
    return ImageFont.truetype(FONT_BOLD, minimum)


def _wrap_text(text: str, max_chars: int, max_lines: int) -> str:
    cleaned = " ".join(text.split())
    lines: list[str] = []
    current = ""
    for word in cleaned.split(" "):
        if len(current) + len(word) + (1 if current else 0) <= max_chars:
            current = f"{current} {word}".strip()
            continue
        if current:
            lines.append(current)
        while len(word) > max_chars:
            lines.append(word[:max_chars])
            word = word[max_chars:]
        current = word
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][: max(1, max_chars - 1)].rstrip() + "…"
    return "\n".join(lines)


def build_srt(narration: str, duration: float) -> str:
    sentences = [
        part.strip()
        for part in re.split(r"(?<=[.!?。！？])\s+|\n+", narration)
        if part.strip()
    ]
    chunks: list[str] = []
    for sentence in sentences or [narration]:
        words = sentence.split()
        current = ""
        for word in words:
            if len(word) > 34:
                if current:
                    chunks.append(current)
                    current = ""
                while len(word) > 34:
                    chunks.append(word[:34])
                    word = word[34:]
            if not word:
                continue
            if len(current) + len(word) + (1 if current else 0) <= 34:
                current = f"{current} {word}".strip()
            else:
                if current:
                    chunks.append(current)
                current = word
        if current:
            chunks.append(current)
    if not chunks:
        chunks = [narration]

    weights = [max(4, len(re.sub(r"\s", "", chunk))) for chunk in chunks]
    total_weight = sum(weights)
    cursor = 0.15
    usable = max(1.0, duration - 0.3)
    output: list[str] = []
    for index, (chunk, weight) in enumerate(zip(chunks, weights), start=1):
        span = usable * weight / total_weight
        end = min(duration, cursor + span)
        output.extend(
            [
                str(index),
                f"{_srt_timestamp(cursor)} --> {_srt_timestamp(end)}",
                _wrap_text(chunk, max_chars=18, max_lines=2),
                "",
            ]
        )
        cursor = end
    return "\n".join(output)


def _srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


async def constrain_audio_duration(path: Path, duration: float, maximum: int) -> float:
    if duration <= maximum:
        return duration
    speed = min(2.0, duration / maximum)
    converted = path.with_name("narration-fitted.mp3")
    await run_command(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-filter:a",
            f"atempo={speed:.5f}",
            "-t",
            str(maximum),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(converted),
        ],
        "audio duration normalization",
    )
    converted.replace(path)
    return await media_duration(path)


async def compose_video(
    *,
    background_path: Path | None,
    artwork_path: Path,
    audio_path: Path,
    captions_path: Path,
    output_path: Path,
    duration: float,
) -> None:
    subtitle_filter = (
        f"subtitles=filename='{captions_path}':fontsdir='{FONTS_DIR}':"
        "force_style='FontName=Noto Sans CJK KR,FontSize=19,Bold=1,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BackColour=&H66000000,BorderStyle=3,Outline=3,Shadow=0,"
        "Alignment=2,MarginV=185'"
    )
    if background_path:
        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-stream_loop",
            "-1",
            "-i",
            str(background_path),
            "-i",
            str(audio_path),
            "-loop",
            "1",
            "-i",
            str(artwork_path),
            "-filter_complex",
            "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,setsar=1,eq=brightness=-0.10:saturation=0.88[base];"
            "[2:v]format=rgba[overlay];[base][overlay]overlay=0:0[decorated];"
            f"[decorated]{subtitle_filter}[video]",
        ]
    else:
        command = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(artwork_path),
            "-i",
            str(audio_path),
            "-filter_complex",
            "[0:v]scale=1080:1920,setsar=1,"
            "zoompan=z='min(zoom+0.00035,1.045)':d=1:s=1080x1920:fps=30[base];"
            f"[base]{subtitle_filter}[video]",
        ]
    command.extend(
        [
            "-map",
            "[video]",
            "-map",
            "1:a:0",
            "-t",
            f"{duration + 0.15:.3f}",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "21",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-map_metadata",
            "-1",
            str(output_path),
        ]
    )
    await run_command(command, "video rendering")


async def media_duration(path: Path) -> float:
    process = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise PipelineError(f"ffprobe failed: {stderr.decode(errors='replace')[-400:]}")
    try:
        value = float(stdout.decode().strip())
    except ValueError as exc:
        raise PipelineError("ffprobe returned an invalid duration") from exc
    if not math.isfinite(value):
        raise PipelineError("media duration is not finite")
    return value


async def run_command(command: list[str], label: str) -> None:
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode != 0:
        detail = stderr.decode(errors="replace")[-1200:]
        raise PipelineError(f"{label} failed: {detail}")
