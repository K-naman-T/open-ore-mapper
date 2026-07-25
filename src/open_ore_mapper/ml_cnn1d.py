"""1D-CNN on spectra under spatial-block protocol (Hu-style spectral CNN).

Train only on train-block pure GT; evaluate test blocks via evaluate_maps.
Optional MNF-reduced spectrum when feature_mode='mnf'.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .evaluate import UNKNOWN_CLASS, evaluate_maps, write_evaluation_artifacts
from .ml_rf import (
    _cap_train_indices,
    _fit_shared_transforms,
    _kaolinite_recall,
)
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
)

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset
except ImportError:  # pragma: no cover
    torch = None  # type: ignore[assignment]
    nn = None  # type: ignore[assignment]
    DataLoader = None  # type: ignore[assignment]
    TensorDataset = None  # type: ignore[assignment]


def _require_torch() -> None:
    if torch is None or nn is None:
        raise ImportError(
            "PyTorch is required for 1D-CNN. Install with: pip install torch"
        )


class SpectralCNN1D(nn.Module if nn is not None else object):  # type: ignore[misc]
    """Small 1D CNN over spectral axis: (B, 1, C) → class logits."""

    def __init__(self, n_bands: int, n_classes: int, channels: int = 32) -> None:
        _require_torch()
        super().__init__()
        self.n_bands = n_bands
        self.n_classes = n_classes
        c = channels
        self.features = nn.Sequential(
            nn.Conv1d(1, c, kernel_size=7, padding=3),
            nn.BatchNorm1d(c),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(c, c * 2, kernel_size=5, padding=2),
            nn.BatchNorm1d(c * 2),
            nn.ReLU(inplace=True),
            nn.MaxPool1d(2),
            nn.Conv1d(c * 2, c * 2, kernel_size=3, padding=1),
            nn.BatchNorm1d(c * 2),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool1d(1),
        )
        self.head = nn.Linear(c * 2, n_classes)

    def forward(self, x: Any) -> Any:
        # x: (N, C) or (N, 1, C)
        if x.dim() == 2:
            x = x.unsqueeze(1)
        h = self.features(x).squeeze(-1)
        return self.head(h)


def train_cnn1d(
    X: NDArray[np.floating[Any]],
    y: NDArray[np.integer[Any]],
    n_classes: int,
    *,
    epochs: int = 25,
    batch_size: int = 256,
    lr: float = 1e-3,
    device: str | None = None,
    seed: int = 0,
    channels: int = 32,
) -> Any:
    """Fit SpectralCNN1D on (N, B) spectra and integer labels."""
    _require_torch()
    assert torch is not None and nn is not None
    rng_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    X = np.asarray(X, dtype=np.float32)
    y = np.asarray(y, dtype=np.int64)
    n_bands = X.shape[1]
    model = SpectralCNN1D(n_bands, n_classes, channels=channels).to(rng_device)

    # Class weights for imbalance
    counts = np.bincount(y, minlength=n_classes).astype(np.float64)
    weights = np.zeros(n_classes, dtype=np.float32)
    present = counts > 0
    weights[present] = float(counts[present].sum()) / (present.sum() * counts[present])
    w_t = torch.tensor(weights, dtype=torch.float32, device=rng_device)

    ds = TensorDataset(
        torch.from_numpy(X),
        torch.from_numpy(y),
    )
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True, drop_last=False)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.CrossEntropyLoss(weight=w_t)

    model.train()
    for ep in range(epochs):
        total = 0.0
        n = 0
        for xb, yb in loader:
            xb = xb.to(rng_device)
            yb = yb.to(rng_device)
            opt.zero_grad(set_to_none=True)
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            total += float(loss.item()) * xb.shape[0]
            n += xb.shape[0]
        if (ep + 1) % max(1, epochs // 5) == 0 or ep == 0:
            print(f"[ml_cnn1d] epoch {ep + 1}/{epochs} loss={total / max(n, 1):.4f}")
    model.eval()
    return model


def predict_cnn1d(
    model: Any,
    X: NDArray[np.floating[Any]],
    *,
    batch_size: int = 4096,
    device: str | None = None,
) -> NDArray[np.uint8]:
    _require_torch()
    assert torch is not None
    rng_device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(rng_device)
    model.eval()
    X = np.asarray(X, dtype=np.float32)
    out = np.empty(X.shape[0], dtype=np.uint8)
    with torch.no_grad():
        for start in range(0, X.shape[0], batch_size):
            end = min(start + batch_size, X.shape[0])
            xb = torch.from_numpy(X[start:end]).to(rng_device)
            logits = model(xb)
            pred = logits.argmax(dim=1).cpu().numpy().astype(np.uint8)
            out[start:end] = pred
    return out


def _spectra_for_coords(
    cube: NDArray[np.float32],
    coords: NDArray[np.integer[Any]],
    *,
    feature_mode: str,
    mnf_cube: NDArray[np.float32] | None,
) -> NDArray[np.float32]:
    rr, cc = coords[:, 0], coords[:, 1]
    mode = feature_mode.strip().lower()
    if mode == "reflectance":
        X = cube[rr, cc, :].astype(np.float32)
    elif mode == "mnf":
        if mnf_cube is None:
            raise ValueError("mnf_cube required for feature_mode=mnf")
        X = mnf_cube[rr, cc, :].astype(np.float32)
    else:
        raise ValueError(f"unknown feature_mode {feature_mode!r}; use reflectance or mnf")
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


def run_cnn1d_spatial_seed(
    bench_dir: Path | str,
    output_dir: Path | str,
    *,
    seed: int = 42,
    feature_mode: str = "mnf",
    n_row_blocks: int = 4,
    n_col_blocks: int = 4,
    train_frac: float = 0.5,
    val_frac: float = 0.25,
    mnf_components: int = 30,
    max_train_samples_per_class: int = 2000,
    min_endmember_pixels: int = 30,
    epochs: int = 20,
    batch_size: int = 256,
    lr: float = 1e-3,
    model_seed: int = 0,
    channels: int = 32,
    device: str | None = None,
) -> dict[str, Any]:
    """One spatial seed: train 1D-CNN on train pure GT spectra, score test blocks."""
    _require_torch()
    mode = feature_mode.strip().lower()
    if mode not in ("reflectance", "mnf"):
        raise ValueError("feature_mode must be 'reflectance' or 'mnf'")

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
        raise ValueError("no labeled train pixels for cnn1d")

    pick = _cap_train_indices(
        y_all, max_per_class=max_train_samples_per_class, seed=seed + model_seed
    )
    train_coords = train_coords[pick]
    y_train = y_all[pick]
    n_classes = len(used_names)

    mnf_cube = None
    if mode == "mnf":
        print(f"[ml_cnn1d] fitting MNF (n={mnf_components}) on train blocks ...")
        mnf_cube, _ = mnf_transform(
            cube, n_components=mnf_components, sample_mask=train_bg
        )

    X_train = _spectra_for_coords(
        cube, train_coords, feature_mode=mode, mnf_cube=mnf_cube
    )
    print(
        f"[ml_cnn1d] training 1D-CNN on {X_train.shape[0]} × {X_train.shape[1]} "
        f"mode={mode} epochs={epochs} ..."
    )
    model = train_cnn1d(
        X_train,
        y_train,
        n_classes,
        epochs=epochs,
        batch_size=batch_size,
        lr=lr,
        device=device,
        seed=model_seed,
        channels=channels,
    )

    valid_coords = np.column_stack(np.where(valid))
    print(f"[ml_cnn1d] predicting {valid_coords.shape[0]} valid pixels ...")
    class_map = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
    chunk = 32768
    for start in range(0, valid_coords.shape[0], chunk):
        end = min(start + chunk, valid_coords.shape[0])
        coords = valid_coords[start:end]
        X = _spectra_for_coords(cube, coords, feature_mode=mode, mnf_cube=mnf_cube)
        pred = predict_cnn1d(model, X, batch_size=4096, device=device)
        class_map[coords[:, 0], coords[:, 1]] = pred

    metrics = evaluate_maps(class_map, ref_test, used_names, ignore_index=ignore)
    metrics_d = metrics.to_dict()
    kao_r = _kaolinite_recall(metrics_d)

    method_name = f"cnn1d_{mode}"
    labeled_train = int(train_labeled.sum())
    labeled_test = int((ref_test != ignore).sum())
    dev = device or ("cuda" if torch is not None and torch.cuda.is_available() else "cpu")

    payload: dict[str, Any] = {
        **metrics_d,
        "method": method_name,
        "available": True,
        "kaolinite_recall": kao_r,
        "cnn1d": {
            "feature_mode": mode,
            "epochs": epochs,
            "batch_size": batch_size,
            "lr": lr,
            "channels": channels,
            "model_seed": model_seed,
            "n_train_samples": int(y_train.shape[0]),
            "n_bands": int(X_train.shape[1]),
            "device": dev,
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
            "feature_mode": mode,
            "mnf_components": mnf_components if mode == "mnf" else None,
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

    # Save lightweight state dict for inspection
    try:
        assert torch is not None
        torch.save(
            {"state_dict": model.state_dict(), "n_bands": X_train.shape[1], "n_classes": n_classes},
            out / "model.pt",
        )
    except Exception:  # noqa: BLE001
        pass

    summary = {
        "seed": seed,
        "feature_mode": mode,
        "method": method_name,
        "overall_accuracy": metrics.overall_accuracy,
        "kappa": metrics.kappa,
        "n_labeled": metrics.n_labeled,
        "n_correct": metrics.n_correct,
        "kaolinite_recall": kao_r,
        "used_names": used_names,
        "n_train_samples": int(y_train.shape[0]),
        "n_bands": int(X_train.shape[1]),
        "device": dev,
        "output_dir": str(out),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
