from app.pipeline import _srt_timestamp, _wrap_text, build_srt


def test_srt_covers_narration_and_has_valid_timestamps() -> None:
    srt = build_srt(
        "첫 번째 핵심입니다. 두 번째 핵심은 자동화가 서버에서 실행된다는 점입니다.",
        12.0,
    )
    assert "00:00:00,150 -->" in srt
    assert "첫 번째 핵심입니다." in srt
    assert "두 번째 핵심은" in srt


def test_srt_splits_long_unspaced_korean_without_dropping_text() -> None:
    narration = "가" * 80
    srt = build_srt(narration, 10.0)
    assert srt.count("가") == 80


def test_srt_timestamp_rolls_over() -> None:
    assert _srt_timestamp(61.234) == "00:01:01,234"


def test_wrap_text_limits_lines() -> None:
    wrapped = _wrap_text("아주 긴 제목을 여러 줄로 안전하게 줄여서 표시합니다", 8, 2)
    assert len(wrapped.splitlines()) == 2
    assert wrapped.endswith("…")
