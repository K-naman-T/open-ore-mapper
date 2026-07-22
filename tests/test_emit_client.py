from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from numpy.typing import NDArray

from open_ore_mapper.emit_client import (
    EmitScene,
    _extract_bbox,
    _extract_cloud_cover,
    _extract_datetime,
    extract_bbox,
    search_emit_granules,
    select_best_granule,
)
from open_ore_mapper.emit_client import (
    EmitAuthError,
    EmitHTTPError,
    EmitTimeoutError,
)


def _make_mock_granule(
    umm: dict | None = None,
    data_links: list[str] | None = None,
    granule_ur: str = "test-granule-1",
) -> MagicMock:
    g = MagicMock()
    g.umm = umm or {"GranuleUR": granule_ur}
    g.data_links.return_value = data_links or [
        "https://example.com/EMIT_L2A_RFL_001.nc",
    ]
    return g


def test_search_emit_by_bbox_returns_real_metadata() -> None:
    with (
        patch("earthaccess.login"),
        patch("earthaccess.search_data") as mock_search,
    ):
        mock_granule = _make_mock_granule(
            umm={
                "GranuleUR": "EMIT_L2A_RFL_001",
                "SpatialExtent": {
                    "HorizontalSpatialDomain": {
                        "Geometry": {
                            "BoundingRectangles": [
                                {
                                    "WestBoundingCoordinate": -115.5,
                                    "NorthBoundingCoordinate": 37.5,
                                    "EastBoundingCoordinate": -114.5,
                                    "SouthBoundingCoordinate": 36.5,
                                }
                            ]
                        }
                    }
                },
                "TemporalExtent": {
                    "RangeDateTime": {
                        "BeginningDateTime": "2023-01-15T10:30:00Z"
                    }
                },
                "DataQuality": {"CloudCover": 8.5},
            },
            granule_ur="EMIT_L2A_RFL_001",
        )
        mock_search.return_value = [mock_granule]

        granules = search_emit_granules(
            bbox=(-115.5, 36.5, -114.5, 37.5), cloud_max=100.0
        )

    assert len(granules) == 1
    g = granules[0]
    assert g["id"] == "EMIT_L2A_RFL_001"
    assert g["bbox"] == [-115.5, 36.5, -114.5, 37.5]
    assert g["datetime"] == "2023-01-15T10:30:00Z"
    assert g["cloud_cover"] == 8.5
    assert g["asset_href"].endswith(".nc")


def test_search_emit_excludes_mask_and_rfluncert() -> None:
    with (
        patch("earthaccess.login"),
        patch("earthaccess.search_data") as mock_search,
    ):
        mock_granule = _make_mock_granule(
            data_links=[
                "https://example.com/EMIT_L2A_RFL_001.nc",
                "https://example.com/EMIT_L2A_MASK_001.nc",
                "https://example.com/EMIT_L2A_RFLUNCERT_001.nc",
            ],
        )
        mock_search.return_value = [mock_granule]

        granules = search_emit_granules(bbox=(-115.5, 36.5, -114.5, 37.5))

    assert len(granules) == 1
    assert granules[0]["asset_href"].endswith("RFL_001.nc")
    assert "MASK" not in granules[0]["asset_href"]
    assert "RFLUNCERT" not in granules[0]["asset_href"]


def test_extract_cloud_cover_returns_none_when_missing() -> None:
    g = MagicMock()
    g.umm = {"GranuleUR": "test"}
    assert _extract_cloud_cover(g) is None


def test_extract_cloud_cover_returns_float() -> None:
    g = MagicMock()
    g.umm = {"DataQuality": {"CloudCover": 12.5}}
    assert _extract_cloud_cover(g) == 12.5


def test_extract_bbox_returns_defaults_when_missing() -> None:
    g = MagicMock()
    g.umm = {"GranuleUR": "test"}
    assert _extract_bbox(g) == [0, 0, 0, 0]


def test_extract_datetime_returns_empty_when_missing() -> None:
    g = MagicMock()
    g.umm = {"GranuleUR": "test"}
    assert _extract_datetime(g) == ""


def test_search_emit_no_results_returns_empty_list() -> None:
    with (
        patch("earthaccess.login"),
        patch("earthaccess.search_data") as mock_search,
    ):
        mock_search.return_value = []
        granules = search_emit_granules(bbox=(-115.5, 36.5, -114.5, 37.5))

    assert granules == []


def test_extract_bbox_from_granule() -> None:
    granule = {"bbox": [-115.5, 36.5, -114.5, 37.5]}
    result = extract_bbox(granule)
    assert result == (-115.5, 36.5, -114.5, 37.5)


def test_select_best_granule_ranks_by_cloud_cover() -> None:
    granules: list[dict] = [
        {"id": "a", "cloud_cover": 90.0, "asset_href": "https://example.com/a.nc"},
        {"id": "b", "cloud_cover": 5.0, "asset_href": "https://example.com/b.nc"},
        {"id": "c", "cloud_cover": 40.0, "asset_href": "https://example.com/c.nc"},
    ]
    best = select_best_granule(granules, cloud_max=100.0)
    assert best is not None
    assert best["id"] == "b"


def test_select_best_granule_none_when_all_exceed_cloud_max() -> None:
    granules: list[dict] = [
        {"id": "a", "cloud_cover": 20.0, "asset_href": "https://example.com/a.nc"},
    ]
    assert select_best_granule(granules, cloud_max=10.0) is None


def test_select_best_granule_skips_missing_href() -> None:
    granules: list[dict] = [
        {"id": "a", "cloud_cover": 5.0, "asset_href": ""},
        {"id": "b", "cloud_cover": 10.0, "asset_href": "https://example.com/b.nc"},
    ]
    best = select_best_granule(granules, cloud_max=100.0)
    assert best is not None
    assert best["id"] == "b"


def test_select_best_granule_unknown_cloud_after_acceptable() -> None:
    granules: list[dict] = [
        {"id": "a", "cloud_cover": 5.0, "asset_href": "https://example.com/a.nc"},
        {"id": "b", "cloud_cover": None, "asset_href": "https://example.com/b.nc"},
        {"id": "c", "cloud_cover": 50.0, "asset_href": "https://example.com/c.nc"},
    ]
    best = select_best_granule(granules, cloud_max=10.0)
    assert best is not None
    assert best["id"] == "a"

    no_known: list[dict] = [
        {"id": "x", "cloud_cover": None, "asset_href": "https://example.com/x.nc"},
        {"id": "y", "cloud_cover": 50.0, "asset_href": "https://example.com/y.nc"},
    ]
    best = select_best_granule(no_known, cloud_max=10.0)
    assert best is not None
    assert best["id"] == "x"

    only_bad: list[dict] = [
        {"id": "z", "cloud_cover": 50.0, "asset_href": "https://example.com/z.nc"},
        {"id": "w", "cloud_cover": 80.0, "asset_href": "https://example.com/w.nc"},
    ]
    assert select_best_granule(only_bad, cloud_max=10.0) is None


def test_select_best_granule_unknown_cloud_ranked_after_known() -> None:
    only_unknown: list[dict] = [
        {"id": "u1", "cloud_cover": None, "asset_href": "https://example.com/u1.nc"},
        {"id": "u2", "cloud_cover": None, "asset_href": "https://example.com/u2.nc"},
    ]
    best = select_best_granule(only_unknown, cloud_max=10.0)
    assert best is not None
    assert best["id"] == "u1"


def test_emit_scene_from_granule_streams_download() -> None:
    H, W, B = 10, 10, 20
    wavelengths = np.linspace(381, 2493, B, dtype=np.float32)
    reflect_data = np.random.rand(H, W, B).astype(np.float32)
    glt_x = np.arange(W, dtype=np.float32)[None, :].repeat(H, axis=0)
    glt_y = np.arange(H, dtype=np.float32)[:, None].repeat(W, axis=1)
    good_wavelengths = np.ones(B, dtype=np.uint8)

    nc_path = Path(tempfile.mktemp(suffix=".nc"))
    try:
        import netCDF4

        with netCDF4.Dataset(str(nc_path), "w") as ds:
            ds.createDimension("downtrack", H)
            ds.createDimension("crosstrack", W)
            ds.createDimension("bands", B)
            ds.createVariable(
                "reflectance", "f4", ("downtrack", "crosstrack", "bands")
            )[:] = reflect_data
            loc = ds.createGroup("location")
            loc.createVariable("ortho_x", "f4", ("downtrack", "crosstrack"))[:] = glt_x
            loc.createVariable("ortho_y", "f4", ("downtrack", "crosstrack"))[:] = glt_y
            sbp = ds.createGroup("sensor_band_parameters")
            sbp.createVariable("wavelengths", "f4", ("bands",))[:] = wavelengths
            sbp.createVariable("good_wavelengths", "u1", ("bands",))[:] = good_wavelengths

        nc_bytes = nc_path.read_bytes()
    finally:
        nc_path.unlink(missing_ok=True)

    with patch("earthaccess.login") as mock_login:
        mock_auth = MagicMock()
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [nc_bytes]
        mock_resp.status_code = 200
        mock_session.get.return_value = mock_resp
        mock_auth.get_session.return_value = mock_session
        mock_login.return_value = mock_auth

        granule = {
            "id": "test",
            "bbox": [-115.5, 36.5, -114.5, 37.5],
            "datetime": "2023-01-01T12:00:00Z",
            "cloud_cover": 5.0,
            "asset_href": "https://data.example.com/test.nc",
        }
        scene = EmitScene.from_granule(granule)

    assert scene.reflectance.shape == (H, W, B)
    assert scene.reflectance.dtype == np.float32
    assert len(scene.wavelengths) == B
    assert scene.good_wavelengths is not None
    assert scene.good_wavelengths.sum() == B


def test_emit_scene_from_granule_raises_auth_error() -> None:
    with patch("earthaccess.login") as mock_login:
        mock_auth = MagicMock()
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_session.get.return_value = mock_resp
        mock_auth.get_session.return_value = mock_session
        mock_login.return_value = mock_auth

        granule = {
            "id": "test",
            "bbox": [0, 0, 1, 1],
            "datetime": "",
            "cloud_cover": None,
            "asset_href": "https://data.example.com/test.nc",
        }
        import pytest

        with pytest.raises(EmitAuthError):
            EmitScene.from_granule(granule)


def test_emit_scene_from_granule_raises_http_error() -> None:
    with patch("earthaccess.login") as mock_login:
        mock_auth = MagicMock()
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
        mock_session.get.return_value = mock_resp
        mock_auth.get_session.return_value = mock_session
        mock_login.return_value = mock_auth

        granule = {
            "id": "test",
            "bbox": [0, 0, 1, 1],
            "datetime": "",
            "cloud_cover": None,
            "asset_href": "https://data.example.com/test.nc",
        }
        import pytest

        with pytest.raises(EmitHTTPError):
            EmitScene.from_granule(granule)


def test_emit_scene_from_granule_raises_timeout_error() -> None:
    with patch("earthaccess.login") as mock_login:
        mock_auth = MagicMock()
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection timeout")
        mock_auth.get_session.return_value = mock_session
        mock_login.return_value = mock_auth

        granule = {
            "id": "test",
            "bbox": [0, 0, 1, 1],
            "datetime": "",
            "cloud_cover": None,
            "asset_href": "https://data.example.com/test.nc",
        }
        import pytest

        with pytest.raises(EmitTimeoutError):
            EmitScene.from_granule(granule)


def test_emit_scene_preserves_wavelengths_and_good_bands() -> None:
    H, W, B = 6, 6, 10
    np.random.seed(42)
    reflect_data = np.random.rand(H, W, B).astype(np.float32)
    wavelengths = np.linspace(400, 2400, B, dtype=np.float32)
    glt_x = np.arange(W, dtype=np.float32)[None, :].repeat(H, axis=0)
    glt_y = np.arange(H, dtype=np.float32)[:, None].repeat(W, axis=1)
    good_wavelengths: NDArray[np.bool_] = np.array(
        [True, True, True, True, True, False, True, True, False, True], dtype=bool
    )

    scene = EmitScene(reflect_data, wavelengths, glt_x, glt_y, good_wavelengths)
    assert np.array_equal(scene.wavelengths, wavelengths)
    assert scene.good_wavelengths is not None
    assert scene.good_wavelengths.sum() == 8
    indices = scene.get_effective_band_indices()
    assert indices == [0, 1, 2, 3, 4, 6, 7, 9]


def test_emit_scene_orthorectify_yields_tiles() -> None:
    H, W, B = 10, 10, 20
    np.random.seed(1)
    reflectance = np.random.rand(H, W, B).astype(np.float32)
    wavelengths = np.linspace(381, 2493, B, dtype=np.float32)

    glt_x = np.arange(W, dtype=np.float32)[None, :].repeat(H, axis=0)
    glt_y = np.arange(H, dtype=np.float32)[:, None].repeat(W, axis=1)

    scene = EmitScene(reflectance, wavelengths, glt_x, glt_y)
    tiles = list(scene.orthorectify(tile_size=8))

    assert len(tiles) == 4
    for r0, r1, c0, c1, tile_data in tiles:
        assert tile_data.shape == (r1 - r0, c1 - c0, B)
        assert tile_data.dtype == np.float32

    r0, r1, c0, c1, tile_data = tiles[0]
    np.testing.assert_array_equal(tile_data, reflectance[r0:r1, c0:c1, :])


def test_emit_scene_handles_missing_good_wavelengths() -> None:
    H, W, B = 10, 10, 20
    np.random.seed(1)
    reflectance = np.random.rand(H, W, B).astype(np.float32)
    wavelengths = np.linspace(381, 2493, B, dtype=np.float32)
    glt_x = np.arange(W, dtype=np.float32)[None, :].repeat(H, axis=0)
    glt_y = np.arange(H, dtype=np.float32)[:, None].repeat(W, axis=1)

    scene = EmitScene(reflectance, wavelengths, glt_x, glt_y, good_wavelengths=None)
    indices = scene.get_effective_band_indices()
    assert indices == list(range(B))


def test_emit_scene_applies_good_wavelengths_mask() -> None:
    H, W, B = 10, 10, 20
    np.random.seed(1)
    reflectance = np.random.rand(H, W, B).astype(np.float32)
    wavelengths = np.linspace(381, 2493, B, dtype=np.float32)
    glt_x = np.arange(W, dtype=np.float32)[None, :].repeat(H, axis=0)
    glt_y = np.arange(H, dtype=np.float32)[:, None].repeat(W, axis=1)

    good_wavelengths: NDArray[np.bool_] = np.array(
        [True] * 18 + [False] * 2, dtype=bool
    )
    scene = EmitScene(reflectance, wavelengths, glt_x, glt_y, good_wavelengths)
    indices = scene.get_effective_band_indices()
    assert indices == list(range(18))
    assert len(indices) == 18


def test_emit_scene_temp_file_cleaned_on_error() -> None:
    with patch("earthaccess.login") as mock_login:
        mock_auth = MagicMock()
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("HTTP 500")
        mock_session.get.return_value = mock_resp
        mock_auth.get_session.return_value = mock_session
        mock_login.return_value = mock_auth

        granule = {
            "id": "test",
            "bbox": [0, 0, 1, 1],
            "datetime": "",
            "cloud_cover": None,
            "asset_href": "https://data.example.com/test.nc",
        }
        tmp_dir = Path(tempfile.mkdtemp())

        def track_temp(path: Path) -> None:
            (tmp_dir / path.name).touch()

        import pytest

        with (
            patch("pathlib.Path.unlink") as mock_unlink,
            pytest.raises(EmitHTTPError),
        ):
            EmitScene.from_granule(granule)

        mock_unlink.assert_called_once_with(missing_ok=True)
