from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path("data/open-ore-mapper.db")

Connection = sqlite3.Connection


def _add_column_if_not_exists(conn: Connection, table: str, column: str, col_type: str) -> None:
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except sqlite3.OperationalError:
        pass


def init_db(path: Path | None = None) -> Connection:
    p = path or DB_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'emit',
            bbox_json TEXT,
            options_json TEXT,
            status TEXT NOT NULL DEFAULT 'queued',
            progress REAL NOT NULL DEFAULT 0.0,
            message TEXT,
            error TEXT,
            map_uuid TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS maps (
            uuid TEXT PRIMARY KEY,
            map_uuid TEXT,
            user_id TEXT,
            result_json TEXT,
            created_at TEXT,
            status TEXT,
            bbox_json TEXT,
            sensor TEXT
        )
    """
    )
    _add_column_if_not_exists(conn, "maps", "progress", "REAL DEFAULT 0.0")
    _add_column_if_not_exists(conn, "maps", "message", "TEXT")
    _add_column_if_not_exists(conn, "maps", "error", "TEXT")
    _add_column_if_not_exists(conn, "maps", "updated_at", "TEXT")
    _add_column_if_not_exists(conn, "maps", "source", "TEXT DEFAULT 'upload'")
    _add_column_if_not_exists(conn, "maps", "options_json", "TEXT")
    conn.commit()
    return conn


def get_connection(path: Path | None = None) -> Connection:
    return init_db(path)


# ── Job lifecycle ────────────────────────────────────────────────────


def create_bbox_job(
    conn: Connection, bbox: dict[str, float], options: dict[str, Any]
) -> str:
    job_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO jobs (id, source, bbox_json, options_json, status, progress, map_uuid, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'queued', 0.0, ?, ?, ?)""",
        (job_id, "emit", json.dumps(bbox), json.dumps(options), job_id, now, now),
    )
    conn.commit()
    return job_id


def update_job_progress(
    conn: Connection,
    job_id: str,
    status: str,
    *,
    progress: float | None = None,
    message: str | None = None,
) -> None:
    if progress is not None:
        if not (0.0 <= progress <= 100.0):
            raise ValueError(f"progress must be between 0 and 100, got {progress}")
        current = conn.execute(
            "SELECT progress FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if current is None:
            raise ValueError(f"job {job_id} not found")
        current_progress = current["progress"]
        if progress < current_progress:
            raise ValueError(
                f"progress cannot decrease from {current_progress} to {progress}"
            )

    now = datetime.now(timezone.utc).isoformat()
    sets = ["status = ?", "updated_at = ?"]
    params: list[Any] = [status, now]
    if progress is not None:
        sets.append("progress = ?")
        params.append(progress)
    if message is not None:
        sets.append("message = ?")
        params.append(message)
    params.append(job_id)
    conn.execute(
        f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", params
    )
    conn.commit()


def fail_job(
    conn: Connection, job_id: str, error: str, *, message: str | None = None
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE jobs SET status = 'failed', error = ?, message = ?, updated_at = ? WHERE id = ?",
        (error, message, now, job_id),
    )
    conn.commit()


def complete_job(conn: Connection, job_id: str, map_uuid: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE jobs SET status = 'complete', progress = 100.0, map_uuid = ?, updated_at = ? WHERE id = ?",
        (map_uuid, now, job_id),
    )
    conn.commit()


def fetch_job_public(conn: Connection, job_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    d = dict(row)
    return {
        "job_id": d["id"],
        "status": d["status"],
        "progress": d["progress"],
        "message": d.get("message"),
        "error": d.get("error"),
        "map_uuid": d.get("map_uuid"),
        "created_at": d["created_at"],
        "updated_at": d["updated_at"],
    }


def fetch_map_result(conn: Connection, map_uuid: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT status, result_json FROM maps WHERE uuid = ?", (map_uuid,)
    ).fetchone()
    if row is None:
        return None
    result_json = row["result_json"]
    if result_json is None:
        return None
    result: dict[str, Any] = json.loads(result_json)
    return result


def mark_nonterminal_jobs_interrupted(conn: Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """UPDATE jobs SET status = 'failed', error = ?, message = ?, updated_at = ?
           WHERE status NOT IN ('complete', 'failed')""",
        (
            "Server interrupted: process restarted",
            "Job was in progress when the server shut down",
            now,
        ),
    )
    conn.commit()


# ── Legacy functions (preserved for backward compatibility) ──────────


def create_job(
    conn: Connection, user_id: str | None = None, job_id: str | None = None
) -> str:
    if job_id is None:
        job_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO maps (uuid, user_id, status, created_at) VALUES (?, ?, ?, ?)",
        (job_id, user_id, "queued", datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return job_id


def update_job_status(
    conn: Connection, job_id: str, status: str, map_uuid: str | None = None
) -> None:
    if map_uuid is not None:
        conn.execute(
            "UPDATE maps SET status = ?, map_uuid = ? WHERE uuid = ?",
            (status, map_uuid, job_id),
        )
    else:
        conn.execute(
            "UPDATE maps SET status = ? WHERE uuid = ?", (status, job_id)
        )
    conn.commit()


def store_result(
    conn: Connection,
    map_uuid: str,
    result: dict[str, Any],
    user_id: str | None = None,
) -> None:
    existing = conn.execute(
        "SELECT 1 FROM maps WHERE uuid = ?", (map_uuid,)
    ).fetchone()
    now = datetime.now(timezone.utc).isoformat()
    if existing:
        conn.execute(
            "UPDATE maps SET result_json = ?, status = ?, created_at = ? WHERE uuid = ?",
            (json.dumps(result), "complete", now, map_uuid),
        )
    else:
        conn.execute(
            "INSERT INTO maps (uuid, user_id, result_json, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (map_uuid, user_id, json.dumps(result), "complete", now),
        )
    conn.commit()


def fetch_map(conn: Connection, map_uuid: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM maps WHERE uuid = ?", (map_uuid,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def fetch_job(conn: Connection, job_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM maps WHERE uuid = ?", (job_id,)
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_user_maps(
    conn: Connection, user_id: str, limit: int = 20
) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM maps WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    if d.get("result_json"):
        d["result"] = json.loads(d.pop("result_json"))
    return d
