from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


Slug = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9._:-]+$", min_length=1, max_length=120)]


def _to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=_to_camel)


class RenderRequest(ApiModel):
    topic: str = Field(min_length=2, max_length=200)
    language: str = Field(default="ko-KR", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    duration_seconds: int = Field(default=45, ge=15, le=180)
    publish_at: datetime
    idempotency_key: Slug
    channel_key: Slug = "main"
    voice: str | None = Field(default=None, max_length=100)

    # Supplying title + narration bypasses Gemini and is useful for reviewed copy.
    title: str | None = Field(default=None, min_length=2, max_length=100)
    narration: str | None = Field(default=None, min_length=20, max_length=1200)
    description: str | None = Field(default=None, max_length=4000)
    tags: list[str] | None = Field(default=None, max_length=15)

    @field_validator("topic")
    @classmethod
    def clean_topic(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("publish_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("publishAt must include a timezone offset")
        return value

    @model_validator(mode="after")
    def require_complete_reviewed_copy(self) -> "RenderRequest":
        if (self.title is None) != (self.narration is None):
            raise ValueError("title and narration must be supplied together")
        return self


class ContentPlan(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    hook: str = Field(min_length=2, max_length=120)
    narration: str = Field(min_length=20, max_length=1200)
    description: str = Field(default="", max_length=4000)
    visual_search_query: str = Field(default="technology abstract", min_length=2, max_length=100)
    tags: list[str] = Field(default_factory=list, max_length=15)

    @field_validator("title", "hook", "narration", "description", "visual_search_query")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            cleaned = value.strip().lstrip("#")[:30]
            if cleaned and cleaned not in result:
                result.append(cleaned)
        return result[:15]


class RenderResponse(ApiModel):
    job_id: str
    status: str
    title: str
    description: str
    tags: list[str]
    publish_at: datetime
    video_url: str
    job_url: str
    duration_seconds: float
    already_uploaded: bool = False
    youtube_video_id: str | None = None
    attribution: str | None = None


class MarkUploadedRequest(ApiModel):
    youtube_video_id: str = Field(pattern=r"^[A-Za-z0-9_-]{11}$")


class LoginRequest(ApiModel):
    password: str = Field(min_length=1, max_length=500)


class ChannelProfile(ApiModel):
    own_channel_url: str = Field(default="", max_length=500)
    benchmark_channel_url: str = Field(default="", max_length=500)
    own_video_urls: list[str] = Field(default_factory=list, max_length=15)
    benchmark_video_urls: list[str] = Field(default_factory=list, max_length=15)

    @field_validator("own_channel_url", "benchmark_channel_url")
    @classmethod
    def clean_channel_url(cls, value: str) -> str:
        return value.strip()

    @field_validator("own_video_urls", "benchmark_video_urls")
    @classmethod
    def clean_video_urls(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value.strip()]
        if len(set(cleaned)) != len(cleaned):
            cleaned = list(dict.fromkeys(cleaned))
        return cleaned


class AutomationConfig(ApiModel):
    topic_pool: str = Field(
        default="AI 생산성 팁, 스마트폰 활용 팁, 유튜브 성장 기초",
        min_length=2,
        max_length=2000,
    )
    timezone: str = Field(default="Asia/Seoul", min_length=3, max_length=100)
    publish_hour: int = Field(default=18, ge=0, le=23)
    publish_minute: int = Field(default=0, ge=0, le=59)
    minimum_lead_minutes: int = Field(default=120, ge=30, le=1440)
    duration_seconds: int = Field(default=45, ge=15, le=180)
    language: str = Field(default="ko-KR", pattern=r"^[a-z]{2,3}(?:-[A-Z]{2})?$")
    voice: str = Field(default="ko-KR-SunHiNeural", min_length=2, max_length=100)
    channel_key: Slug = "main"

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("unknown IANA timezone") from exc
        return value

    @field_validator("topic_pool")
    @classmethod
    def has_topics(cls, value: str) -> str:
        topics = [topic.strip() for topic in value.split(",") if topic.strip()]
        if not topics:
            raise ValueError("topicPool must contain at least one topic")
        if len(topics) > 30:
            raise ValueError("topicPool supports at most 30 comma-separated topics")
        return ", ".join(dict.fromkeys(topics))


class ConversationCreate(ApiModel):
    title: str = Field(default="새 대화", min_length=1, max_length=100)
    profile: ChannelProfile = Field(default_factory=ChannelProfile)


class ConversationUpdate(ApiModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    profile: ChannelProfile | None = None


class ConversationSummary(ApiModel):
    id: str
    title: str
    profile: ChannelProfile
    created_at: datetime
    updated_at: datetime


class ChatProposal(ApiModel):
    reply: str = Field(min_length=1, max_length=12000)
    suggested_automation_config: AutomationConfig | None = None


class ChatResponse(ApiModel):
    message_id: str
    reply: str
    suggested_automation_config: AutomationConfig | None = None
    youtube_data_used: bool = False
    warnings: list[str] = Field(default_factory=list)
