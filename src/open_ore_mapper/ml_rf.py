"""Sklearn Random Forest baseline on spatial-block protocol (Phase A ML).

Feature transforms that need background stats (MNF, MTMF) are fit on train-block
valid pixels only. Labels come from pure GT pixels inside train blocks.
Prediction is closed-set over train-supported classes; metrics use test blocks only.

Feature sets
------------
reflectance
    Raw spectra. Train: labeled train pixels. Predict: all valid pixels.
cr
    Continuum-removed spectra via hull_quotient (chunked). Expensive on full
    scene (~400k×bands); applied only to labeled train + valid predict pixels.
mnf
    MNF coefficients (default 20), fit on train-block background samples.
mtmf_scores
    Concat of MF scores and infeasibility per train endmember (2K features).
cr_mnf
    Continuum-removed + MNF (CR only on needed pixels).
full
    CR + MNF + MTMF scores (slowest; CR on needed pixels only).
refl_mnf_mtmf
    Reflectance + MNF + MTMF scores — primary "rich" set without full-scene CR.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .continuum_removal import hull_quotient
from .evaluate import UNKNOWN_CLASS, evaluate_maps, write_evaluation_artifacts
from .preprocessing import valid_pixel_mask
from .spatial_eval import (
    SPLIT_TEST,
    SPLIT_TRAIN,
    build_train_endmember_library,
    load_cuprite_benchmark,
    make_spatial_split,
    mask_reference_to_split,
    mnf_transform,
    remap_reference_to_names,
    write_library_csv,
    _mtmf_seeded,
)

try:
    from sklearn.ensemble import RandomForestClassifier
except ImportError as _exc:  # pragma: no cover - optional dep message
    RandomForestClassifier = None  # type: ignore[misc, assignment]
    _SKLEARN_IMPORT_ERROR = _exc
else:
    _SKLEARN_IMPORT_ERROR = None

FEATURE_SETS = (
    "reflectance",
    "cr",
    "mnf",
    "mtmf_scores",
    "cr_mnf",
    "full",
    "refl_mnf_mtmf",
)

_CR_CHUNK = 4096


def _require_sklearn() -> None:
    if RandomForestClassifier is None:
        raise ImportError(
            "scikit-learn is required for RF baselines. "
            "Install with: pip install scikit-learn"
        ) from _SKLEARN_IMPORT_ERROR


def continuum_remove_pixels(
    spectra: NDArray[np.floating[Any]],
    wavelengths: NDArray[np.float32] | list[float],
    *,
    chunk_size: int = _CR_CHUNK,
) -> NDArray[np.float32]:
    """Apply hull_quotient to (N, B) spectra in chunks (avoids full-cube CR)."""
    wl = np.asarray(wavelengths, dtype=np.float32)
    specs = np.asarray(spectra, dtype=np.float32)
    if specs.ndim != 2:
        raise ValueError("spectra must be (N, B)")
    n = specs.shape[0]
    out = np.empty_like(specs)
    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        for i in range(start, end):
            out[i] = hull_quotient(wl, specs[i])
    return out


def _cap_train_indices(
    y: NDArray[np.integer[Any]],
    *,
    max_per_class: int,
    seed: int,
) -> NDArray[np.intp]:
    """Subsample train indices so each class has at most max_per_class samples."""
    if max_per_class <= 0:
        return np.arange(y.shape[0], dtype=np.intp)
    rng = np.random.default_rng(seed)
    keep: list[NDArray[np.intp]] = []
    for c in np.unique(y):
        idx = np.flatnonzero(y == c)
        if idx.size > max_per_class:
            idx = rng.choice(idx, size=max_per_class, replace=False)
        keep.append(idx.astype(np.intp))
    if not keep:
        return np.zeros(0, dtype=np.intp)
    return np.sort(np.concatenate(keep))


def _kaolinite_recall(metrics_dict: dict[str, Any]) -> float | None:
    for row in metrics_dict.get("per_class") or []:
        name = str(row.get("name", "")).lower()
        if "kaol" in name:
            return float(row["recall"])
    return None


def _gather_features(
    cube: NDArray[np.float32],
    wavelengths: list[float],
    coords: NDArray[np.integer[Any]],
    *,
    feature_set: str,
    mnf_cube: NDArray[np.float32] | None,
    mf: NDArray[np.float32] | None,
    infeas: NDArray[np.float32] | None,
) -> tuple[NDArray[np.float32], dict[str, Any]]:
    """Stack feature columns for the given (row, col) coordinates."""
    fs = feature_set.strip().lower().replace("-", "_")
    if fs not in FEATURE_SETS:
        raise ValueError(f"unknown feature_set {feature_set!r}; choose from {FEATURE_SETS}")
    if coords.size == 0:
        return np.zeros((0, 1), dtype=np.float32), {"feature_set": fs, "n_features": 1}

    rr = coords[:, 0]
    cc = coords[:, 1]
    parts: list[NDArray[np.float32]] = []
    meta: dict[str, Any] = {"feature_set": fs}

    if fs in ("reflectance", "refl_mnf_mtmf"):
        specs = cube[rr, cc, :].astype(np.float32)
        parts.append(specs)
        meta["reflectance_bands"] = int(specs.shape[1])

    if fs in ("cr", "cr_mnf", "full"):
        specs = cube[rr, cc, :].astype(np.float32)
        cr_specs = continuum_remove_pixels(specs, wavelengths)
        parts.append(cr_specs)
        meta["cr_pixels"] = int(cr_specs.shape[0])

    if fs in ("mnf", "cr_mnf", "full", "refl_mnf_mtmf"):
        if mnf_cube is None:
            raise ValueError(f"mnf_cube required for feature_set={fs}")
        mnf_pix = mnf_cube[rr, cc, :].astype(np.float32)
        parts.append(mnf_pix)
        meta["mnf_components"] = int(mnf_pix.shape[1])

    if fs in ("mtmf_scores", "full", "refl_mnf_mtmf"):
        if mf is None or infeas is None:
            raise ValueError(f"mtmf arrays required for feature_set={fs}")
        mf_pix = mf[rr, cc, :]
        inf_pix = infeas[rr, cc, :]
        parts.append(np.concatenate([mf_pix, inf_pix], axis=1).astype(np.float32))
        meta["mtmf_k"] = int(mf.shape[2])
        meta["mtmf_features"] = int(2 * mf.shape[2])

    if not parts:
        raise ValueError(f"no feature parts built for {fs}")

    X = np.concatenate(parts, axis=1).astype(np.float32)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    meta["n_features"] = int(X.shape[1])
    meta["n_pixels"] = int(X.shape[0])
    return X, meta


def _fit_shared_transforms(
    cube: NDArray[np.float32],
    library_spectra: NDArray[np.float32],
    train_bg: NDArray[np.bool_],
    *,
    feature_set: str,
    mnf_components: int,
    mtmf_seed: int,
) -> tuple[NDArray[np.float32] | None, NDArray[np.float32] | None, NDArray[np.float32] | None]:
    """Fit MNF / MTMF once on train background when the feature set needs them."""
    fs = feature_set.strip().lower().replace("-", "_")
    mnf_cube = None
    mf = None
    infeas = None
    if fs in ("mnf", "cr_mnf", "full", "refl_mnf_mtmf"):
        mnf_cube, _ = mnf_transform(
            cube, n_components=mnf_components, sample_mask=train_bg
        )
    if fs in ("mtmf_scores", "full", "refl_mnf_mtmf"):
        mf, infeas = _mtmf_seeded(
            cube.astype(np.float32),
            library_spectra.astype(np.float32),
            valid_mask=train_bg,
            seed=mtmf_seed,
        )
    return mnf_cube, mf, infeas


def run_rf_spatial_seed(
    bench_dir: Path | str,
    output_dir: Path | str,
    *,
    seed: int = 42,
    feature_set: str = "refl_mnf_mtmf",
    n_row_blocks: int = 4,
    n_col_blocks: int = 4,
    train_frac: float = 0.5,
    val_frac: float = 0.25,
    n_estimators: int = 200,
    max_depth: int | None = None,
    min_samples_leaf: int = 2,
    rf_seed: int = 0,
    mnf_components: int = 20,
    max_train_samples_per_class: int = 2000,
    min_endmember_pixels: int = 30,
) -> dict[str, Any]:
    """One spatial seed: train RF on train pure GT, score test blocks.

    Writes metrics JSON and evaluation artifacts under output_dir.
    """
    _require_sklearn()
    fs = feature_set.strip().lower().replace("-", "_")
    if fs not in FEATURE_SETS:
        raise ValueError(f"unknown feature_set {feature_set!r}; choose from {FEATURE_SETS}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    data = load_cuprite_benchmark(bench_dir)
    cube: NDArray[np.float32] = data["cube"]
    reference: NDArray[np.uint8] = data["reference"]
    class_names: list[str] = data["class_names"]
    wavelengths: list[float] = data["wavelengths"]
    ignore = int(data["ignore_index"])
    h, w, _b = cube.shape

    split = make_spatial_split(
        h,
        w,
        n_row_blocks=n_row_blocks,
        n_col_blocks=n_col_blocks,
        train_frac=train_frac,
        val_frac=val_frac,
        seed=seed,
    )
    (out / "spatial_split.json").write_text(
        json.dumps(split.to_dict(), indent=2), encoding="utf-8"
    )

    train_mask = split.mask(SPLIT_TRAIN)
    valid = valid_pixel_mask(cube)
    train_bg = train_mask & valid

    library, used_names, em_counts = build_train_endmember_library(
        cube,
        reference,
        class_names,
        wavelengths,
        train_mask,
        min_pixels=min_endmember_pixels,
        ignore_index=ignore,
        seed=seed,
    )
    write_library_csv(out / "train_library.csv", library)

    ref_remapped = remap_reference_to_names(
        reference, class_names, used_names, ignore_index=ignore
    )
    ref_test = mask_reference_to_split(ref_remapped, split, SPLIT_TEST, ignore_index=ignore)

    # Train labels: pure GT in train blocks among used classes
    train_labeled = train_mask & (ref_remapped != ignore) & valid
    train_coords = np.column_stack(np.where(train_labeled))
    y_all = ref_remapped[train_labeled].astype(np.int64)
    if y_all.size == 0:
        raise ValueError("no labeled train pixels for RF")

    pick = _cap_train_indices(
        y_all, max_per_class=max_train_samples_per_class, seed=seed + rf_seed
    )
    train_coords = train_coords[pick]
    y_train = y_all[pick]

    print(f"[ml_rf] fitting shared transforms for {fs} ...")
    mnf_cube, mf, infeas = _fit_shared_transforms(
        cube,
        library.spectra,
        train_bg,
        feature_set=fs,
        mnf_components=mnf_components,
        mtmf_seed=seed,
    )

    X_train, feat_meta_train = _gather_features(
        cube,
        wavelengths,
        train_coords,
        feature_set=fs,
        mnf_cube=mnf_cube,
        mf=mf,
        infeas=infeas,
    )

    clf = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        min_samples_leaf=min_samples_leaf,
        n_jobs=-1,
        random_state=rf_seed,
        class_weight="balanced_subsample",
    )
    print(f"[ml_rf] training RF on {X_train.shape[0]} samples × {X_train.shape[1]} feats ...")
    clf.fit(X_train, y_train)

    # Closed-set predict on all valid pixels
    valid_coords = np.column_stack(np.where(valid))
    print(f"[ml_rf] predicting {valid_coords.shape[0]} valid pixels ...")
    X_all, feat_meta_pred = _gather_features(
        cube,
        wavelengths,
        valid_coords,
        feature_set=fs,
        mnf_cube=mnf_cube,
        mf=mf,
        infeas=infeas,
    )
    pred_valid = clf.predict(X_all).astype(np.uint8)
    class_map = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
    class_map[valid_coords[:, 0], valid_coords[:, 1]] = pred_valid

    metrics = evaluate_maps(class_map, ref_test, used_names, ignore_index=ignore)
    metrics_d = metrics.to_dict()
    kao_r = _kaolinite_recall(metrics_d)

    labeled_train = int(train_labeled.sum())
    labeled_test = int((ref_test != ignore).sum())

    payload: dict[str, Any] = {
        **metrics_d,
        "method": f"rf_{fs}",
        "available": True,
        "kaolinite_recall": kao_r,
        "feature_meta": {"train": feat_meta_train, "predict": feat_meta_pred},
        "rf": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_leaf": min_samples_leaf,
            "rf_seed": rf_seed,
            "n_train_samples": int(y_train.shape[0]),
            "max_train_samples_per_class": max_train_samples_per_class,
            "classes_in_train": sorted(int(c) for c in np.unique(y_train)),
        },
        "provenance": {
            "benchmark": str(data["bench_dir"]),
            "split": "spatial_block",
            "score_region": "test_blocks_only",
            "library": "train-block pure GT endmembers",
            "endmember_counts": em_counts,
            "used_names": used_names,
            "labeled_test": labeled_test,
            "labeled_train": labeled_train,
            "n_row_blocks": n_row_blocks,
            "n_col_blocks": n_col_blocks,
            "seed": seed,
            "feature_set": fs,
            "mnf_components": mnf_components,
            "model": "RandomForestClassifier",
            "closed_set": True,
        },
    }
    (out / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_evaluation_artifacts(
        out / "eval",
        class_map,
        ref_test,
        used_names,
        ignore_index=ignore,
        extra_metrics=payload["provenance"],
    )
    np.save(out / "class_map.npy", class_map)

    summary = {
        "seed": seed,
        "feature_set": fs,
        "overall_accuracy": metrics.overall_accuracy,
        "kappa": metrics.kappa,
        "n_labeled": metrics.n_labeled,
        "n_correct": metrics.n_correct,
        "kaolinite_recall": kao_r,
        "used_names": used_names,
        "n_train_samples": int(y_train.shape[0]),
        "n_features": feat_meta_pred.get("n_features"),
        "output_dir": str(out),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
