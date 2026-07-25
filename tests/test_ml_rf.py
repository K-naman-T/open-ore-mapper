"""Unit tests for sklearn RF spatial baseline (ml_rf) + fuse_classical spatial branch."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pytest
import tifffile

pytest.importorskip("sklearn")

from open_ore_mapper.evaluate import UNKNOWN_CLASS, evaluate_maps
from open_ore_mapper.ml_rf import (
    FEATURE_SETS,
    _cap_train_indices,
    _fit_shared_transforms,
    _gather_features,
    continuum_remove_pixels,
    run_rf_spatial_seed,
)
from open_ore_mapper.spatial_eval import (
    SPLIT_TEST,
    SPLIT_TRAIN,
    make_spatial_split,
    run_spatial_split_eval,
)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------


def _synthetic_hwc_scene(
    height: int = 24,
    width: int = 24,
    n_bands: int = 16,
    seed: int = 0,
    patch: int = 3,
) -> tuple[np.ndarray, np.ndarray, list[str], list[float]]:
    """Build a small HWC cube with two classes tiled so both appear in all blocks.

    Alternating ``patch×patch`` pure tiles (not left/right halves) so spatial
    2×2 train/test splits still see both minerals in train *and* test.
    """
    rng = np.random.default_rng(seed)
    wavelengths = [float(400 + i * 100) for i in range(n_bands)]
    wl = np.asarray(wavelengths, dtype=np.float32)

    end0 = 0.25 + 0.35 * (wl - wl.min()) / (wl.max() - wl.min())
    end1 = 0.55 - 0.15 * np.sin(2 * np.pi * (wl - 400) / 800)
    mid = n_bands // 2
    end1[mid - 1 : mid + 2] *= 0.55  # shallow absorption

    cube = np.zeros((height, width, n_bands), dtype=np.float32)
    reference = np.full((height, width), UNKNOWN_CLASS, dtype=np.uint8)
    for r in range(height):
        for c in range(width):
            cls = int(((r // patch) + (c // patch)) % 2)
            base = end0 if cls == 0 else end1
            noise = 0.02 * rng.normal(size=n_bands).astype(np.float32)
            cube[r, c] = np.clip(base + noise, 0.05, 1.2).astype(np.float32)
            reference[r, c] = cls

    names = ["hematite", "kaolinite"]
    return cube, reference, names, wavelengths


def _write_mini_benchmark(
    root: Path,
    cube: np.ndarray,
    reference: np.ndarray,
    class_names: list[str],
    wavelengths: list[float],
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(root / "scene.tif", cube.astype(np.float32), photometric="minisblack")
    tifffile.imwrite(root / "reference.tif", reference.astype(np.uint8), photometric="minisblack")
    (root / "legend.json").write_text(
        json.dumps({"class_names": class_names, "ignore_index": UNKNOWN_CLASS}),
        encoding="utf-8",
    )
    (root / "wavelengths.json").write_text(json.dumps(wavelengths), encoding="utf-8")
    (root / "options.json").write_text(
        json.dumps({"minerals": class_names, "classifier": "sam"}),
        encoding="utf-8",
    )
    return root


# ---------------------------------------------------------------------------
# Feature / transform helpers
# ---------------------------------------------------------------------------


def test_feature_sets_documented() -> None:
    assert "reflectance" in FEATURE_SETS
    assert "mnf" in FEATURE_SETS
    assert "mtmf_scores" in FEATURE_SETS
    assert "refl_mnf_mtmf" in FEATURE_SETS


def test_continuum_remove_pixels_shape() -> None:
    wl = [400.0, 500.0, 600.0, 700.0, 800.0]
    specs = np.array(
        [
            [0.2, 0.3, 0.25, 0.35, 0.4],
            [0.5, 0.45, 0.2, 0.4, 0.5],
        ],
        dtype=np.float32,
    )
    out = continuum_remove_pixels(specs, wl)
    assert out.shape == specs.shape
    assert np.all(np.isfinite(out))
    # hull quotient of a continuum-ish spectrum stays near 1
    assert float(np.mean(out[0])) == pytest.approx(1.0, abs=0.15)


def test_cap_train_indices_limits_per_class() -> None:
    y = np.array([0] * 50 + [1] * 10, dtype=np.int64)
    pick = _cap_train_indices(y, max_per_class=8, seed=1)
    assert pick.size == 16
    assert int((y[pick] == 0).sum()) == 8
    assert int((y[pick] == 1).sum()) == 8


def test_gather_features_reflectance_only() -> None:
    cube, _ref, _names, wl = _synthetic_hwc_scene(height=8, width=8, n_bands=10)
    coords = np.array([[0, 0], [1, 2], [3, 4]], dtype=np.intp)
    X, meta = _gather_features(
        cube,
        wl,
        coords,
        feature_set="reflectance",
        mnf_cube=None,
        mf=None,
        infeas=None,
    )
    assert X.shape == (3, 10)
    assert meta["n_features"] == 10
    np.testing.assert_allclose(X[0], cube[0, 0])


def test_fit_shared_transforms_train_mask_only_for_mtmf() -> None:
    """MTMF background stats use train_bg; mutating pure-test pixels must not
    change MF scores on train pixels when refit with the same train_bg mask.
    """
    cube, reference, _names, _wl = _synthetic_hwc_scene(height=20, width=20, n_bands=12, seed=3)
    h, w, b = cube.shape
    split = make_spatial_split(h, w, n_row_blocks=2, n_col_blocks=2, seed=42)
    train_bg = split.mask(SPLIT_TRAIN)
    test_mask = split.mask(SPLIT_TEST)

    # Library = mean spectra of each class on train pure pixels
    lib_rows = []
    for cls in (0, 1):
        m = train_bg & (reference == cls)
        lib_rows.append(cube[m].mean(axis=0))
    library = np.stack(lib_rows, axis=0).astype(np.float32)

    mnf0, mf0, inf0 = _fit_shared_transforms(
        cube,
        library,
        train_bg,
        feature_set="mtmf_scores",
        mnf_components=6,
        mtmf_seed=7,
    )
    assert mnf0 is None  # not needed for mtmf_scores alone
    assert mf0 is not None and inf0 is not None

    # Corrupt test-only pure pixels with extreme spectra
    cube_corrupt = cube.copy()
    cube_corrupt[test_mask] = 0.01 + 0.98 * np.linspace(0, 1, b, dtype=np.float32)

    _mnf1, mf1, inf1 = _fit_shared_transforms(
        cube_corrupt,
        library,
        train_bg,
        feature_set="mtmf_scores",
        mnf_components=6,
        mtmf_seed=7,
    )
    # Train-block MF must be unchanged (bg stats from train_bg only)
    np.testing.assert_allclose(mf0[train_bg], mf1[train_bg], rtol=1e-5, atol=1e-5)
    np.testing.assert_allclose(inf0[train_bg], inf1[train_bg], rtol=1e-5, atol=1e-5)


def test_fit_shared_transforms_mnf_sample_mask_is_train() -> None:
    """MNF signal stats use train_bg; full-scene fit as sample_mask changes train MNF."""
    cube, _ref, _names, _wl = _synthetic_hwc_scene(height=20, width=20, n_bands=12, seed=5)
    h, w, _b = cube.shape
    split = make_spatial_split(h, w, n_row_blocks=2, n_col_blocks=2, seed=11)
    train_bg = split.mask(SPLIT_TRAIN)
    full = np.ones((h, w), dtype=bool)

    # Make test half statistically very different so sample mean differs
    cube2 = cube.copy()
    cube2[~train_bg] = cube2[~train_bg] * 0.3 + 0.5

    library = np.stack([cube[train_bg].mean(axis=0)] * 2, axis=0).astype(np.float32)

    mnf_train, _, _ = _fit_shared_transforms(
        cube2,
        library,
        train_bg,
        feature_set="mnf",
        mnf_components=5,
        mtmf_seed=0,
    )
    mnf_full, _, _ = _fit_shared_transforms(
        cube2,
        library,
        full,  # deliberately leaky sample mask
        feature_set="mnf",
        mnf_components=5,
        mtmf_seed=0,
    )
    assert mnf_train is not None and mnf_full is not None
    # Different sample_mask ⇒ different projection (features on train pixels differ)
    assert not np.allclose(mnf_train[train_bg], mnf_full[train_bg], rtol=1e-3, atol=1e-3)


# ---------------------------------------------------------------------------
# End-to-end RF on tiny synthetic benchmark package
# ---------------------------------------------------------------------------


def test_run_rf_spatial_seed_trains_on_train_blocks_only(tmp_path: Path) -> None:
    cube, reference, names, wavelengths = _synthetic_hwc_scene(
        height=24, width=24, n_bands=14, seed=1
    )
    bench = _write_mini_benchmark(tmp_path / "bench", cube, reference, names, wavelengths)
    out = tmp_path / "rf_out"

    summary = run_rf_spatial_seed(
        bench,
        out,
        seed=42,
        feature_set="reflectance",
        n_row_blocks=2,
        n_col_blocks=2,
        train_frac=0.5,
        val_frac=0.0,
        n_estimators=30,
        max_depth=6,
        min_samples_leaf=1,
        rf_seed=0,
        max_train_samples_per_class=500,
        min_endmember_pixels=5,
    )

    assert summary["n_train_samples"] > 0
    assert summary["overall_accuracy"] is not None
    assert 0.0 <= float(summary["overall_accuracy"]) <= 1.0
    assert (out / "metrics.json").is_file()
    assert (out / "class_map.npy").is_file()
    assert (out / "summary.json").is_file()

    class_map = np.load(out / "class_map.npy")
    assert class_map.shape == cube.shape[:2]
    # Predictions cover the map (closed-set on valid pixels)
    assert np.all(np.isin(class_map, [0, 1, UNKNOWN_CLASS]))
    n_assigned = int(np.isin(class_map, [0, 1]).sum())
    assert n_assigned == cube.shape[0] * cube.shape[1]

    # Train sample count equals labeled train pixels (no cap hit on tiny scene)
    split = make_spatial_split(24, 24, n_row_blocks=2, n_col_blocks=2, seed=42)
    train_mask = split.mask(SPLIT_TRAIN)
    labeled_train = int((train_mask & (reference != UNKNOWN_CLASS)).sum())
    assert summary["n_train_samples"] == labeled_train

    # OA computable via evaluate_maps on test-block labels
    test_ref = reference.copy()
    test_ref[~split.mask(SPLIT_TEST)] = UNKNOWN_CLASS
    metrics = evaluate_maps(class_map, test_ref, names)
    assert metrics.n_labeled > 0
    assert metrics.overall_accuracy == pytest.approx(summary["overall_accuracy"], abs=1e-6)


def test_run_rf_spatial_seed_mnf_features(tmp_path: Path) -> None:
    cube, reference, names, wavelengths = _synthetic_hwc_scene(
        height=20, width=20, n_bands=12, seed=2
    )
    bench = _write_mini_benchmark(tmp_path / "bench", cube, reference, names, wavelengths)
    summary = run_rf_spatial_seed(
        bench,
        tmp_path / "rf_mnf",
        seed=7,
        feature_set="mnf",
        n_row_blocks=2,
        n_col_blocks=2,
        train_frac=0.5,
        val_frac=0.0,
        n_estimators=20,
        max_depth=4,
        mnf_components=6,
        min_endmember_pixels=5,
        max_train_samples_per_class=200,
    )
    assert summary["n_features"] == 6
    assert summary["n_labeled"] > 0


def test_run_rf_spatial_seed_test_only_labels_not_in_train(tmp_path: Path) -> None:
    """If a class exists only in test blocks, it cannot appear in RF train labels.

    We inject a third class only on a fixed test block and check classes_in_train.
    """
    cube, reference, names, wavelengths = _synthetic_hwc_scene(
        height=24, width=24, n_bands=12, seed=9
    )
    # Third class pure pixels only in bottom-right quadrant (often test under seed=0)
    names3 = ["hematite", "kaolinite", "alunite"]
    reference = reference.copy()
    reference[18:24, 18:24] = 2
    # Give those pixels a distinct spectrum
    cube = cube.copy()
    cube[18:24, 18:24] = 0.15

    # Find a seed where class 2 is entirely outside train blocks
    chosen_seed = None
    for seed in range(0, 200):
        split = make_spatial_split(24, 24, n_row_blocks=2, n_col_blocks=2, seed=seed)
        train_m = split.mask(SPLIT_TRAIN)
        if int((train_m & (reference == 2)).sum()) == 0 and int(
            (split.mask(SPLIT_TEST) & (reference == 2)).sum()
        ) > 0:
            chosen_seed = seed
            break
    assert chosen_seed is not None, "could not find split keeping class 2 out of train"

    bench = _write_mini_benchmark(tmp_path / "bench", cube, reference, names3, wavelengths)
    out = tmp_path / "rf_leak"
    summary = run_rf_spatial_seed(
        bench,
        out,
        seed=chosen_seed,
        feature_set="reflectance",
        n_row_blocks=2,
        n_col_blocks=2,
        train_frac=0.5,
        val_frac=0.0,
        n_estimators=15,
        max_depth=4,
        min_endmember_pixels=5,
        max_train_samples_per_class=500,
    )
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    classes_in_train = metrics["rf"]["classes_in_train"]
    # Class index 2 must not be in training labels
    assert 2 not in classes_in_train
    # used_names should not include alunite (no train pure pixels for library)
    assert "alunite" not in summary["used_names"]


def test_unknown_feature_set_raises(tmp_path: Path) -> None:
    cube, reference, names, wavelengths = _synthetic_hwc_scene(height=12, width=12)
    bench = _write_mini_benchmark(tmp_path / "bench", cube, reference, names, wavelengths)
    with pytest.raises(ValueError, match="feature_set"):
        run_rf_spatial_seed(
            bench,
            tmp_path / "bad",
            feature_set="not_a_real_set",
            min_endmember_pixels=3,
            n_row_blocks=2,
            n_col_blocks=2,
            n_estimators=5,
        )


# ---------------------------------------------------------------------------
# fuse_classical branch in run_spatial_split_eval
# ---------------------------------------------------------------------------


def test_spatial_eval_fuse_classical_branch_exists() -> None:
    src = inspect.getsource(run_spatial_split_eval)
    assert "fuse_classical" in src
    assert "fuse" in src


def test_run_spatial_split_eval_accepts_fuse_classical(tmp_path: Path) -> None:
    """Tiny fixture: fuse_classical should run as available method (not unknown)."""
    cube, reference, names, wavelengths = _synthetic_hwc_scene(
        height=16, width=16, n_bands=12, seed=4
    )
    bench = _write_mini_benchmark(tmp_path / "bench", cube, reference, names, wavelengths)
    out = tmp_path / "spatial_fuse"
    summary = run_spatial_split_eval(
        bench,
        out,
        n_row_blocks=2,
        n_col_blocks=2,
        train_frac=0.5,
        val_frac=0.0,
        seed=42,
        methods=["fuse_classical"],
        min_endmember_pixels=5,
        sam_threshold_deg=90.0,
        min_confidence=0.0,
        mnf_components=6,
    )
    assert "fuse_classical" in summary["methods"]
    m = summary["methods"]["fuse_classical"]
    assert m["available"] is True, m.get("notes")
    assert m["n_labeled"] > 0
    assert 0.0 <= m["overall_accuracy"] <= 1.0
    assert (out / "metrics_fuse_classical.json").is_file()
