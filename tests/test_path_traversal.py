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
def starter_cube_path() -> str:
    # data/starter_libraries/usgs_minerals.csv uses a 200-band grid from 450.0
    # to 2500.0 nm across 12 classes.
    cube = np.random.default_rng(7).random((5, 5, 200)).astype(np.float32)
    tmp = tempfile.NamedTemporaryFile(suffix=".tif", delete=False)
    with tifffile.TiffWriter(tmp.name) as tif:
        tif.write(cube)
    yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)


def _post_match(cube_path: str, options: dict) -> object:
    with open(cube_path, "rb") as f:
        return client.post(
            "/v1/match",
            files={"file": ("cube.tif", f, "image/tiff")},
            data={"options": json.dumps(options)},
        )


def test_spectral_library_relative_traversal_rejected(demo_cube_path: str) -> None:
    resp = _post_match(demo_cube_path, {"spectral_library": "../../etc/passwd"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"]["code"] == "BAD_REQUEST"
    # The attacker's path value must not be echoed back (no leak of resolution attempt)
    assert "../../etc/passwd" not in body["error"]["message"]


def test_spectral_library_absolute_path_rejected(demo_cube_path: str) -> None:
    resp = _post_match(demo_cube_path, {"spectral_library": "/absolute/path.csv"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


def test_spectral_library_backslash_traversal_rejected(demo_cube_path: str) -> None:
    resp = _post_match(demo_cube_path, {"spectral_library": "..\\..\\etc\\passwd"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


def test_spectral_library_dotdot_embedded_rejected(demo_cube_path: str) -> None:
    resp = _post_match(demo_cube_path, {"spectral_library": "USGS invalid/../x"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


def test_spectral_library_csv_suffix_rejected(demo_cube_path: str) -> None:
    resp = _post_match(demo_cube_path, {"spectral_library": "usgs_minerals.csv"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "BAD_REQUEST"


def test_spectral_library_starter_name_allowed(starter_cube_path: str) -> None:
    resp = _post_match(
        starter_cube_path,
        {
            "spectral_library": "usgs_minerals",
            "wavelengths": np.linspace(450.0, 2500.0, 200).tolist(),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert "Alunite" in body["classes"]
    assert "Muscovite" in body["classes"]
