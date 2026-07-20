import numpy as np

from open_ore_mapper.rendering import class_map_png_data_url, confidence_png_data_url, mineral_statistics


def test_class_map_png_data_url_is_returned() -> None:
    class_map = np.array([[0, 1], [255, 0]], dtype=np.uint8)
    data_url = class_map_png_data_url(class_map, ["A", "B"])
    assert data_url.startswith("data:image/png;base64,")


def test_confidence_png_data_url_is_returned() -> None:
    confidence = np.array([[0.0, 0.5], [1.0, 0.25]], dtype=np.float32)
    data_url = confidence_png_data_url(confidence)
    assert data_url.startswith("data:image/png;base64,")


def test_statistics_include_count_percentage_confidence_and_abundance() -> None:
    class_map = np.array([[0, 1], [255, 0]], dtype=np.uint8)
    confidence = np.array([[0.8, 0.7], [0.0, 0.9]], dtype=np.float32)
    abundances = np.zeros((2, 2, 2), dtype=np.float32)
    abundances[:, :, 0] = 0.6
    abundances[:, :, 1] = 0.4
    stats = mineral_statistics(class_map, confidence, abundances, ["A", "B"])
    assert stats["A"].count == 2
    assert stats["A"].percentage == 50.0
    assert stats["A"].mean_confidence > 0.8
    assert stats["A"].mean_abundance == np.float32(0.6)
