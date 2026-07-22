from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from open_ore_mapper import tileserver


# ---------------------------------------------------------------------------
# Map UUID validation
# ---------------------------------------------------------------------------


class TestMapUuidValidation:
    def test_accepts_short_hex(self) -> None:
        tileserver.validate_map_uuid("a1b2c3d4e5f6")

    def test_accepts_long_hex(self) -> None:
        tileserver.validate_map_uuid("abcdef0123456789ab")

    def test_accepts_hyphens(self) -> None:
        tileserver.validate_map_uuid("test-uuid")
        tileserver.validate_map_uuid("map-2024-01")

    def test_accepts_underscores(self) -> None:
        tileserver.validate_map_uuid("legacy_map_id")
        tileserver.validate_map_uuid("my_map_v2")

    def test_rejects_path_traversal_with_slashes(self) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.validate_map_uuid("../../etc/passwd")

    def test_rejects_path_traversal_with_backslashes(self) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.validate_map_uuid("..\\..\\etc")

    def test_rejects_dot_dot_only(self) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.validate_map_uuid("..")

    def test_rejects_absolute_path(self) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.validate_map_uuid("/etc/passwd")

    def test_rejects_empty_string(self) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.validate_map_uuid("")

    def test_rejects_too_long_id(self) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.validate_map_uuid("a" * 65)

    def test_rejects_null_byte(self) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.validate_map_uuid("valid\x00id")

    def test_rejects_leading_dot(self) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.validate_map_uuid(".hidden")


# ---------------------------------------------------------------------------
# Tile coordinate validation
# ---------------------------------------------------------------------------


class TestTileCoordValidation:
    def test_accepts_zero(self) -> None:
        tileserver.validate_tile_coords(0, 0, 0)

    def test_accepts_positive(self) -> None:
        tileserver.validate_tile_coords(5, 100, 200)

    def test_rejects_negative_z(self) -> None:
        with pytest.raises(ValueError, match="Negative"):
            tileserver.validate_tile_coords(-1, 0, 0)

    def test_rejects_negative_x(self) -> None:
        with pytest.raises(ValueError, match="Negative"):
            tileserver.validate_tile_coords(0, -1, 0)

    def test_rejects_negative_y(self) -> None:
        with pytest.raises(ValueError, match="Negative"):
            tileserver.validate_tile_coords(0, 0, -1)

    def test_rejects_excessive_zoom(self) -> None:
        with pytest.raises(ValueError, match="Zoom"):
            tileserver.validate_tile_coords(31, 0, 0)


# ---------------------------------------------------------------------------
# get_tile_path safety (the main public API)
# ---------------------------------------------------------------------------


class TestGetTilePathSafety:
    def test_traversal_via_slashes_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("../../etc", 0, 0, 0, tiles_dir=tmp_path) is None

    def test_traversal_via_backslashes_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("..\\..\\etc", 0, 0, 0, tiles_dir=tmp_path) is None

    def test_absolute_map_uuid_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("/etc/passwd", 0, 0, 0, tiles_dir=tmp_path) is None

    def test_dot_dot_map_uuid_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("..", 0, 0, 0, tiles_dir=tmp_path) is None

    def test_negative_z_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("valid-id", -1, 0, 0, tiles_dir=tmp_path) is None

    def test_negative_x_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("valid-id", 0, -1, 0, tiles_dir=tmp_path) is None

    def test_negative_y_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("valid-id", 0, 0, -1, tiles_dir=tmp_path) is None

    def test_excessive_zoom_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("valid-id", 31, 0, 0, tiles_dir=tmp_path) is None

    def test_empty_map_uuid_returns_none(self, tmp_path: Path) -> None:
        assert tileserver.get_tile_path("", 0, 0, 0, tiles_dir=tmp_path) is None

    def test_valid_coords_with_existing_file(self, tmp_path: Path) -> None:
        p = tmp_path / "valid-id" / "0" / "0" / "0.png"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"PNG")
        result = tileserver.get_tile_path("valid-id", 0, 0, 0, tiles_dir=tmp_path)
        assert result is not None
        assert result.exists()

    def test_valid_coords_with_missing_file(self, tmp_path: Path) -> None:
        result = tileserver.get_tile_path("valid-id", 0, 0, 0, tiles_dir=tmp_path)
        assert result is None

    def test_returned_path_is_under_tiles_dir(self, tmp_path: Path) -> None:
        p = tmp_path / "valid-id" / "5" / "3" / "2.png"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"PNG")
        result = tileserver.get_tile_path("valid-id", 5, 3, 2, tiles_dir=tmp_path)
        assert result is not None
        root = tmp_path.resolve()
        result.relative_to(root)  # raises if not under root


# ---------------------------------------------------------------------------
# write_tiles and get_tile_metadata also validate map_uuid
# ---------------------------------------------------------------------------


class TestWriteTilesValidation:
    def test_write_tiles_rejects_bad_uuid(self, tmp_path: Path) -> None:
        class_map = np.zeros((64, 64), dtype=np.uint8)
        confidence = np.ones((64, 64), dtype=np.float32)
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.write_tiles(
                class_map, confidence, ["A"], "../../evil", (0, 0, 1, 1), tiles_dir=tmp_path
            )


class TestGetTileMetadataValidation:
    def test_get_tile_metadata_rejects_bad_uuid(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid map_uuid"):
            tileserver.get_tile_metadata("../../evil", tiles_dir=tmp_path)


# ---------------------------------------------------------------------------
# API-level tests for the tile endpoint
# ---------------------------------------------------------------------------


def test_tile_api_traversal_returns_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import open_ore_mapper.tileserver as ts

    monkeypatch.setattr(ts, "TILES_DIR", tmp_path)
    from open_ore_mapper.api import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    # URL-encoded slashes that route to the endpoint; get_tile_path will
    # reject the map_uuid and return None → 404
    resp = client.get("/v1/maps/%2e%2e%2f%2e%2e%2fetc/tiles/0/0/0.png")
    assert resp.status_code == 404


def test_tile_api_negative_z_returns_422(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import open_ore_mapper.tileserver as ts

    monkeypatch.setattr(ts, "TILES_DIR", tmp_path)
    from open_ore_mapper.api import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/v1/maps/valid-id/tiles/-1/0/0.png")
    assert resp.status_code == 422


def test_tile_api_empty_map_uuid_returns_404(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import open_ore_mapper.tileserver as ts

    monkeypatch.setattr(ts, "TILES_DIR", tmp_path)
    from open_ore_mapper.api import app
    from fastapi.testclient import TestClient

    client = TestClient(app)
    resp = client.get("/v1/maps//tiles/0/0/0.png")
    assert resp.status_code == 404


def test_tile_api_valid_tile_returns_200(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import open_ore_mapper.tileserver as ts

    monkeypatch.setattr(ts, "TILES_DIR", tmp_path)
    from open_ore_mapper.api import app
    from fastapi.testclient import TestClient

    p = tmp_path / "valid-id" / "0" / "0" / "0.png"
    p.parent.mkdir(parents=True)
    p.write_bytes(b"PNG")
    (tmp_path / "valid-id" / "metadata.json").write_text('{"map_uuid":"valid-id","bbox":[0,0,1,1]}')

    client = TestClient(app)
    resp = client.get("/v1/maps/valid-id/tiles/0/0/0.png")
    assert resp.status_code == 200
    assert "image/png" in resp.headers["content-type"]


# ---------------------------------------------------------------------------
# Existing tests (unchanged behaviour)
# ---------------------------------------------------------------------------


def test_write_tiles_creates_directory_structure(tmp_path: Path) -> None:
    class_map = np.zeros((256, 256), dtype=np.uint8)
    confidence = np.ones((256, 256), dtype=np.float32)

    tile_root = tileserver.write_tiles(
        class_map,
        confidence,
        ["A", "B"],
        "test-uuid",
        (0, 0, 1, 1),
        tiles_dir=tmp_path,
    )

    assert tile_root.exists()
    png_files = list(tile_root.rglob("*.png"))
    assert len(png_files) >= 1


def test_write_tiles_png_files_are_valid(tmp_path: Path) -> None:
    class_map = np.zeros((256, 256), dtype=np.uint8)
    confidence = np.ones((256, 256), dtype=np.float32)

    tileserver.write_tiles(
        class_map,
        confidence,
        ["A", "B"],
        "test-uuid-2",
        (0, 0, 1, 1),
        tiles_dir=tmp_path,
    )

    png_files = list((tmp_path / "test-uuid-2").rglob("*.png"))
    assert len(png_files) > 0
    img = Image.open(png_files[0])
    assert img.mode in ("RGB", "RGBA")


def test_tile_coordinates_correct(tmp_path: Path) -> None:
    class_map = np.zeros((256, 256), dtype=np.uint8)
    confidence = np.ones((256, 256), dtype=np.float32)

    tileserver.write_tiles(
        class_map,
        confidence,
        ["A", "B"],
        "test-uuid-3",
        (0, 0, 1, 1),
        tiles_dir=tmp_path,
    )

    tile_path = tileserver.get_tile_path("test-uuid-3", 0, 0, 0, tiles_dir=tmp_path)
    assert tile_path is not None
    assert tile_path.exists()

    meta = tileserver.get_tile_metadata("test-uuid-3", tiles_dir=tmp_path)
    assert meta is not None
    assert "bbox" in meta


def test_tile_for_nonexistent_area_returns_404(tmp_path: Path) -> None:
    class_map = np.zeros((256, 256), dtype=np.uint8)
    confidence = np.ones((256, 256), dtype=np.float32)

    tileserver.write_tiles(
        class_map,
        confidence,
        ["A", "B"],
        "test-uuid-4",
        (0, 0, 1, 1),
        tiles_dir=tmp_path,
    )

    tile_path = tileserver.get_tile_path("test-uuid-4", 18, 0, 0, tiles_dir=tmp_path)
    assert tile_path is None


def test_subtiles_for_large_scene(tmp_path: Path) -> None:
    class_map = np.zeros((512, 512), dtype=np.uint8)
    confidence = np.ones((512, 512), dtype=np.float32)

    tileserver.write_tiles(
        class_map,
        confidence,
        ["A", "B"],
        "test-uuid-5",
        (0, 0, 1, 1),
        tiles_dir=tmp_path,
    )

    meta = tileserver.get_tile_metadata("test-uuid-5", tiles_dir=tmp_path)
    assert meta is not None
    assert meta["max_zoom"] >= 1

    z1_tiles = list((tmp_path / "test-uuid-5" / "1").rglob("*.png"))
    assert len(z1_tiles) > 1
