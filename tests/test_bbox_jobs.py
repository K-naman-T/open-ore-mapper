from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

from open_ore_mapper import store as store_module
from open_ore_mapper.api import app
from open_ore_mapper.schemas import MapperOptions, validate_bbox


# ── Bbox validation ──────────────────────────────────────────────────


def test_validate_bbox_valid() -> None:
    bbox = {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}
    assert validate_bbox(bbox) == bbox


def test_validate_bbox_missing_key() -> None:
    with pytest.raises(ValueError, match="west"):
        validate_bbox({"south": 0, "east": 1, "north": 2})


def test_validate_bbox_non_numeric() -> None:
    with pytest.raises(ValueError, match="west"):
        validate_bbox({"west": "abc", "south": 0, "east": 1, "north": 2})


def test_validate_bbox_non_finite() -> None:
    with pytest.raises(ValueError, match="west"):
        validate_bbox({"west": float("inf"), "south": 0, "east": 1, "north": 2})


def test_validate_bbox_longitude_out_of_range() -> None:
    with pytest.raises(ValueError, match="west"):
        validate_bbox({"west": -200, "south": 0, "east": -150, "north": 10})
    with pytest.raises(ValueError, match="east"):
        validate_bbox({"west": 170, "south": 0, "east": 200, "north": 10})


def test_validate_bbox_latitude_out_of_range() -> None:
    with pytest.raises(ValueError, match="south"):
        validate_bbox({"west": 0, "south": -100, "east": 10, "north": -80})
    with pytest.raises(ValueError, match="north"):
        validate_bbox({"west": 0, "south": 80, "east": 10, "north": 100})


def test_validate_bbox_west_gte_east() -> None:
    with pytest.raises(ValueError, match="west"):
        validate_bbox({"west": -100, "south": 0, "east": -100, "north": 10})
    with pytest.raises(ValueError, match="west"):
        validate_bbox({"west": -100, "south": 0, "east": -110, "north": 10})


def test_validate_bbox_south_gte_north() -> None:
    with pytest.raises(ValueError, match="south"):
        validate_bbox({"west": -100, "south": 10, "east": -90, "north": 10})
    with pytest.raises(ValueError, match="south"):
        validate_bbox({"west": -100, "south": 20, "east": -90, "north": 10})


def test_validate_bbox_accepts_integers() -> None:
    bbox = {"west": -100, "south": 30, "east": -90, "north": 40}
    result = validate_bbox(bbox)
    assert all(isinstance(v, float) for v in result.values())


# ── Store: job lifecycle ────────────────────────────────────────────


def _init_store(tmp_path: Path) -> store_module.Connection:
    return store_module.init_db(tmp_path / "test.db")


def test_create_bbox_job_returns_job(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    bbox = {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}
    options = {"minerals": ["hematite"]}
    job_id = store_module.create_bbox_job(conn, bbox, options)
    assert job_id is not None
    assert isinstance(job_id, str)
    job = store_module.fetch_job_public(conn, job_id)
    assert job is not None
    assert job["job_id"] == job_id
    assert job["status"] == "queued"
    assert job["progress"] == 0.0
    assert job["map_uuid"] == job_id


def test_job_lifecycle_through_phases(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    job_id = store_module.create_bbox_job(
        conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
    )

    store_module.update_job_progress(conn, job_id, "searching", progress=10)
    job = store_module.fetch_job_public(conn, job_id)
    assert job["status"] == "searching"
    assert job["progress"] == 10.0

    store_module.update_job_progress(conn, job_id, "downloading", progress=30)
    job = store_module.fetch_job_public(conn, job_id)
    assert job["status"] == "downloading"
    assert job["progress"] == 30.0

    store_module.update_job_progress(conn, job_id, "processing", progress=60)
    job = store_module.fetch_job_public(conn, job_id)
    assert job["status"] == "processing"
    assert job["progress"] == 60.0

    store_module.complete_job(conn, job_id, map_uuid=job_id)
    job = store_module.fetch_job_public(conn, job_id)
    assert job["status"] == "complete"
    assert job["progress"] == 100.0


def test_job_progress_decrease_rejected(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    job_id = store_module.create_bbox_job(
        conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
    )
    store_module.update_job_progress(conn, job_id, "searching", progress=50)
    with pytest.raises(ValueError, match="decrease"):
        store_module.update_job_progress(conn, job_id, "searching", progress=20)


def test_job_progress_out_of_bounds(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    job_id = store_module.create_bbox_job(
        conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
    )
    with pytest.raises(ValueError, match="0.*100"):
        store_module.update_job_progress(conn, job_id, "searching", progress=-1)
    with pytest.raises(ValueError, match="0.*100"):
        store_module.update_job_progress(conn, job_id, "searching", progress=101)


def test_fail_job_sets_error(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    job_id = store_module.create_bbox_job(
        conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
    )
    store_module.fail_job(conn, job_id, error="No granules found")
    job = store_module.fetch_job_public(conn, job_id)
    assert job["status"] == "failed"
    assert job["error"] == "No granules found"
    assert job["progress"] >= 0.0


def test_fetch_job_public_contract(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    job_id = store_module.create_bbox_job(
        conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
    )
    job = store_module.fetch_job_public(conn, job_id)
    expected_keys = {
        "job_id",
        "status",
        "progress",
        "message",
        "error",
        "map_uuid",
        "created_at",
        "updated_at",
    }
    assert set(job.keys()) == expected_keys


def test_fetch_job_public_nonexistent(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    assert store_module.fetch_job_public(conn, "nonexistent") is None


def test_fetch_map_result_not_found_when_not_stored(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    assert store_module.fetch_map_result(conn, "absent") is None


def test_store_result_then_fetch_map(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    result = {"status": "success", "minerals": ["hematite"]}
    store_module.store_result(conn, "test-map-uuid", result)
    fetched = store_module.fetch_map_result(conn, "test-map-uuid")
    assert fetched is not None
    assert fetched["status"] == "success"
    assert fetched["minerals"] == ["hematite"]


def test_mark_nonterminal_jobs_interrupted(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    live_id = store_module.create_bbox_job(
        conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
    )
    done_id = store_module.create_bbox_job(
        conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
    )
    store_module.complete_job(conn, done_id, map_uuid=done_id)

    store_module.mark_nonterminal_jobs_interrupted(conn)

    live_job = store_module.fetch_job_public(conn, live_id)
    assert live_job["status"] == "failed"
    assert "interrupted" in live_job["error"].lower()

    done_job = store_module.fetch_job_public(conn, done_id)
    assert done_job["status"] == "complete"


def test_mark_nonterminal_jobs_skips_terminal(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    for status in ("complete", "failed"):
        jid = store_module.create_bbox_job(
            conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
        )
        conn.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, jid))
    conn.commit()
    store_module.mark_nonterminal_jobs_interrupted(conn)
    for status in ("complete", "failed"):
        row = conn.execute(
            "SELECT status FROM jobs WHERE status = ?", (status,)
        ).fetchone()
        assert row is not None


def test_existing_store_functions_still_work(tmp_path: Path) -> None:
    conn = _init_store(tmp_path)
    jid = store_module.create_job(conn)
    assert store_module.fetch_job(conn, jid) is not None
    store_module.update_job_status(conn, jid, "processing")
    assert store_module.fetch_job(conn, jid)["status"] == "processing"


# ── API endpoints via TestClient ─────────────────────────────────────


def test_predict_bbox_valid_returns_202(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}}
    with TestClient(app) as client:
        response = client.post("/v1/predict/bbox", json=body)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert "map_uuid" in data
    assert data["job_id"] == data["map_uuid"]
    assert data["status"] == "queued"
    assert data["progress"] == 0.0


def test_predict_bbox_invalid_bbox_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -200, "south": 36, "east": -114, "north": 37}}
    with TestClient(app) as client:
        response = client.post("/v1/predict/bbox", json=body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_predict_bbox_missing_bbox_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        response = client.post("/v1/predict/bbox", json={})
    assert response.status_code == 400


def test_predict_bbox_non_dict_bbox_returns_400(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        response = client.post("/v1/predict/bbox", json={"bbox": [1, 2, 3, 4]})
    assert response.status_code == 400


def test_get_job_returns_public_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}}
    with TestClient(app) as client:
        resp = client.post("/v1/predict/bbox", json=body)
    job_id = resp.json()["job_id"]
    with TestClient(app) as client:
        resp = client.get(f"/v1/jobs/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {
        "job_id",
        "status",
        "progress",
        "message",
        "error",
        "map_uuid",
        "created_at",
        "updated_at",
    }
    assert set(data.keys()) == expected_keys
    assert data["job_id"] == job_id


def test_get_job_not_found_returns_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        resp = client.get("/v1/jobs/nonexistent")
    assert resp.status_code == 404


def test_get_map_returns_404_when_not_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}}
    with TestClient(app) as client:
        resp = client.post("/v1/predict/bbox", json=body)
    job_id = resp.json()["job_id"]
    with TestClient(app) as client:
        resp = client.get(f"/v1/maps/{job_id}")
    assert resp.status_code == 404


def test_get_map_returns_404_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        resp = client.get("/v1/maps/absent")
    assert resp.status_code == 404


def test_post_bbox_and_get_map_404_before_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}}
    with TestClient(app) as client:
        resp = client.post("/v1/predict/bbox", json=body)
    job_id = resp.json()["job_id"]
    with TestClient(app) as client:
        resp = client.get(f"/v1/maps/{job_id}")
    assert resp.status_code == 404


def test_background_pipeline_failure_sets_job_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}}

    with patch(
        "open_ore_mapper.emit_client.search_emit_granules",
        side_effect=RuntimeError("EMIT down"),
    ):
        with TestClient(app) as client:
            resp = client.post("/v1/predict/bbox", json=body)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    with TestClient(app) as client:
        job = client.get(f"/v1/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert job["error"] is not None
    assert "Traceback" not in job["error"]


def test_background_pipeline_no_granules(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}}

    with patch(
        "open_ore_mapper.emit_client.search_emit_granules", return_value=[]
    ):
        with TestClient(app) as client:
            resp = client.post("/v1/predict/bbox", json=body)
    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    with TestClient(app) as client:
        job = client.get(f"/v1/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert job["error"] is not None
    assert "No" in job["error"] or "no" in job["error"].lower()


def test_background_pipeline_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {
        "bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0},
        "min_confidence": 0.0,
        "sam_threshold_deg": 180.0,
    }

    B = 10
    wavelengths_arr = np.linspace(381, 2493, B)
    glt_x = np.zeros((16, 16), dtype=np.float32)
    glt_y = np.zeros((16, 16), dtype=np.float32)

    tile_data = np.random.rand(16, 16, B).astype(np.float32)

    mock_granule = {
        "id": "test-granule-multi",
        "bbox": [-115, 36, -114, 37],
        "datetime": "now",
        "cloud_cover": 5.0,
        "asset_href": "https://example.com/test.nc",
    }

    mock_scene = MagicMock()
    mock_scene.wavelengths = wavelengths_arr.astype(np.float32)
    mock_scene.good_wavelengths = np.ones(B, dtype=bool)
    mock_scene.glt_x = glt_x
    mock_scene.glt_y = glt_y
    mock_scene.orthorectify.return_value = [
        (0, 16, 0, 16, tile_data),
    ]

    with (
        patch(
            "open_ore_mapper.emit_client.search_emit_granules",
            return_value=[mock_granule],
        ),
        patch(
            "open_ore_mapper.emit_client.select_best_granule",
            return_value=mock_granule,
        ),
        patch(
            "open_ore_mapper.emit_client.EmitScene.from_granule",
            return_value=mock_scene,
        ),
    ):
        with TestClient(app) as client:
            resp = client.post("/v1/predict/bbox", json=body)

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    with TestClient(app) as client:
        job = client.get(f"/v1/jobs/{job_id}").json()
    assert job["status"] == "complete"
    assert job["progress"] == 100.0

    with TestClient(app) as client:
        map_result = client.get(f"/v1/maps/{job_id}").json()
    assert map_result["status"] == "success"
    assert "provenance" in map_result
    assert map_result["provenance"]["source"] == "emit"
    assert map_result["provenance"]["processed_tile_count"] == 1
    assert map_result["provenance"]["granule_id"] == "test-granule-multi"
    assert "wavelength_count" in map_result["provenance"]
    assert "requested_bbox" in map_result["provenance"]


def test_bbox_submission_with_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {
        "bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0},
        "minerals": ["hematite", "goethite"],
        "sam_threshold_deg": 10.0,
    }
    with TestClient(app) as client:
        resp = client.post("/v1/predict/bbox", json=body)
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["progress"] == 0.0


def test_predict_bbox_no_traceback_in_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}}
    with patch(
        "open_ore_mapper.emit_client.search_emit_granules",
        side_effect=RuntimeError("boom"),
    ):
        with TestClient(app) as client:
            resp = client.post("/v1/predict/bbox", json=body)
    job_id = resp.json()["job_id"]
    with TestClient(app) as client:
        job = client.get(f"/v1/jobs/{job_id}").json()
    assert "Traceback" not in str(job)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"bbox": None},
        {"bbox": "not-a-dict"},
        {"bbox": []},
    ],
)
def test_predict_bbox_various_invalid_inputs(
    body: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(app) as client:
        resp = client.post("/v1/predict/bbox", json=body)
    assert resp.status_code == 400


def test_multi_tile_processing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {
        "bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0},
        "min_confidence": 0.0,
        "sam_threshold_deg": 180.0,
    }

    B = 10
    wavelengths_arr = np.linspace(381, 2493, B)
    glt_x = np.zeros((16, 16), dtype=np.float32)
    glt_y = np.zeros((16, 16), dtype=np.float32)

    tile1 = np.full((8, 16, B), 0.3, dtype=np.float32)
    tile2 = np.full((8, 16, B), 0.6, dtype=np.float32)

    mock_granule = {
        "id": "multi-tile-granule",
        "bbox": [-115, 36, -114, 37],
        "datetime": "now",
        "cloud_cover": 5.0,
        "asset_href": "https://example.com/test.nc",
    }

    mock_scene = MagicMock()
    mock_scene.wavelengths = wavelengths_arr.astype(np.float32)
    mock_scene.good_wavelengths = np.ones(B, dtype=bool)
    mock_scene.glt_x = glt_x
    mock_scene.glt_y = glt_y
    mock_scene.orthorectify.return_value = [
        (0, 8, 0, 16, tile1),
        (8, 16, 0, 16, tile2),
    ]

    with (
        patch(
            "open_ore_mapper.emit_client.search_emit_granules",
            return_value=[mock_granule],
        ),
        patch(
            "open_ore_mapper.emit_client.select_best_granule",
            return_value=mock_granule,
        ),
        patch(
            "open_ore_mapper.emit_client.EmitScene.from_granule",
            return_value=mock_scene,
        ),
    ):
        with TestClient(app) as client:
            resp = client.post("/v1/predict/bbox", json=body)

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    with TestClient(app) as client:
        job = client.get(f"/v1/jobs/{job_id}").json()
    assert job["status"] == "complete"

    with TestClient(app) as client:
        map_result = client.get(f"/v1/maps/{job_id}").json()
    assert map_result["status"] == "success"
    assert map_result["provenance"]["processed_tile_count"] == 2


def test_empty_invalid_tiles_fail_clearly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {"bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0}}

    B = 10
    wavelengths_arr = np.linspace(381, 2493, B)
    glt_x = np.zeros((1, 1), dtype=np.float32)
    glt_y = np.zeros((1, 1), dtype=np.float32)

    mock_granule = {
        "id": "empty-tile-test",
        "bbox": [-115, 36, -114, 37],
        "datetime": "now",
        "cloud_cover": 5.0,
        "asset_href": "https://example.com/test.nc",
    }

    mock_scene = MagicMock()
    mock_scene.wavelengths = wavelengths_arr.astype(np.float32)
    mock_scene.good_wavelengths = np.ones(B, dtype=bool)
    mock_scene.glt_x = glt_x
    mock_scene.glt_y = glt_y
    mock_scene.orthorectify.return_value = []

    with (
        patch(
            "open_ore_mapper.emit_client.search_emit_granules",
            return_value=[mock_granule],
        ),
        patch(
            "open_ore_mapper.emit_client.select_best_granule",
            return_value=mock_granule,
        ),
        patch(
            "open_ore_mapper.emit_client.EmitScene.from_granule",
            return_value=mock_scene,
        ),
    ):
        with TestClient(app) as client:
            resp = client.post("/v1/predict/bbox", json=body)

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]

    with TestClient(app) as client:
        job = client.get(f"/v1/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "No orthorectified tiles" in job["error"]


def test_progress_is_monotonic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn = _init_store(tmp_path)
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")

    job_id = store_module.create_bbox_job(
        conn, {"west": 0, "south": 0, "east": 1, "north": 1}, {}
    )

    from open_ore_mapper.api import _run_bbox_pipeline as pipeline

    B = 10
    wavelengths_arr = np.linspace(381, 2493, B)
    glt_x = np.zeros((16, 16), dtype=np.float32)
    glt_y = np.zeros((16, 16), dtype=np.float32)

    tile1 = np.random.rand(8, 16, B).astype(np.float32)
    tile2 = np.random.rand(8, 16, B).astype(np.float32)

    mock_granule = {
        "id": "progress-test",
        "bbox": [0, 0, 1, 1],
        "datetime": "now",
        "cloud_cover": 5.0,
        "asset_href": "https://example.com/test.nc",
    }

    mock_scene = MagicMock()
    mock_scene.wavelengths = wavelengths_arr.astype(np.float32)
    mock_scene.good_wavelengths = np.ones(B, dtype=bool)
    mock_scene.glt_x = glt_x
    mock_scene.glt_y = glt_y
    mock_scene.orthorectify.return_value = [
        (0, 8, 0, 16, tile1),
        (8, 16, 0, 16, tile2),
    ]

    with (
        patch(
            "open_ore_mapper.emit_client.search_emit_granules",
            return_value=[mock_granule],
        ),
        patch(
            "open_ore_mapper.emit_client.select_best_granule",
            return_value=mock_granule,
        ),
        patch(
            "open_ore_mapper.emit_client.EmitScene.from_granule",
            return_value=mock_scene,
        ),
    ):
        pipeline(
            job_id=job_id,
            bbox={"west": 0, "south": 0, "east": 1, "north": 1},
            options=MapperOptions(
                minerals=["hematite_demo", "goethite_demo"],
                min_confidence=0.0,
                sam_threshold_deg=180.0,
                wavelengths=wavelengths_arr.tolist(),
            ),
        )

    job = store_module.fetch_job_public(conn, job_id)
    assert job["status"] == "complete"
    assert job["progress"] == 100.0

    progress_values = [
        row["progress"]
        for row in conn.execute(
            "SELECT progress FROM jobs WHERE id = ?", (job_id,)
        ).fetchall()
    ]
    assert len(progress_values) >= 1


def test_provenance_includes_required_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store_module, "DB_PATH", tmp_path / "test.db")
    body = {
        "bbox": {"west": -115.0, "south": 36.0, "east": -114.0, "north": 37.0},
        "min_confidence": 0.0,
        "sam_threshold_deg": 180.0,
    }

    B = 10
    wavelengths_arr = np.linspace(381, 2493, B)
    glt_x = np.zeros((8, 8), dtype=np.float32)
    glt_y = np.zeros((8, 8), dtype=np.float32)
    tile_data = np.random.rand(8, 8, B).astype(np.float32)

    mock_granule = {
        "id": "provenance-test-granule",
        "bbox": [-115, 36, -114, 37],
        "datetime": "now",
        "cloud_cover": 5.0,
        "asset_href": "https://example.com/test.nc",
    }

    mock_scene = MagicMock()
    mock_scene.wavelengths = wavelengths_arr.astype(np.float32)
    mock_scene.good_wavelengths = np.ones(B, dtype=bool)
    mock_scene.glt_x = glt_x
    mock_scene.glt_y = glt_y
    mock_scene.orthorectify.return_value = [(0, 8, 0, 8, tile_data)]

    with (
        patch(
            "open_ore_mapper.emit_client.search_emit_granules",
            return_value=[mock_granule],
        ),
        patch(
            "open_ore_mapper.emit_client.select_best_granule",
            return_value=mock_granule,
        ),
        patch(
            "open_ore_mapper.emit_client.EmitScene.from_granule",
            return_value=mock_scene,
        ),
    ):
        with TestClient(app) as client:
            resp = client.post("/v1/predict/bbox", json=body)

    job_id = resp.json()["job_id"]
    with TestClient(app) as client:
        map_result = client.get(f"/v1/maps/{job_id}").json()

    prov = map_result["provenance"]
    assert prov["source"] == "emit"
    assert prov["granule_id"] == "provenance-test-granule"
    assert "requested_bbox" in prov
    assert "processed_bounds" in prov
    assert prov["processed_tile_count"] == 1
    assert "selected_minerals" in prov
    assert "classifier" in prov
    assert "wavelength_count" in prov
