"""Gradient boosting baselines on the same spatial-block protocol as RF.

Supports sklearn HistGradientBoostingClassifier (always if sklearn present)
and LightGBM when installed. Feature transforms match ml_rf (train-only).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .evaluate import UNKNOWN_CLASS, evaluate_maps, write_evaluation_artifacts
from .ml_rf import (
    FEATURE_SETS,
    _cap_train_indices,
    _fit_shared_transforms,
    _gather_features,
    _kaolinite_recall,
    _require_sklearn,
)
from .preprocessing import valid_pixel_mask
from .spatial_eval import (
    SPLIT_TEST,
    SPLIT_TRAIN,
    build_train_endmember_library,
    load_cuprite_benchmark,
    make_spatial_split,
    mask_reference_to_split,
    remap_reference_to_names,
    write_library_csv,
)

try:
    from sklearn.ensemble import HistGradientBoostingClassifier
except ImportError:  # pragma: no cover
    HistGradientBoostingClassifier = None  # type: ignore[misc, assignment]

try:
    import lightgbm as lgb
except ImportError:  # pragma: no cover
    lgb = None  # type: ignore[assignment]

BOOST_BACKENDS = ("hist", "lightgbm")


def _make_classifier(
    backend: str,
    *,
    n_estimators: int,
    max_depth: int | None,
    learning_rate: float,
    random_state: int,
    min_samples_leaf: int,
) -> Any:
    b = backend.strip().lower()
    if b in ("hist", "hgb", "sklearn"):
        _require_sklearn()
        if HistGradientBoostingClassifier is None:
            raise ImportError("HistGradientBoostingClassifier unavailable")
        # sklearn HGB uses max_iter trees; max_depth None → no limit via large int
        depth = 31 if max_depth is None else int(max_depth)
        return HistGradientBoostingClassifier(
            max_iter=n_estimators,
            max_depth=depth,
            learning_rate=learning_rate,
            min_samples_leaf=min_samples_leaf,
            random_state=random_state,
            class_weight="balanced",
        )
    if b in ("lightgbm", "lgbm", "lgb"):
        if lgb is None:
            raise ImportError(
                "lightgbm is required for backend=lightgbm. "
                "Install with: pip install lightgbm"
            )
        return lgb.LGBMClassifier(
            n_estimators=n_estimators,
            max_depth=-1 if max_depth is None else max_depth,
            learning_rate=learning_rate,
            num_leaves=31,
            min_child_samples=min_samples_leaf,
            class_weight="balanced",
            random_state=random_state,
            n_jobs=-1,
            verbosity=-1,
        )
    raise ValueError(f"unknown boost backend {backend!r}; choose from {BOOST_BACKENDS}")


def run_boost_spatial_seed(
    bench_dir: Path | str,
    output_dir: Path | str,
    *,
    seed: int = 42,
    feature_set: str = "mnf",
    backend: str = "hist",
    n_row_blocks: int = 4,
    n_col_blocks: int = 4,
    train_frac: float = 0.5,
    val_frac: float = 0.25,
    n_estimators: int = 200,
    max_depth: int | None = None,
    learning_rate: float = 0.1,
    min_samples_leaf: int = 20,
    model_seed: int = 0,
    mnf_components: int = 20,
    max_train_samples_per_class: int = 2000,
    min_endmember_pixels: int = 30,
) -> dict[str, Any]:
    """One spatial seed: train boosting on train pure GT, score test blocks."""
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

    train_labeled = train_mask & (ref_remapped != ignore) & valid
    train_coords = np.column_stack(np.where(train_labeled))
    y_all = ref_remapped[train_labeled].astype(np.int64)
    if y_all.size == 0:
        raise ValueError("no labeled train pixels for boosting")

    pick = _cap_train_indices(
        y_all, max_per_class=max_train_samples_per_class, seed=seed + model_seed
    )
    train_coords = train_coords[pick]
    y_train = y_all[pick]

    print(f"[ml_boost] fitting shared transforms for {fs} ...")
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

    clf = _make_classifier(
        backend,
        n_estimators=n_estimators,
        max_depth=max_depth,
        learning_rate=learning_rate,
        random_state=model_seed,
        min_samples_leaf=min_samples_leaf,
    )
    print(
        f"[ml_boost] training {backend} on {X_train.shape[0]} samples × "
        f"{X_train.shape[1]} feats ..."
    )
    clf.fit(X_train, y_train)

    valid_coords = np.column_stack(np.where(valid))
    print(f"[ml_boost] predicting {valid_coords.shape[0]} valid pixels ...")
    # Chunk prediction for memory
    class_map = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
    chunk = 65536
    n_feat_pred = 0
    for start in range(0, valid_coords.shape[0], chunk):
        end = min(start + chunk, valid_coords.shape[0])
        coords = valid_coords[start:end]
        X_chunk, feat_meta_pred = _gather_features(
            cube,
            wavelengths,
            coords,
            feature_set=fs,
            mnf_cube=mnf_cube,
            mf=mf,
            infeas=infeas,
        )
        n_feat_pred = int(feat_meta_pred.get("n_features", 0))
        pred = clf.predict(X_chunk).astype(np.uint8)
        class_map[coords[:, 0], coords[:, 1]] = pred

    metrics = evaluate_maps(class_map, ref_test, used_names, ignore_index=ignore)
    metrics_d = metrics.to_dict()
    kao_r = _kaolinite_recall(metrics_d)

    labeled_train = int(train_labeled.sum())
    labeled_test = int((ref_test != ignore).sum())
    method_name = f"boost_{backend}_{fs}"

    payload: dict[str, Any] = {
        **metrics_d,
        "method": method_name,
        "available": True,
        "kaolinite_recall": kao_r,
        "feature_meta": {"train": feat_meta_train, "n_features_predict": n_feat_pred},
        "boost": {
            "backend": backend,
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "min_samples_leaf": min_samples_leaf,
            "model_seed": model_seed,
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
            "model": method_name,
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
        "backend": backend,
        "method": method_name,
        "overall_accuracy": metrics.overall_accuracy,
        "kappa": metrics.kappa,
        "n_labeled": metrics.n_labeled,
        "n_correct": metrics.n_correct,
        "kaolinite_recall": kao_r,
        "used_names": used_names,
        "n_train_samples": int(y_train.shape[0]),
        "n_features": n_feat_pred or feat_meta_train.get("n_features"),
        "output_dir": str(out),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
