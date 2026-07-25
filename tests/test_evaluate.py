"""Tests for evaluate_maps and write_evaluation_artifacts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from open_ore_mapper.evaluate import (
    UNKNOWN_CLASS,
    evaluate_maps,
    overlay_class_on_rgb,
    rasterize_rois,
    render_diff_rgb,
    true_color_rgb,
    write_evaluation_artifacts,
)


def test_perfect_match_oa_one() -> None:
    names = ["a", "b"]
    ref = np.array([[0, 0], [1, 1]], dtype=np.uint8)
    pred = ref.copy()
    result = evaluate_maps(pred, ref, names)
    assert result.overall_accuracy == 1.0
    assert result.n_labeled == 4
    assert result.n_correct == 4
    assert result.kappa == 1.0
    assert result.per_class[0].recall == 1.0
    assert result.per_class[1].precision == 1.0


def test_systematic_swap_oa_zero_on_labeled() -> None:
    names = ["a", "b"]
    ref = np.array([[0, 0], [1, 1]], dtype=np.uint8)
    pred = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    result = evaluate_maps(pred, ref, names)
    assert result.overall_accuracy == 0.0
    assert result.n_correct == 0


def test_ignore_unknown_reference_pixels() -> None:
    names = ["a", "b"]
    ref = np.array([[0, UNKNOWN_CLASS], [1, UNKNOWN_CLASS]], dtype=np.uint8)
    pred = np.array([[0, 1], [1, 0]], dtype=np.uint8)
    result = evaluate_maps(pred, ref, names)
    assert result.n_labeled == 2
    assert result.overall_accuracy == 1.0


def test_predicted_unknown_counts_as_error() -> None:
    names = ["a"]
    ref = np.array([[0, 0]], dtype=np.uint8)
    pred = np.array([[0, UNKNOWN_CLASS]], dtype=np.uint8)
    result = evaluate_maps(pred, ref, names)
    assert result.n_labeled == 2
    assert result.overall_accuracy == 0.5


def test_write_artifacts(tmp_path: Path) -> None:
    names = ["hematite", "kaolinite"]
    ref = np.zeros((8, 8), dtype=np.uint8)
    ref[:, 4:] = 1
    pred = ref.copy()
    result = write_evaluation_artifacts(tmp_path, pred, ref, names)
    assert result.overall_accuracy == 1.0
    assert (tmp_path / "metrics.json").is_file()
    assert (tmp_path / "confusion.csv").is_file()
    assert (tmp_path / "our_class.png").is_file()
    assert (tmp_path / "reference.png").is_file()
    assert (tmp_path / "diff.png").is_file()
    assert (tmp_path / "report.md").is_file()
    metrics = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["overall_accuracy"] == 1.0


def test_write_artifacts_map_agreement_framing(tmp_path: Path) -> None:
    """Shipped demo path must label OA as map-to-map agreement, not field truth."""
    names = ["a", "b"]
    ref = np.zeros((6, 6), dtype=np.uint8)
    ref[:, 3:] = 1
    pred = ref.copy()
    pred[0, 0] = 1  # one error
    write_evaluation_artifacts(
        tmp_path,
        pred,
        ref,
        names,
        extra_metrics={
            "classifier": "fuse_classical",
            "metric_framing": "map_to_map_agreement",
            "not_field_truth": True,
            "product_default": "unsupervised_classical",
            "external_classical_bar": "fuse multi-seed spatial ~0.664",
        },
    )
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "map-to-map agreement" in report.lower()
    assert "not" in report.lower() and "field" in report.lower()
    assert "fuse multi-seed" in report
    metrics = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["provenance"]["classifier"] == "fuse_classical"
    assert metrics["provenance"]["metric_framing"] == "map_to_map_agreement"
    assert 0.0 < metrics["overall_accuracy"] < 1.0


def test_true_color_rgb_shape_and_range() -> None:
    rng = np.random.default_rng(0)
    h, w, b = 20, 24, 30
    # wavelengths in nm
    wl = [400.0 + i * 10.0 for i in range(b)]
    cube = rng.uniform(0.05, 0.6, size=(h, w, b)).astype(np.float32)
    rgb = true_color_rgb(cube, wl)
    assert rgb.shape == (h, w, 3)
    assert rgb.dtype == np.uint8
    assert rgb.max() > 0


def test_true_color_accepts_micrometers() -> None:
    rng = np.random.default_rng(1)
    cube = rng.uniform(0.1, 0.5, size=(8, 8, 10)).astype(np.float32)
    wl_um = [0.45 + i * 0.03 for i in range(10)]
    rgb = true_color_rgb(cube, wl_um)
    assert rgb.shape == (8, 8, 3)


def test_overlay_class_on_rgb_preserves_unknown_terrain() -> None:
    base = np.full((10, 10, 3), 120, dtype=np.uint8)
    labels = np.full((10, 10), UNKNOWN_CLASS, dtype=np.uint8)
    labels[2:5, 2:5] = 0
    out = overlay_class_on_rgb(base, labels, n_classes=2, alpha=0.5, only_labeled=True)
    # Unknown region stays base gray
    assert np.all(out[0, 0] == 120)
    # Class region moved toward palette red-ish (class 0)
    assert int(out[3, 3, 0]) != 120 or int(out[3, 3, 1]) != 120


def test_diff_colors_match_and_mismatch() -> None:
    ref = np.array([[0, 0], [1, UNKNOWN_CLASS]], dtype=np.uint8)
    pred = np.array([[0, 1], [UNKNOWN_CLASS, 0]], dtype=np.uint8)
    rgb = render_diff_rgb(pred, ref)
    assert tuple(rgb[0, 0]) == (34, 139, 34)  # match
    assert tuple(rgb[0, 1]) == (178, 34, 34)  # mismatch
    assert tuple(rgb[1, 0]) == (255, 140, 0)  # ours unknown
    assert tuple(rgb[1, 1]) == (40, 40, 40)  # ignore


def test_rasterize_rois() -> None:
    names = {"hematite": 0, "kaolinite": 1}
    rois = [
        {"mineral": "hematite", "row0": 0, "row1": 2, "col0": 0, "col1": 2},
        {"mineral": "kaolinite", "row0": 2, "row1": 4, "col0": 2, "col1": 4},
    ]
    ref = rasterize_rois(4, 4, rois, names)
    assert ref[0, 0] == 0
    assert ref[3, 3] == 1
    assert ref[0, 3] == UNKNOWN_CLASS
