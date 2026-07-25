"""Unit tests for 1D-CNN spatial path (shipped train→predict→evaluate)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import tifffile

pytest.importorskip("torch")
pytest.importorskip("sklearn")

from open_ore_mapper.evaluate import UNKNOWN_CLASS
from open_ore_mapper.ml_cnn1d import (
    SpectralCNN1D,
    predict_cnn1d,
    run_cnn1d_spatial_seed,
    train_cnn1d,
)


def _write_mini_bench(tmp_path: Path, *, seed: int = 0) -> Path:
    rng = np.random.default_rng(seed)
    h, w, b = 40, 40, 24
    wavelengths = [400.0 + i * 20.0 for i in range(b)]
    cube = np.zeros((h, w, b), dtype=np.float32)
    ref = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
    for br in range(4):
        for bc in range(4):
            r0, c0 = br * 10, bc * 10
            cls = (br + bc) % 2
            # Distinct spectral shapes
            t = np.linspace(0, 1, b, dtype=np.float32)
            base = 0.3 + 0.4 * cls + 0.2 * np.sin(2 * np.pi * (t + 0.3 * cls))
            cube[r0 : r0 + 10, c0 : c0 + 10, :] = base + 0.03 * rng.standard_normal(
                (10, 10, b)
            ).astype(np.float32)
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


def test_train_predict_cnn1d_core() -> None:
    rng = np.random.default_rng(0)
    n, b, c = 200, 32, 3
    X = rng.standard_normal((n, b)).astype(np.float32)
    y = rng.integers(0, c, size=n)
    # Make classes separable by mean shift
    for i in range(c):
        X[y == i] += i * 0.5
    model = train_cnn1d(X, y, c, epochs=5, batch_size=64, seed=0, channels=16)
    pred = predict_cnn1d(model, X[:50], batch_size=16)
    assert pred.shape == (50,)
    assert pred.dtype == np.uint8
    assert set(pred.tolist()).issubset(set(range(c)))


def test_cnn1d_spatial_seed_path(tmp_path: Path) -> None:
    bench = _write_mini_bench(tmp_path)
    out = tmp_path / "out_cnn"
    summary = run_cnn1d_spatial_seed(
        bench,
        out,
        seed=42,
        feature_mode="reflectance",
        n_row_blocks=2,
        n_col_blocks=2,
        epochs=8,
        batch_size=64,
        max_train_samples_per_class=200,
        min_endmember_pixels=5,
        channels=16,
        device="cpu",
    )
    assert summary["n_labeled"] > 0
    assert 0.0 < summary["overall_accuracy"] <= 1.0
    assert (out / "metrics.json").is_file()
    assert (out / "class_map.npy").is_file()
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["provenance"]["score_region"] == "test_blocks_only"
    assert metrics["method"] == "cnn1d_reflectance"
    class_map = np.load(out / "class_map.npy")
    valid = class_map != UNKNOWN_CLASS
    assert valid.any()


def test_cnn1d_mnf_mode(tmp_path: Path) -> None:
    bench = _write_mini_bench(tmp_path, seed=3)
    out = tmp_path / "out_mnf"
    summary = run_cnn1d_spatial_seed(
        bench,
        out,
        seed=7,
        feature_mode="mnf",
        n_row_blocks=2,
        n_col_blocks=2,
        mnf_components=8,
        epochs=6,
        batch_size=64,
        min_endmember_pixels=5,
        channels=16,
        device="cpu",
    )
    assert summary["n_bands"] == 8
    assert summary["n_labeled"] > 0
    assert summary["overall_accuracy"] > 0.0
