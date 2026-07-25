"""Compare a predicted mineral class map against a reference / ROI mask."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from PIL import Image

UNKNOWN_CLASS = 255

# Diff colors (RGB)
DIFF_MATCH = (34, 139, 34)  # green
DIFF_MISMATCH = (178, 34, 34)  # red
DIFF_OURS_UNKNOWN = (255, 140, 0)  # orange — reference labeled, we said unknown
DIFF_IGNORE = (40, 40, 40)  # dark gray — unlabeled / ignored


@dataclass(frozen=True)
class ClassMetrics:
    name: str
    precision: float
    recall: float
    f1: float
    support: int  # reference pixel count
    predicted: int


@dataclass(frozen=True)
class EvaluationResult:
    overall_accuracy: float
    kappa: float
    n_labeled: int
    n_correct: int
    per_class: list[ClassMetrics]
    confusion: list[list[int]]  # rows = reference, cols = predicted (aligned to class_names)
    class_names: list[str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_accuracy": self.overall_accuracy,
            "kappa": self.kappa,
            "n_labeled": self.n_labeled,
            "n_correct": self.n_correct,
            "per_class": [asdict(c) for c in self.per_class],
            "confusion": self.confusion,
            "class_names": self.class_names,
            "warnings": list(self.warnings),
        }


def evaluate_maps(
    predicted: NDArray[np.integer[Any]],
    reference: NDArray[np.integer[Any]],
    class_names: list[str],
    *,
    ignore_index: int = UNKNOWN_CLASS,
) -> EvaluationResult:
    """Compute OA, kappa, per-class P/R, confusion on labeled reference pixels only."""
    if predicted.shape != reference.shape:
        raise ValueError(
            f"predicted shape {predicted.shape} != reference shape {reference.shape}"
        )
    if not class_names:
        raise ValueError("class_names must be non-empty")

    pred = np.asarray(predicted)
    ref = np.asarray(reference)
    n_classes = len(class_names)

    labeled = ref != ignore_index
    n_labeled = int(labeled.sum())
    if n_labeled == 0:
        empty = [
            ClassMetrics(name=n, precision=0.0, recall=0.0, f1=0.0, support=0, predicted=0)
            for n in class_names
        ]
        return EvaluationResult(
            overall_accuracy=0.0,
            kappa=0.0,
            n_labeled=0,
            n_correct=0,
            per_class=empty,
            confusion=[[0] * n_classes for _ in range(n_classes)],
            class_names=list(class_names),
            warnings=["No labeled reference pixels to evaluate"],
        )

    pred_l = pred[labeled].astype(np.int64)
    ref_l = ref[labeled].astype(np.int64)

    # Clamp invalid predicted labels outside [0, n_classes) to a mismatch bucket:
    # treat as wrong (not matching any class) for OA — count as incorrect.
    valid_pred = (pred_l >= 0) & (pred_l < n_classes)
    correct_mask = valid_pred & (pred_l == ref_l)
    n_correct = int(correct_mask.sum())
    oa = float(n_correct / n_labeled)

    confusion = np.zeros((n_classes, n_classes), dtype=np.int64)
    for r, p in zip(ref_l, pred_l, strict=False):
        if 0 <= r < n_classes and 0 <= p < n_classes:
            confusion[r, p] += 1
        # predicted unknown or OOB: no column credit; still counts as labeled error via OA

    per_class: list[ClassMetrics] = []
    for i, name in enumerate(class_names):
        support = int((ref_l == i).sum())
        predicted_count = int(((pred_l == i) & valid_pred).sum())
        tp = int(confusion[i, i])
        precision = float(tp / predicted_count) if predicted_count > 0 else 0.0
        recall = float(tp / support) if support > 0 else 0.0
        f1 = (
            float(2 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )
        per_class.append(
            ClassMetrics(
                name=name,
                precision=precision,
                recall=recall,
                f1=f1,
                support=support,
                predicted=predicted_count,
            )
        )

    kappa = _cohen_kappa(confusion, n_labeled)
    return EvaluationResult(
        overall_accuracy=oa,
        kappa=kappa,
        n_labeled=n_labeled,
        n_correct=n_correct,
        per_class=per_class,
        confusion=confusion.tolist(),
        class_names=list(class_names),
        warnings=[],
    )


def _cohen_kappa(confusion: NDArray[np.integer[Any]], n: int) -> float:
    if n <= 0:
        return 0.0
    po = float(np.trace(confusion) / n)
    row_m = confusion.sum(axis=1).astype(np.float64)
    col_m = confusion.sum(axis=0).astype(np.float64)
    pe = float(np.dot(row_m, col_m) / (n * n))
    if abs(1.0 - pe) < 1e-12:
        return 0.0
    return float((po - pe) / (1.0 - pe))


def render_diff_rgb(
    predicted: NDArray[np.integer[Any]],
    reference: NDArray[np.integer[Any]],
    *,
    ignore_index: int = UNKNOWN_CLASS,
) -> NDArray[np.uint8]:
    """Green=match, red=mismatch, orange=ref labeled & pred unknown, gray=ignored."""
    pred = np.asarray(predicted)
    ref = np.asarray(reference)
    h, w = ref.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    rgb[:] = DIFF_IGNORE

    labeled = ref != ignore_index
    match = labeled & (pred == ref)
    pred_unknown = labeled & (pred == ignore_index)
    mismatch = labeled & ~match & ~pred_unknown

    rgb[match] = DIFF_MATCH
    rgb[mismatch] = DIFF_MISMATCH
    rgb[pred_unknown] = DIFF_OURS_UNKNOWN
    return rgb


def class_map_to_rgb(
    class_map: NDArray[np.integer[Any]],
    n_classes: int,
    *,
    ignore_index: int = UNKNOWN_CLASS,
) -> NDArray[np.uint8]:
    """Simple distinct palette for class maps (shared order for our vs reference)."""
    # Deterministic palette (not requiring rendering.CLASS_COLORS import cycle)
    palette = np.array(
        [
            [177, 56, 36],
            [214, 117, 39],
            [231, 178, 57],
            [82, 84, 91],
            [136, 92, 48],
            [194, 134, 79],
            [78, 126, 153],
            [78, 153, 116],
            [119, 92, 163],
            [181, 77, 122],
            [108, 111, 61],
            [60, 140, 180],
        ],
        dtype=np.uint8,
    )
    unknown = np.array([20, 20, 20], dtype=np.uint8)
    rgb = np.zeros((*class_map.shape, 3), dtype=np.uint8)
    rgb[:] = unknown
    for idx in range(n_classes):
        rgb[class_map == idx] = palette[idx % len(palette)]
    rgb[class_map == ignore_index] = unknown
    return rgb


def write_png(path: Path, rgb: NDArray[np.uint8]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb.astype(np.uint8)).save(path, format="PNG")


def write_evaluation_artifacts(
    output_dir: Path | str,
    predicted: NDArray[np.integer[Any]],
    reference: NDArray[np.integer[Any]],
    class_names: list[str],
    *,
    ignore_index: int = UNKNOWN_CLASS,
    extra_metrics: dict[str, Any] | None = None,
) -> EvaluationResult:
    """Evaluate and write metrics.json, confusion.csv, our/reference/diff PNGs, report.md."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result = evaluate_maps(
        predicted, reference, class_names, ignore_index=ignore_index
    )
    payload = result.to_dict()
    if extra_metrics:
        payload["provenance"] = extra_metrics
    (out / "metrics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with (out / "confusion.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["ref\\pred"] + class_names)
        for i, name in enumerate(class_names):
            writer.writerow([name] + result.confusion[i])

    n = len(class_names)
    write_png(out / "our_class.png", class_map_to_rgb(predicted, n, ignore_index=ignore_index))
    write_png(
        out / "reference.png", class_map_to_rgb(reference, n, ignore_index=ignore_index)
    )
    write_png(
        out / "diff.png",
        render_diff_rgb(predicted, reference, ignore_index=ignore_index),
    )

    framing = ""
    if extra_metrics:
        if extra_metrics.get("metric_framing") == "map_to_map_agreement" or extra_metrics.get(
            "not_field_truth"
        ):
            framing = (
                "\n> **Framing:** numbers are **map-to-map agreement** with the reference labels "
                "(e.g. Tetracorder), **not** field mineral truth and **not** ore proof.\n"
            )
        if extra_metrics.get("external_classical_bar"):
            framing += f"\n> External classical bar (if cited): {extra_metrics['external_classical_bar']}\n"

    lines = [
        "# Evaluation report",
        "",
        framing.strip(),
        "",
        f"- Overall agreement (OA): **{result.overall_accuracy:.4f}**",
        f"- Cohen's kappa: **{result.kappa:.4f}**",
        f"- Labeled pixels: {result.n_labeled} (correct: {result.n_correct})",
        "",
        "## Per-class",
        "",
        "| Class | Precision | Recall | F1 | Support |",
        "|-------|-----------|--------|----|---------|",
    ]
    for c in result.per_class:
        lines.append(
            f"| {c.name} | {c.precision:.3f} | {c.recall:.3f} | {c.f1:.3f} | {c.support} |"
        )
    lines.extend(
        [
            "",
            "Artifacts: `our_class.png`, `reference.png`, `diff.png`, `confusion.csv`.",
        ]
    )
    if extra_metrics:
        lines.extend(["", "## Provenance", ""])
        for k, v in extra_metrics.items():
            if k == "warnings":
                continue
            lines.append(f"- **{k}:** {v}")
    if result.warnings:
        lines.append("")
        lines.append("Warnings: " + "; ".join(result.warnings))
    if extra_metrics and extra_metrics.get("warnings"):
        w = extra_metrics["warnings"]
        if isinstance(w, list) and w:
            lines.append("")
            lines.append("Pipeline warnings: " + "; ".join(str(x) for x in w))
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def load_class_map_png(path: Path | str) -> NDArray[np.uint8]:
    """Load a single-channel or RGB class index PNG (grayscale preferred)."""
    img = Image.open(path)
    arr = np.array(img)
    if arr.ndim == 3:
        # take first channel as class id if already indexed palette-like
        arr = arr[:, :, 0]
    return arr.astype(np.uint8)


def rasterize_rois(
    height: int,
    width: int,
    rois: list[dict[str, Any]],
    name_to_index: dict[str, int],
    *,
    ignore_index: int = UNKNOWN_CLASS,
) -> NDArray[np.uint8]:
    """Rasterize axis-aligned ROI boxes: {mineral, row0, row1, col0, col1}."""
    ref = np.full((height, width), ignore_index, dtype=np.uint8)
    for roi in rois:
        name = str(roi["mineral"])
        if name not in name_to_index:
            raise ValueError(f"ROI mineral '{name}' not in legend/class names")
        idx = name_to_index[name]
        r0, r1 = int(roi["row0"]), int(roi["row1"])
        c0, c1 = int(roi["col0"]), int(roi["col1"])
        ref[r0:r1, c0:c1] = idx
    return ref
