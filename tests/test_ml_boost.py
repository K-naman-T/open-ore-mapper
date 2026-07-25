"""Unit tests for gradient boosting spatial path (shipped train→predict→evaluate)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import tifffile

pytest.importorskip("sklearn")

from open_ore_mapper.evaluate import UNKNOWN_CLASS, evaluate_maps
from open_ore_mapper.ml_boost import run_boost_spatial_seed


def _write_mini_bench(tmp_path: Path, *, seed: int = 0) -> Path:
    """Tiled pure patches so 2×2 spatial splits keep both classes in train & test."""
    rng = np.random.default_rng(seed)
    h, w, b = 40, 40, 16
    wavelengths = [400.0 + i * 20.0 for i in range(b)]
    cube = np.zeros((h, w, b), dtype=np.float32)
    ref = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
    # 4 tiles of class 0 and 4 of class 1 in checkerboard of 10x10
    for br in range(4):
        for bc in range(4):
            r0, c0 = br * 10, bc * 10
            cls = (br + bc) % 2
            spec = 0.2 + 0.5 * cls + 0.05 * rng.standard_normal(b).astype(np.float32)
            cube[r0 : r0 + 10, c0 : c0 + 10, :] = spec
            # noise per pixel
            cube[r0 : r0 + 10, c0 : c0 + 10, :] += 0.02 * rng.standard_normal((10, 10, b)).astype(
                np.float32
            )
            ref[r0 + 2 : r0 + 8, c0 + 2 : c0 + 8] = cls

    class_names = ["mineral_a", "mineral_b"]
    bench = tmp_path / "bench"
    bench.mkdir()
    tifffile.imwrite(bench / "scene.tif", cube)
    tifffile.imwrite(bench / "reference.tif", ref)
    (bench / "legend.json").write_text(
        json.dumps({"class_names": class_names, "ignore_index": 255}), encoding="utf-8"
    )
    (bench / "wavelengths.json").write_text(json.dumps(wavelengths), encoding="utf-8")
    return bench


def test_boost_hist_train_predict_oa_path(tmp_path: Path) -> None:
    bench = _write_mini_bench(tmp_path)
    out = tmp_path / "out_hist"
    summary = run_boost_spatial_seed(
        bench,
        out,
        seed=42,
        feature_set="reflectance",
        backend="hist",
        n_row_blocks=2,
        n_col_blocks=2,
        n_estimators=50,
        max_train_samples_per_class=200,
        min_endmember_pixels=5,
        min_samples_leaf=5,
    )
    assert summary["n_labeled"] > 0
    assert 0.0 < summary["overall_accuracy"] <= 1.0
    assert (out / "metrics.json").is_file()
    assert (out / "summary.json").is_file()
    assert (out / "class_map.npy").is_file()
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["provenance"]["score_region"] == "test_blocks_only"
    assert metrics["provenance"]["split"] == "spatial_block"
    assert metrics["n_labeled"] == summary["n_labeled"]


def test_boost_hist_mnf_features(tmp_path: Path) -> None:
    bench = _write_mini_bench(tmp_path, seed=1)
    out = tmp_path / "out_mnf"
    summary = run_boost_spatial_seed(
        bench,
        out,
        seed=7,
        feature_set="mnf",
        backend="hist",
        n_row_blocks=2,
        n_col_blocks=2,
        n_estimators=40,
        mnf_components=5,
        max_train_samples_per_class=100,
        min_endmember_pixels=5,
        min_samples_leaf=5,
    )
    assert summary["n_features"] == 5
    assert summary["n_labeled"] > 0
    assert summary["overall_accuracy"] > 0.0


def test_boost_lightgbm_if_available(tmp_path: Path) -> None:
    pytest.importorskip("lightgbm")
    bench = _write_mini_bench(tmp_path, seed=4)
    out = tmp_path / "out_lgb"
    summary = run_boost_spatial_seed(
        bench,
        out,
        seed=42,
        feature_set="reflectance",
        backend="lightgbm",
        n_row_blocks=2,
        n_col_blocks=2,
        n_estimators=40,
        min_endmember_pixels=5,
        min_samples_leaf=5,
    )
    assert summary["n_labeled"] > 0
    assert 0.0 < summary["overall_accuracy"] <= 1.0
    assert summary["backend"] == "lightgbm"


def test_boost_closed_set_class_map(tmp_path: Path) -> None:
    bench = _write_mini_bench(tmp_path, seed=2)
    out = tmp_path / "out_map"
    run_boost_spatial_seed(
        bench,
        out,
        seed=42,
        feature_set="reflectance",
        backend="hist",
        n_row_blocks=2,
        n_col_blocks=2,
        n_estimators=30,
        min_endmember_pixels=5,
        min_samples_leaf=3,
    )
    class_map = np.load(out / "class_map.npy")
    valid = class_map != UNKNOWN_CLASS
    assert valid.any()
    assert set(np.unique(class_map[valid])).issubset({0, 1})
