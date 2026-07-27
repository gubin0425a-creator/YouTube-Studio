import pytest
from pydantic import ValidationError

from app.models import ChannelProfile
from app.youtube_data import extract_video_id


def test_extract_video_id_supports_watch_shorts_and_short_links() -> None:
    assert extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ?t=2") == "dQw4w9WgXcQ"


def test_profile_allows_optional_videos_but_caps_each_side_at_15() -> None:
    profile = ChannelProfile(
        ownChannelUrl="https://youtube.com/@mine",
        ownVideoUrls=[f"https://example.com/{index}" for index in range(15)],
    )
    assert len(profile.own_video_urls) == 15
    with pytest.raises(ValidationError):
        ChannelProfile(ownVideoUrls=[str(index) for index in range(16)])
