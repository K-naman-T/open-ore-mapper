from __future__ import annotations

import base64
import io

import numpy as np
import pytest
from PIL import Image

from spectral_matching.rendering import class_map_png_data_url, confidence_png_data_url, class_statistics


def test_class_map_png_data_url_decode_verify_dimensions() -> None:
    class_map = np.array([[0, 1], [255, 0]], dtype=np.uint8)
    data_url = class_map_png_data_url(class_map, ["A", "B"])
    assert data_url.startswith("data:image/png;base64,")
    b64 = data_url.removeprefix("data:image/png;base64,")
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    assert img.size == (2, 2)


def test_confidence_png_data_url_decode_verify_dimensions() -> None:
    confidence = np.array([[0.0, 0.5], [1.0, 0.25]], dtype=np.float32)
    data_url = confidence_png_data_url(confidence)
    assert data_url.startswith("data:image/png;base64,")
    b64 = data_url.removeprefix("data:image/png;base64,")
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    assert img.size == (2, 2)


def test_confidence_png_all_zero_vs_all_one() -> None:
    zero = confidence_png_data_url(np.zeros((1, 1), dtype=np.float32))
    one = confidence_png_data_url(np.ones((1, 1), dtype=np.float32))
    assert zero.startswith("data:image/png;base64,")
    assert one.startswith("data:image/png;base64,")
    assert zero != one


def test_statistics_include_count_percentage_confidence_and_abundance() -> None:
    class_map = np.array([[0, 1], [255, 0]], dtype=np.uint8)
    confidence = np.array([[0.8, 0.7], [0.0, 0.9]], dtype=np.float32)
    abundances = np.zeros((2, 2, 2), dtype=np.float32)
    abundances[:, :, 0] = 0.6
    abundances[:, :, 1] = 0.4
    stats = class_statistics(class_map, confidence, abundances, ["A", "B"])
    assert stats["A"].count == 2
    assert stats["A"].percentage == 50.0
    assert stats["A"].mean_confidence == pytest.approx(0.85)
    assert stats["A"].mean_abundance == pytest.approx(0.6)
    assert stats["B"].count == 1
    assert stats["B"].mean_confidence == pytest.approx(0.7)
    assert stats["B"].mean_abundance == pytest.approx(0.4)


def test_class_map_all_unknown_produces_valid_png() -> None:
    class_map = np.full((3, 3), 255, dtype=np.uint8)
    data_url = class_map_png_data_url(class_map, ["A"])
    assert data_url.startswith("data:image/png;base64,")


def test_statistics_empty_class_list_returns_empty_dict() -> None:
    class_map = np.array([[0, 0], [0, 0]], dtype=np.uint8)
    confidence = np.full((2, 2), 0.5, dtype=np.float32)
    abundances = np.zeros((2, 2, 0), dtype=np.float32)
    stats = class_statistics(class_map, confidence, abundances, [])
    assert stats == {}
