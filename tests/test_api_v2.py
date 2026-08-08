from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient

from spectral_matching.api import app

client = TestClient(app)


@pytest.fixture
def demo_cube_path() -> str:
    cube = np.random.default_rng(42).random((5, 5, 3)).astype(np.float32)
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    with tifffile.TiffWriter(tmp.name) as tif:
        tif.write(cube)
    yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def demo_library_csv_bytes() -> bytes:
    rows = [
        "name,wavelength,reflectance",
        "class_a,450,0.42",
        "class_a,550,0.30",
        "class_a,650,0.34",
        "class_b,450,0.38",
        "class_b,550,0.44",
        "class_b,650,0.35",
    ]
    return "\n".join(rows).encode("utf-8")


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_match_upload_cube_only(demo_cube_path: str) -> None:
    options = json.dumps({
        "spectral_library": "usgs_minerals",
        "wavelengths": [450.0, 550.0, 650.0],
    })
    with open(demo_cube_path, "rb") as f:
        resp = client.post(
            "/v1/match",
            files={"file": ("cube.tif", f, "image/tiff")},
            data={"options": options},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "map_uuid" in body
    assert len(body["classes"]) > 0


def test_match_upload_cube_and_library(demo_cube_path: str, demo_library_csv_bytes: bytes) -> None:
    options = json.dumps({
        "wavelengths": [450.0, 550.0, 650.0],
    })
    with open(demo_cube_path, "rb") as f:
        resp = client.post(
            "/v1/match",
            files={
                "file": ("cube.tif", f, "image/tiff"),
                "library": ("lib.csv", demo_library_csv_bytes, "text/csv"),
            },
            data={"options": options},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "map_uuid" in body
    assert len(body["classes"]) == 2


def test_qc_raster(demo_cube_path: str) -> None:
    options = json.dumps({"wavelengths": [450.0, 550.0, 650.0]})
    with open(demo_cube_path, "rb") as f:
        resp = client.post(
            "/v1/qc/raster",
            files={"file": ("cube.tif", f, "image/tiff")},
            data={"options": options},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "warnings" in body
    assert "retained_band_indices" in body


def test_match_empty_file(demo_cube_path: str) -> None:
    resp = client.post(
        "/v1/match",
        files={"file": ("empty.tif", b"", "image/tiff")},
        data={"options": "{}"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body
    assert "BAD_REQUEST" in body["error"]["code"]


def test_match_missing_classes(demo_cube_path: str) -> None:
    options = json.dumps({"wavelengths": [450.0, 550.0, 650.0], "classes": []})
    with open(demo_cube_path, "rb") as f:
        resp = client.post(
            "/v1/match",
            files={"file": ("cube.tif", f, "image/tiff")},
            data={"options": options},
        )
    assert resp.status_code == 400
    body = resp.json()
    assert "error" in body
