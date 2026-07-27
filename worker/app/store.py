import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class JobBusyError(RuntimeError):
    pass


@dataclass(frozen=True)
class JobClaim:
    job_id: str
    cached_result: dict[str, Any] | None


class JobStore:
    """Small durable idempotency store for render/upload hand-off state."""

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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    request_json TEXT NOT NULL,
                    result_json TEXT,
                    error TEXT,
                    youtube_video_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS jobs_updated_at_idx ON jobs(updated_at)"
            )

    def claim(self, idempotency_key: str, request: dict[str, Any]) -> JobClaim:
        now = datetime.now(UTC)
        stale_before = now - timedelta(hours=2)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            if row is None:
                job_id = str(uuid.uuid4())
                connection.execute(
                    """
                    INSERT INTO jobs (
                        id, idempotency_key, status, request_json, created_at, updated_at
                    ) VALUES (?, ?, 'processing', ?, ?, ?)
                    """,
                    (
                        job_id,
                        idempotency_key,
                        json.dumps(request, ensure_ascii=False),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                return JobClaim(job_id=job_id, cached_result=None)

            if row["status"] in {"completed", "uploaded"} and row["result_json"]:
                result = json.loads(row["result_json"])
                if row["status"] == "uploaded":
                    result["alreadyUploaded"] = True
                    result["youtubeVideoId"] = row["youtube_video_id"]
                    result["status"] = "uploaded"
                return JobClaim(job_id=row["id"], cached_result=result)

            updated_at = datetime.fromisoformat(row["updated_at"])
            if row["status"] == "processing" and updated_at > stale_before:
                raise JobBusyError(f"job {row['id']} is already rendering")

            connection.execute(
                """
                UPDATE jobs
                SET status = 'processing', request_json = ?, error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(request, ensure_ascii=False), now.isoformat(), row["id"]),
            )
            return JobClaim(job_id=row["id"], cached_result=None)

    def complete(self, job_id: str, result: dict[str, Any]) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs
                SET status = 'completed', result_json = ?, error = NULL, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(result, ensure_ascii=False), now, job_id),
            )

    def fail(self, job_id: str, error: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE jobs SET status = 'failed', error = ?, updated_at = ? WHERE id = ?
                """,
                (error[:1000], datetime.now(UTC).isoformat(), job_id),
            )

    def mark_uploaded(self, job_id: str, youtube_video_id: str) -> dict[str, Any] | None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if row is None or row["result_json"] is None:
                return None
            if row["youtube_video_id"] and row["youtube_video_id"] != youtube_video_id:
                raise ValueError("job is already linked to a different YouTube video")
            connection.execute(
                """
                UPDATE jobs
                SET status = 'uploaded', youtube_video_id = ?, updated_at = ?
                WHERE id = ?
                """,
                (youtube_video_id, now, job_id),
            )
            result = json.loads(row["result_json"])
            result.update(
                status="uploaded",
                alreadyUploaded=True,
                youtubeVideoId=youtube_video_id,
            )
            return result

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        result = json.loads(row["result_json"]) if row["result_json"] else {}
        return {
            "jobId": row["id"],
            "status": row["status"],
            "error": row["error"],
            "youtubeVideoId": row["youtube_video_id"],
            "result": result,
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def expired_job_ids(self, retention_days: int) -> list[str]:
        cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id FROM jobs
                WHERE updated_at < ? AND status IN ('completed', 'uploaded', 'failed')
                """,
                (cutoff,),
            ).fetchall()
        return [row["id"] for row in rows]

    def delete(self, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
