import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from .models import ChannelProfile

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHANNEL_ID_RE = re.compile(r"^UC[A-Za-z0-9_-]{22}$")


class YouTubeDataError(RuntimeError):
    pass


class YouTubeDataClient:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def enrich_profile(self, profile: ChannelProfile) -> tuple[dict[str, Any], list[str]]:
        warnings: list[str] = []
        if not self.api_key:
            if profile.own_channel_url or profile.benchmark_channel_url:
                warnings.append("YOUTUBE_DATA_API_KEY가 없어 채널 실데이터를 불러오지 못했습니다.")
            return {}, warnings

        result: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=30) as client:
            if profile.own_channel_url:
                result["ownChannel"] = await self._channel_bundle(
                    client, profile.own_channel_url, profile.own_video_urls
                )
            if profile.benchmark_channel_url:
                result["benchmarkChannel"] = await self._channel_bundle(
                    client, profile.benchmark_channel_url, profile.benchmark_video_urls
                )
        return result, warnings

    async def _get(
        self, client: httpx.AsyncClient, path: str, params: dict[str, str]
    ) -> dict[str, Any]:
        params = {**params, "key": self.api_key}
        try:
            response = await client.get(
                f"https://www.googleapis.com/youtube/v3/{path}", params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            try:
                message = exc.response.json().get("error", {}).get("message")
            except ValueError:
                message = None
            raise YouTubeDataError(message or f"YouTube API returned {exc.response.status_code}") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise YouTubeDataError("YouTube Data API request failed") from exc

    async def _resolve_channel_id(self, client: httpx.AsyncClient, raw: str) -> str:
        value = raw.strip()
        if CHANNEL_ID_RE.fullmatch(value):
            return value

        handle: str | None = None
        query = value
        try:
            parsed = urlparse(value if "://" in value else f"https://{value}")
            segments = [segment for segment in parsed.path.split("/") if segment]
            if segments[:1] == ["channel"] and len(segments) > 1:
                if CHANNEL_ID_RE.fullmatch(segments[1]):
                    return segments[1]
            if segments and segments[0].startswith("@"):
                handle = segments[0]
            elif len(segments) > 1 and segments[0] in {"c", "user"}:
                handle = f"@{segments[1]}"
            query = segments[-1] if segments else value
        except ValueError:
            pass
        if value.startswith("@"):
            handle = value

        if handle:
            body = await self._get(client, "channels", {"part": "id", "forHandle": handle})
            items = body.get("items") or []
            if items:
                return items[0]["id"]

        # Custom/legacy URLs require a search fallback. It costs more quota, so
        # normal channel IDs and @handles above are strongly preferred.
        body = await self._get(
            client,
            "search",
            {"part": "snippet", "type": "channel", "maxResults": "1", "q": query},
        )
        items = body.get("items") or []
        if not items:
            raise YouTubeDataError(f"채널을 찾지 못했습니다: {raw}")
        return items[0]["snippet"]["channelId"]

    async def _channel_bundle(
        self, client: httpx.AsyncClient, channel_url: str, video_urls: list[str]
    ) -> dict[str, Any]:
        channel_id = await self._resolve_channel_id(client, channel_url)
        body = await self._get(
            client,
            "channels",
            {"part": "snippet,statistics,contentDetails", "id": channel_id},
        )
        items = body.get("items") or []
        if not items:
            raise YouTubeDataError(f"채널 데이터가 없습니다: {channel_url}")
        channel = items[0]
        stats = channel.get("statistics") or {}
        snippet = channel.get("snippet") or {}

        video_ids = [video_id for url in video_urls if (video_id := extract_video_id(url))]
        if video_urls and len(video_ids) != len(video_urls):
            raise YouTubeDataError("영상 주소 중 올바르지 않은 YouTube URL/ID가 있습니다.")
        if not video_ids:
            uploads = (
                channel.get("contentDetails", {})
                .get("relatedPlaylists", {})
                .get("uploads")
            )
            if uploads:
                playlist = await self._get(
                    client,
                    "playlistItems",
                    {
                        "part": "contentDetails",
                        "playlistId": uploads,
                        "maxResults": "15",
                    },
                )
                video_ids = [
                    item["contentDetails"]["videoId"] for item in playlist.get("items") or []
                ]

        videos: list[dict[str, Any]] = []
        if video_ids:
            video_body = await self._get(
                client,
                "videos",
                {
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids[:15]),
                },
            )
            by_id = {item["id"]: item for item in video_body.get("items") or []}
            for video_id in video_ids[:15]:
                item = by_id.get(video_id)
                if not item:
                    continue
                video_stats = item.get("statistics") or {}
                video_snippet = item.get("snippet") or {}
                videos.append(
                    {
                        "id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "title": video_snippet.get("title"),
                        "publishedAt": video_snippet.get("publishedAt"),
                        "duration": (item.get("contentDetails") or {}).get("duration"),
                        "views": _number(video_stats.get("viewCount")),
                        "likes": _number(video_stats.get("likeCount")),
                        "comments": _number(video_stats.get("commentCount")),
                    }
                )

        return {
            "id": channel_id,
            "url": f"https://www.youtube.com/channel/{channel_id}",
            "title": snippet.get("title"),
            "description": (snippet.get("description") or "")[:500],
            "publishedAt": snippet.get("publishedAt"),
            "subscribers": None
            if stats.get("hiddenSubscriberCount")
            else _number(stats.get("subscriberCount")),
            "totalViews": _number(stats.get("viewCount")),
            "videoCount": _number(stats.get("videoCount")),
            "videos": videos,
            "videoSelection": "provided" if video_urls else "latest",
        }


def extract_video_id(raw: str) -> str | None:
    value = raw.strip()
    if VIDEO_ID_RE.fullmatch(value):
        return value
    try:
        parsed = urlparse(value if "://" in value else f"https://{value}")
        host = parsed.hostname or ""
        if host.endswith("youtu.be"):
            candidate = parsed.path.strip("/").split("/")[0]
            return candidate if VIDEO_ID_RE.fullmatch(candidate) else None
        segments = [segment for segment in parsed.path.split("/") if segment]
        if len(segments) > 1 and segments[0] in {"shorts", "embed", "live"}:
            return segments[1] if VIDEO_ID_RE.fullmatch(segments[1]) else None
        candidate = parse_qs(parsed.query).get("v", [None])[0]
        return candidate if candidate and VIDEO_ID_RE.fullmatch(candidate) else None
    except ValueError:
        return None


def _number(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
