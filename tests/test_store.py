from __future__ import annotations

from pathlib import Path

from open_ore_mapper import store


def test_create_job_returns_job_id(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = store.init_db(db)
    job_id = store.create_job(conn)
    assert isinstance(job_id, str)
    assert len(job_id) > 0
    job = store.fetch_job(conn, job_id)
    assert job is not None
    assert job["status"] == "queued"


def test_update_job_status(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = store.init_db(db)
    job_id = store.create_job(conn)

    store.update_job_status(conn, job_id, "processing")
    job = store.fetch_job(conn, job_id)
    assert job is not None
    assert job["status"] == "processing"

    store.update_job_status(conn, job_id, "complete", map_uuid="abc123")
    job = store.fetch_job(conn, job_id)
    assert job is not None
    assert job["status"] == "complete"
    assert job.get("map_uuid") == "abc123"


def test_fetch_job_not_found_returns_none(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = store.init_db(db)
    assert store.fetch_job(conn, "nonexistent") is None


def test_store_result_and_retrieve(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = store.init_db(db)
    result = {"status": "success", "minerals": ["A", "B"]}
    store.store_result(conn, "map-123", result)
    fetched = store.fetch_map(conn, "map-123")
    assert fetched is not None
    assert fetched["result"]["status"] == "success"
    assert fetched["result"]["minerals"] == ["A", "B"]


def test_list_user_maps(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = store.init_db(db)
    for i in range(3):
        store.store_result(conn, f"map-{i}", {"idx": i}, user_id="user1")

    store.store_result(conn, "other", {"idx": 99}, user_id="user2")

    maps = store.list_user_maps(conn, "user1")
    assert len(maps) == 3

    maps2 = store.list_user_maps(conn, "user2")
    assert len(maps2) == 1


def test_db_creates_tables_on_first_use(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = store.init_db(db)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='maps'"
    ).fetchall()
    assert len(tables) == 1


def test_store_updates_existing_map(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    conn = store.init_db(db)
    store.store_result(conn, "abc", {"version": 1})
    store.store_result(conn, "abc", {"version": 2})
    fetched = store.fetch_map(conn, "abc")
    assert fetched is not None
    assert fetched["result"]["version"] == 2
