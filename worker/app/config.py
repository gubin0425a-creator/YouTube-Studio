from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, case_sensitive=False)

    video_worker_token: str = Field(min_length=32)
    video_worker_base_url: str = "http://video-worker:8000"
    data_dir: Path = Path("/data")
    video_retention_days: int = Field(default=7, ge=1, le=90)
    max_video_seconds: int = Field(default=60, ge=15, le=180)

    studio_host: str = "studio.example.com"
    studio_access_password: str = Field(min_length=16)
    studio_session_secret: str = Field(min_length=32)
    studio_session_days: int = Field(default=30, ge=1, le=365)
    studio_secure_cookie: bool = True
    max_chat_image_mb: int = Field(default=10, ge=1, le=25)
    max_chat_images: int = Field(default=5, ge=1, le=10)
    chat_history_messages: int = Field(default=40, ge=4, le=200)

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    youtube_data_api_key: str = ""
    pexels_api_key: str = ""

    tts_provider: str = "edge"
    tts_voice: str = "ko-KR-SunHiNeural"
    google_tts_api_key: str = ""
    google_tts_voice: str = "ko-KR-Neural2-A"

    @field_validator("video_worker_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    @field_validator("tts_provider")
    @classmethod
    def validate_tts_provider(cls, value: str) -> str:
        normalized = value.lower().strip()
        if normalized not in {"edge", "google"}:
            raise ValueError("TTS_PROVIDER must be 'edge' or 'google'")
        return normalized

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "jobs.sqlite3"

    @property
    def studio_database_path(self) -> Path:
        return self.data_dir / "studio.sqlite3"

    @property
    def chat_images_dir(self) -> Path:
        return self.data_dir / "chat-images"

    @property
    def studio_origin(self) -> str:
        return f"https://{self.studio_host}"
