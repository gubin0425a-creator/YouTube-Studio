from pathlib import Path

from app.models import AutomationConfig, ChannelProfile
from app.studio_store import StudioStore


def test_chat_history_is_persistent_and_not_artificially_capped(tmp_path: Path) -> None:
    database = tmp_path / "studio.sqlite3"
    store = StudioStore(database)
    conversation = store.create_conversation("장기 대화", ChannelProfile())
    for index in range(205):
        store.add_message(conversation["id"], "user", f"메시지 {index}")

    reopened = StudioStore(database)
    assert len(reopened.get_messages(conversation["id"])) == 205
    assert len(reopened.get_messages(conversation["id"], limit=40)) == 40


def test_automation_config_round_trip(tmp_path: Path) -> None:
    store = StudioStore(tmp_path / "studio.sqlite3")
    config = AutomationConfig(publishHour=21, topicPool="AI, 자동화")
    store.set_automation_config(config)
    loaded = store.get_automation_config()
    assert loaded.publish_hour == 21
    assert loaded.topic_pool == "AI, 자동화"
