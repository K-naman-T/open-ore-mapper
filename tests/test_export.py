from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
import tifffile

from spectral_matching.export import export_geotiff


def test_export_writes_valid_tiff() -> None:
    class_map = np.zeros((10, 10), dtype=np.uint8)
    class_map[3:7, 3:7] = 1
    confidence_map = np.full((10, 10), 0.85, dtype=np.float32)
    classes = ["background", "target"]

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        out_path = export_geotiff(tmp.name, class_map, confidence_map, classes)
        assert Path(out_path).exists()
        with tifffile.TiffFile(str(out_path)) as tif:
            assert len(tif.pages) == 2
            assert tif.pages[0].shape == (10, 10)
            assert tif.pages[1].shape == (10, 10)
        Path(out_path).unlink()


def test_export_preserves_bands() -> None:
    class_map = np.array([[0, 1], [2, 3]], dtype=np.uint8)
    confidence_map = np.array([[0.1, 0.2], [0.3, 0.4]], dtype=np.float32)
    classes = ["a", "b", "c", "d"]

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        out_path = export_geotiff(tmp.name, class_map, confidence_map, classes)
        with tifffile.TiffFile(str(out_path)) as tif:
            assert tif.pages[0].dtype == np.uint8
            np.testing.assert_array_equal(tif.pages[0].asarray(), class_map)
            assert tif.pages[1].dtype == np.float32
            np.testing.assert_array_equal(tif.pages[1].asarray(), confidence_map)
        Path(out_path).unlink()


def test_export_handles_missing_crs() -> None:
    class_map = np.full((5, 5), 1, dtype=np.uint8)
    confidence_map = np.full((5, 5), 0.9, dtype=np.float32)
    classes = ["foo"]

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        out_path = export_geotiff(tmp.name, class_map, confidence_map, classes, source_path=None)
        assert Path(out_path).exists()
        with tifffile.TiffFile(str(out_path)) as tif:
            assert tif.pages[0].shape == (5, 5)
        Path(out_path).unlink()


def test_export_class_names_metadata() -> None:
    class_map = np.zeros((8, 8), dtype=np.uint8)
    confidence_map = np.full((8, 8), 0.5, dtype=np.float32)
    classes = ["hematite", "goethite", "jarosite"]

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        out_path = export_geotiff(tmp.name, class_map, confidence_map, classes)
        with tifffile.TiffFile(str(out_path)) as tif:
            page = tif.pages[1]
            for _code, tag in page.tags.items():
                value = tag.value
                if isinstance(value, str) and "CLASS_NAMES" in value:
                    import json
                    meta = json.loads(value)
                    parsed = json.loads(meta["CLASS_NAMES"])
                    assert parsed == classes
                    break
            else:
                raise AssertionError("CLASS_NAMES metadata not found")
        Path(out_path).unlink()


def test_export_rejects_empty_maps() -> None:
    class_map = np.zeros((0, 10), dtype=np.uint8)
    confidence_map = np.zeros((0, 10), dtype=np.float32)
    classes = ["a"]

    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        with pytest.raises(Exception):
            export_geotiff(tmp.name, class_map, confidence_map, classes)
        Path(tmp.name).unlink() if Path(tmp.name).exists() else None
