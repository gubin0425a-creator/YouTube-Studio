import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import AutomationConfig, ChannelProfile


class StudioStore:
    """Persistent chats, channel profiles, and the n8n automation configuration."""

    def __init__(self, database_path: Path) -> None:
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path = database_path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user', 'model')),
                    text TEXT NOT NULL,
                    images_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS messages_conversation_created_idx
                ON messages(conversation_id, created_at);

                CREATE TABLE IF NOT EXISTS studio_settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            existing = connection.execute(
                "SELECT 1 FROM studio_settings WHERE key = 'automation'"
            ).fetchone()
            if existing is None:
                default = AutomationConfig().model_dump(mode="json", by_alias=True)
                connection.execute(
                    "INSERT INTO studio_settings(key, value_json, updated_at) VALUES('automation', ?, ?)",
                    (json.dumps(default, ensure_ascii=False), datetime.now(UTC).isoformat()),
                )

    def create_conversation(self, title: str, profile: ChannelProfile) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        conversation_id = str(uuid.uuid4())
        profile_json = json.dumps(profile.model_dump(mode="json", by_alias=True), ensure_ascii=False)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO conversations(id, title, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, title.strip(), profile_json, now, now),
            )
        return self.get_conversation(conversation_id)  # type: ignore[return-value]

    def list_conversations(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        return [self._conversation(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        return self._conversation(row) if row else None

    def update_conversation(
        self,
        conversation_id: str,
        *,
        title: str | None = None,
        profile: ChannelProfile | None = None,
    ) -> dict[str, Any] | None:
        current = self.get_conversation(conversation_id)
        if current is None:
            return None
        next_title = title.strip() if title is not None else current["title"]
        next_profile = (
            profile.model_dump(mode="json", by_alias=True)
            if profile is not None
            else current["profile"]
        )
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE conversations SET title = ?, profile_json = ?, updated_at = ? WHERE id = ?
                """,
                (
                    next_title,
                    json.dumps(next_profile, ensure_ascii=False),
                    datetime.now(UTC).isoformat(),
                    conversation_id,
                ),
            )
        return self.get_conversation(conversation_id)

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM conversations WHERE id = ?", (conversation_id,)
            )
        return cursor.rowcount > 0

    def add_message(
        self,
        conversation_id: str,
        role: str,
        text: str,
        *,
        images: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
            if exists is None:
                raise KeyError("conversation not found")
            connection.execute(
                """
                INSERT INTO messages(
                    id, conversation_id, role, text, images_json, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    conversation_id,
                    role,
                    text,
                    json.dumps(images or [], ensure_ascii=False),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id)
            )
        return {
            "id": message_id,
            "conversationId": conversation_id,
            "role": role,
            "text": text,
            "images": images or [],
            "metadata": metadata or {},
            "createdAt": now,
        }

    def get_messages(self, conversation_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        sql = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at DESC"
        params: list[Any] = [conversation_id]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        rows = list(reversed(rows))
        return [
            {
                "id": row["id"],
                "conversationId": row["conversation_id"],
                "role": row["role"],
                "text": row["text"],
                "images": json.loads(row["images_json"]),
                "metadata": json.loads(row["metadata_json"]),
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    def get_automation_config(self) -> AutomationConfig:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value_json FROM studio_settings WHERE key = 'automation'"
            ).fetchone()
        if row is None:
            return AutomationConfig()
        return AutomationConfig.model_validate_json(row["value_json"])

    def set_automation_config(self, config: AutomationConfig) -> AutomationConfig:
        value = json.dumps(config.model_dump(mode="json", by_alias=True), ensure_ascii=False)
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO studio_settings(key, value_json, updated_at)
                VALUES('automation', ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json,
                                               updated_at = excluded.updated_at
                """,
                (value, now),
            )
        return config

    @staticmethod
    def _conversation(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "title": row["title"],
            "profile": json.loads(row["profile_json"]),
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }
