"""Spatial block train/val/test evaluation for hyperspectral mineral maps.

Prevents leakage from scene-derived endmembers by building libraries only from
train-block pure GT pixels, then scoring predictions on test-block pixels only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import tifffile
from numpy.typing import NDArray

from .evaluate import UNKNOWN_CLASS, EvaluationResult, evaluate_maps, write_evaluation_artifacts
from .preprocessing import normalize_cube, select_bands, valid_pixel_mask
from .qc import analyze_raster_quality
from .sam import compute_sam_angles
from .schemas import MapperOptions
from .service import OreMapper
from .spectral_library import SpectralLibrary

SPLIT_TRAIN = 0
SPLIT_VAL = 1
SPLIT_TEST = 2
SPLIT_NAMES = {SPLIT_TRAIN: "train", SPLIT_VAL: "val", SPLIT_TEST: "test"}


@dataclass(frozen=True)
class SpatialSplit:
    """Block-level spatial partition of a scene."""

    n_row_blocks: int
    n_col_blocks: int
    seed: int
    block_id: NDArray[np.int32]  # (H, W) block index 0..n_blocks-1
    split_id: NDArray[np.uint8]  # (H, W) train/val/test
    block_to_split: list[int]  # length n_blocks
    row_edges: list[int]
    col_edges: list[int]

    @property
    def n_blocks(self) -> int:
        return self.n_row_blocks * self.n_col_blocks

    def mask(self, split: int) -> NDArray[np.bool_]:
        return self.split_id == split

    def to_dict(self) -> dict[str, Any]:
        counts = {
            name: int((self.split_id == sid).sum())
            for sid, name in SPLIT_NAMES.items()
        }
        block_assign = {
            str(i): SPLIT_NAMES[s] for i, s in enumerate(self.block_to_split)
        }
        return {
            "n_row_blocks": self.n_row_blocks,
            "n_col_blocks": self.n_col_blocks,
            "n_blocks": self.n_blocks,
            "seed": self.seed,
            "row_edges": list(self.row_edges),
            "col_edges": list(self.col_edges),
            "block_to_split": block_assign,
            "pixel_counts": counts,
            "train_blocks": [i for i, s in enumerate(self.block_to_split) if s == SPLIT_TRAIN],
            "val_blocks": [i for i, s in enumerate(self.block_to_split) if s == SPLIT_VAL],
            "test_blocks": [i for i, s in enumerate(self.block_to_split) if s == SPLIT_TEST],
        }


@dataclass
class MethodResult:
    method: str
    metrics: EvaluationResult
    class_map: NDArray[np.uint8]
    available: bool = True
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def metrics_dict(self) -> dict[str, Any]:
        d = self.metrics.to_dict()
        d["method"] = self.method
        d["available"] = self.available
        if self.notes:
            d["notes"] = self.notes
        if self.extra:
            d["extra"] = self.extra
        return d


def make_spatial_split(
    height: int,
    width: int,
    *,
    n_row_blocks: int = 4,
    n_col_blocks: int = 4,
    train_frac: float = 0.5,
    val_frac: float = 0.25,
    seed: int = 42,
) -> SpatialSplit:
    """Partition a (H,W) grid into row×col blocks and assign blocks to splits.

    Assignment is by BLOCK (not pixel). Fractions are applied to the block count
    with a fixed RNG seed for reproducibility.
    """
    if n_row_blocks < 1 or n_col_blocks < 1:
        raise ValueError("n_row_blocks and n_col_blocks must be >= 1")
    if height < n_row_blocks or width < n_col_blocks:
        raise ValueError("scene smaller than requested block grid")
    if train_frac <= 0 or train_frac >= 1:
        raise ValueError("train_frac must be in (0, 1)")
    if val_frac < 0 or train_frac + val_frac >= 1:
        raise ValueError("val_frac must be >= 0 and train_frac + val_frac < 1")

    row_edges = [int(round(i * height / n_row_blocks)) for i in range(n_row_blocks + 1)]
    col_edges = [int(round(i * width / n_col_blocks)) for i in range(n_col_blocks + 1)]
    row_edges[0], row_edges[-1] = 0, height
    col_edges[0], col_edges[-1] = 0, width

    n_blocks = n_row_blocks * n_col_blocks
    block_id = np.full((height, width), -1, dtype=np.int32)
    for br in range(n_row_blocks):
        for bc in range(n_col_blocks):
            bid = br * n_col_blocks + bc
            r0, r1 = row_edges[br], row_edges[br + 1]
            c0, c1 = col_edges[bc], col_edges[bc + 1]
            block_id[r0:r1, c0:c1] = bid

    n_train = max(1, int(round(n_blocks * train_frac)))
    n_val = max(0, int(round(n_blocks * val_frac)))
    n_test = n_blocks - n_train - n_val
    if n_test < 1:
        # steal one block from train
        n_train = max(1, n_train - 1)
        n_test = n_blocks - n_train - n_val
    if n_test < 1:
        raise ValueError("need at least one test block; reduce train/val fractions")

    rng = np.random.default_rng(seed)
    order = rng.permutation(n_blocks)
    block_to_split = [SPLIT_TRAIN] * n_blocks
    for i, bid in enumerate(order):
        if i < n_train:
            block_to_split[int(bid)] = SPLIT_TRAIN
        elif i < n_train + n_val:
            block_to_split[int(bid)] = SPLIT_VAL
        else:
            block_to_split[int(bid)] = SPLIT_TEST

    split_id = np.zeros((height, width), dtype=np.uint8)
    for bid, sid in enumerate(block_to_split):
        split_id[block_id == bid] = sid

    return SpatialSplit(
        n_row_blocks=n_row_blocks,
        n_col_blocks=n_col_blocks,
        seed=seed,
        block_id=block_id,
        split_id=split_id,
        block_to_split=block_to_split,
        row_edges=row_edges,
        col_edges=col_edges,
    )


def build_train_endmember_library(
    cube: NDArray[np.floating[Any]],
    reference: NDArray[np.integer[Any]],
    class_names: list[str],
    wavelengths: list[float],
    train_mask: NDArray[np.bool_],
    *,
    min_pixels: int = 30,
    ignore_index: int = UNKNOWN_CLASS,
    seed: int = 0,
) -> tuple[SpectralLibrary, list[str], dict[str, int]]:
    """Median endmember per class from pure GT pixels inside train blocks only.

    Returns (library, used_names, pixel_counts_used). Classes with too few train
    pure pixels are dropped.
    """
    if cube.ndim != 3:
        raise ValueError("cube must be HWC")
    if reference.shape != cube.shape[:2]:
        raise ValueError("reference shape must match cube spatial dims")
    if train_mask.shape != cube.shape[:2]:
        raise ValueError("train_mask shape must match cube spatial dims")

    used_names: list[str] = []
    spectra_rows: list[NDArray[np.float32]] = []
    counts: dict[str, int] = {}
    wl = np.asarray(wavelengths, dtype=np.float32)

    for idx, name in enumerate(class_names):
        mask = train_mask & (reference == idx) & (reference != ignore_index)
        n = int(mask.sum())
        if n < min_pixels:
            counts[name] = 0
            continue
        coords = np.column_stack(np.where(mask))
        means = cube[mask].mean(axis=1)
        ok_m = np.isfinite(means) & (means > 0.05) & (means < 1.2)
        coords = coords[ok_m]
        means = means[ok_m]
        if len(coords) < min_pixels:
            counts[name] = 0
            continue
        lo, hi = np.percentile(means, [20, 80])
        mid = (means >= lo) & (means <= hi)
        if int(mid.sum()) >= min_pixels:
            coords = coords[mid]
            means = means[mid]
        # Stable seed (avoid PYTHONHASHSEED / randomized hash())
        name_key = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed + (name_key % (2**20)))
        if len(coords) > 800:
            pick = rng.choice(len(coords), 800, replace=False)
            coords = coords[pick]
        specs = cube[coords[:, 0], coords[:, 1], :]
        ok = np.isfinite(specs).all(axis=1) & (specs.max(axis=1) > 0.05)
        specs = specs[ok]
        if specs.shape[0] < min_pixels:
            counts[name] = 0
            continue
        end = np.median(specs, axis=0).astype(np.float32)
        end = np.clip(end, 0.001, 1.5)
        used_names.append(name)
        spectra_rows.append(end)
        counts[name] = int(specs.shape[0])

    if not used_names:
        raise ValueError("no train-block pure pixels for any class; cannot build library")

    spectra = np.stack(spectra_rows, axis=0).astype(np.float32)
    library = SpectralLibrary(
        names=used_names,
        wavelengths=wl,
        spectra=spectra,
        source="train-block scene endmembers (median pure GT pixels)",
        is_authoritative=False,
    )
    return library, used_names, counts


def write_library_csv(
    path: Path | str,
    library: SpectralLibrary,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["name,wavelength,reflectance"]
    for i, name in enumerate(library.names):
        for w, v in zip(library.wavelengths, library.spectra[i], strict=True):
            lines.append(f"{name},{float(w):.2f},{float(v):.6f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def remap_reference_to_names(
    reference: NDArray[np.integer[Any]],
    old_names: list[str],
    new_names: list[str],
    *,
    ignore_index: int = UNKNOWN_CLASS,
) -> NDArray[np.uint8]:
    """Remap class indices from old_names order to new_names order."""
    name_to_new = {n: i for i, n in enumerate(new_names)}
    out = np.full(reference.shape, ignore_index, dtype=np.uint8)
    for old_i, name in enumerate(old_names):
        if name not in name_to_new:
            continue
        out[reference == old_i] = name_to_new[name]
    return out


def mask_reference_to_split(
    reference: NDArray[np.integer[Any]],
    split: SpatialSplit,
    split_kind: int,
    *,
    ignore_index: int = UNKNOWN_CLASS,
) -> NDArray[np.uint8]:
    """Keep labels only on the requested split; elsewhere → ignore_index."""
    ref = np.asarray(reference, dtype=np.uint8).copy()
    ref[~split.mask(split_kind)] = ignore_index
    return ref


def classify_oremapper(
    cube: NDArray[np.floating[Any]],
    wavelengths: list[float],
    library_csv: Path | str,
    minerals: list[str],
    *,
    classifier: str = "continuum_removal",
    sam_threshold_deg: float = 12.0,
    min_confidence: float = 0.50,
    tile_size: int = 128,
    normalization: str = "l2",
    min_band_valid_fraction: float = 0.3,
) -> tuple[NDArray[np.uint8], list[str], list[str]]:
    """Run shipped OreMapper._classify_core; returns (class_map, names, warnings)."""
    opts = MapperOptions(
        wavelengths=list(wavelengths),
        sensor="manual",
        minerals=list(minerals),
        spectral_library=str(library_csv),
        min_confidence=min_confidence,
        sam_threshold_deg=sam_threshold_deg,
        tile_size=tile_size,
        normalization=normalization,
        classifier=classifier,
        min_band_valid_fraction=min_band_valid_fraction,
    )
    om = OreMapper()
    report = analyze_raster_quality(
        cube,
        wavelengths,
        min_band_valid_fraction=min_band_valid_fraction,
    )
    cube_f, retained = select_bands(cube, wavelengths, report.retained_band_indices)
    library = om._load_library(opts, retained)
    class_map, _conf, _ab = om._classify_core(cube_f, retained, library, opts)
    warnings = list(report.warnings)
    effective = om._effective_classifier(classifier)
    requested = classifier.strip().lower().replace(" ", "_")
    if requested == "cr_sam":
        requested = "continuum_removal"
    if effective != requested:
        warnings.append(f"classifier {classifier!r} ran as {effective!r}")
    return class_map.astype(np.uint8), list(library.names), warnings


def classify_mtmf_hard(
    cube: NDArray[np.floating[Any]],
    library: SpectralLibrary,
    *,
    background_mask: NDArray[np.bool_] | None = None,
    mf_threshold: float = 0.3,
    infeas_threshold: float = 15.0,
    seed: int = 42,
) -> NDArray[np.uint8]:
    """Hard multi-class map from MTMF: argmax MF among feasible detections."""
    valid = valid_pixel_mask(cube)
    bg = background_mask & valid if background_mask is not None else valid
    # Deterministic background subsample (mtmf.estimate_background_stats is unseeded)
    mf, infeas = _mtmf_seeded(
        cube.astype(np.float32),
        library.spectra.astype(np.float32),
        valid_mask=bg,
        seed=seed,
    )

    h, w, k = mf.shape
    class_map = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
    # only consider pixels that pass detection for at least one target
    feasible = (mf >= mf_threshold) & (infeas <= infeas_threshold) & valid[..., None]
    # set infeasible scores to -inf so they lose argmax
    scores = np.where(feasible, mf, -np.inf)
    best = np.argmax(scores, axis=2).astype(np.uint8)
    best_score = np.max(scores, axis=2)
    accept = np.isfinite(best_score) & (best_score > -np.inf)
    class_map[accept] = best[accept]
    return class_map


def _mtmf_seeded(
    cube: NDArray[np.float32],
    targets: NDArray[np.float32],
    *,
    valid_mask: NDArray[np.bool_],
    seed: int = 42,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """MTMF with deterministic background covariance subsample."""
    h, w, b = cube.shape
    pixels = cube[valid_mask].reshape(-1, b)
    n = pixels.shape[0]
    rng = np.random.default_rng(seed)
    if n > 5000:
        sampled = pixels[rng.choice(n, size=5000, replace=False)]
    else:
        sampled = pixels
    sampled_64 = np.asarray(sampled, dtype=np.float64)
    mean = np.mean(sampled_64, axis=0)
    cov = np.cov(sampled_64, rowvar=False)
    cond = np.linalg.cond(cov)
    epsilon = 1e-4 * np.trace(cov)
    cov_reg = cov + epsilon * np.eye(b, dtype=np.float64) if cond > 1e4 else cov
    inv_cov = np.linalg.pinv(cov_reg)

    # Inline MTMF using fixed mean/inv_cov (same math as mtmf.mtmf)
    k = targets.shape[0]
    flat = cube.reshape(-1, b)
    z = np.asarray(flat, dtype=np.float64) - mean[np.newaxis, :]
    t = np.asarray(targets, dtype=np.float64) - mean[np.newaxis, :]
    z_inv = z @ inv_cov
    mahalanobis2 = np.sum(z_inv * z, axis=1)
    mf_flat = np.zeros((z.shape[0], k), dtype=np.float64)
    infeas_flat = np.zeros((z.shape[0], k), dtype=np.float64)
    for ki in range(k):
        d = t[ki]
        denom = float(d @ inv_cov @ d)
        if abs(denom) < 1e-18:
            continue
        wvec = inv_cov @ d / denom
        mf_k = z @ wvec
        mf_flat[:, ki] = mf_k
        infeas_flat[:, ki] = np.sqrt(np.maximum(0.0, mahalanobis2 - mf_k**2 * denom))
    return (
        mf_flat.reshape(h, w, k).astype(np.float32),
        infeas_flat.reshape(h, w, k).astype(np.float32),
    )


def _estimate_noise_covariance(cube: NDArray[np.floating[Any]], max_pairs: int = 20000) -> NDArray[np.float64]:
    """Adjacent-pixel difference noise covariance (classic MNF noise estimate)."""
    h, w, b = cube.shape
    # horizontal diffs
    dh = cube[:, 1:, :] - cube[:, :-1, :]
    dv = cube[1:, :, :] - cube[:-1, :, :]
    samples = np.concatenate(
        [dh.reshape(-1, b), dv.reshape(-1, b)],
        axis=0,
    )
    finite = np.isfinite(samples).all(axis=1)
    samples = samples[finite]
    if samples.shape[0] > max_pairs:
        rng = np.random.default_rng(0)
        samples = samples[rng.choice(samples.shape[0], max_pairs, replace=False)]
    if samples.shape[0] < b + 2:
        return np.eye(b, dtype=np.float64)
    # noise ~ half variance of differences
    cov = np.cov(samples.T) / 2.0
    cov = cov + 1e-6 * np.eye(b)
    return cov.astype(np.float64)


def mnf_transform(
    cube: NDArray[np.floating[Any]],
    *,
    n_components: int = 20,
    sample_mask: NDArray[np.bool_] | None = None,
) -> tuple[NDArray[np.float32], NDArray[np.float64]]:
    """Minimum Noise Fraction projection (Green et al.).

    Returns (transformed cube HxWxC, projection matrix BandsxC).
    """
    h, w, b = cube.shape
    flat = cube.reshape(-1, b).astype(np.float64)
    if sample_mask is not None:
        sel = sample_mask.reshape(-1)
        data = flat[sel]
    else:
        data = flat[np.isfinite(flat).all(axis=1)]
    if data.shape[0] < b + 5:
        raise ValueError("not enough samples for MNF")

    # subsample for speed
    if data.shape[0] > 30000:
        rng = np.random.default_rng(1)
        data = data[rng.choice(data.shape[0], 30000, replace=False)]

    noise_cov = _estimate_noise_covariance(cube)
    # whiten by noise: noise_cov^{-1/2}
    eigval_n, eigvec_n = np.linalg.eigh(noise_cov)
    eigval_n = np.maximum(eigval_n, 1e-10)
    w_noise = eigvec_n @ np.diag(1.0 / np.sqrt(eigval_n)) @ eigvec_n.T

    mean = data.mean(axis=0)
    centered = data - mean
    whitened = centered @ w_noise
    sig_cov = np.cov(whitened.T)
    eigval_s, eigvec_s = np.linalg.eigh(sig_cov)
    # largest variance first (signal)
    order = np.argsort(eigval_s)[::-1]
    n_components = min(n_components, b)
    evecs = eigvec_s[:, order[:n_components]]
    # full projection: x -> (x - mean) @ w_noise @ evecs
    proj = w_noise @ evecs  # B x C

    out = ((flat - mean) @ proj).reshape(h, w, n_components).astype(np.float32)
    return out, proj.astype(np.float64)


def classify_mnf_sam(
    cube: NDArray[np.floating[Any]],
    library: SpectralLibrary,
    *,
    n_components: int = 20,
    sample_mask: NDArray[np.bool_] | None = None,
    sam_threshold_deg: float = 12.0,
    min_strength: float = 0.50,
) -> NDArray[np.uint8]:
    """SAM in MNF space using train-derived endmembers projected with same MNF."""
    mnf_cube, proj = mnf_transform(cube, n_components=n_components, sample_mask=sample_mask)
    # project library: need same mean — recompute mean from sample
    h, w, b = cube.shape
    flat = cube.reshape(-1, b).astype(np.float64)
    if sample_mask is not None:
        mean = flat[sample_mask.reshape(-1)].mean(axis=0)
    else:
        mean = flat[np.isfinite(flat).all(axis=1)].mean(axis=0)
    refs = ((library.spectra.astype(np.float64) - mean) @ proj).astype(np.float32)

    valid = valid_pixel_mask(cube)
    # L2 normalize in MNF space for SAM
    pix = mnf_cube.reshape(-1, mnf_cube.shape[2])
    refs_n = normalize_cube(refs[np.newaxis, :, :], "l2")[0]
    pix_n = pix / np.maximum(np.linalg.norm(pix, axis=1, keepdims=True), 1e-10)

    class_map = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
    flat_valid = valid.reshape(-1)
    if not np.any(flat_valid):
        return class_map
    angles = compute_sam_angles(pix_n[flat_valid], refs_n)
    best_idx = np.argmin(angles, axis=1).astype(np.uint8)
    best_ang = np.min(angles, axis=1)
    strength = np.clip(1.0 - best_ang / 90.0, 0.0, 1.0)
    accept = (best_ang <= sam_threshold_deg) & (strength >= min_strength)
    positions = np.where(flat_valid)[0]
    labels = np.full(flat_valid.shape[0], UNKNOWN_CLASS, dtype=np.uint8)
    labels[positions[accept]] = best_idx[accept]
    return labels.reshape(h, w)


def load_cuprite_benchmark(bench_dir: Path | str) -> dict[str, Any]:
    """Load benchmarks/cuprite_real package arrays + metadata."""
    bench = Path(bench_dir)
    scene = bench / "scene.tif"
    ref_path = bench / "reference.tif"
    legend = json.loads((bench / "legend.json").read_text(encoding="utf-8"))
    wavelengths = [float(x) for x in json.loads((bench / "wavelengths.json").read_text(encoding="utf-8"))]
    options: dict[str, Any] = {}
    opt_path = bench / "options.json"
    if opt_path.is_file():
        options = json.loads(opt_path.read_text(encoding="utf-8"))

    cube = np.asarray(tifffile.imread(scene), dtype=np.float32)
    if cube.ndim != 3:
        raise ValueError(f"scene.tif must be HWC, got {cube.shape}")
    reference = np.asarray(tifffile.imread(ref_path))
    if reference.ndim == 3:
        reference = reference[:, :, 0]
    reference = reference.astype(np.uint8)
    class_names = list(legend.get("class_names") or options.get("minerals") or [])
    if not class_names:
        raise ValueError("legend.json missing class_names")
    ignore = int(legend.get("ignore_index", UNKNOWN_CLASS))
    return {
        "bench_dir": bench,
        "cube": cube,
        "reference": reference,
        "class_names": class_names,
        "wavelengths": wavelengths,
        "options": options,
        "ignore_index": ignore,
        "legend": legend,
    }


def run_spatial_split_eval(
    bench_dir: Path | str,
    output_dir: Path | str,
    *,
    n_row_blocks: int = 4,
    n_col_blocks: int = 4,
    train_frac: float = 0.5,
    val_frac: float = 0.25,
    seed: int = 42,
    methods: list[str] | None = None,
    min_endmember_pixels: int = 30,
    sam_threshold_deg: float = 12.0,
    min_confidence: float = 0.50,
    mtmf_mf_threshold: float = 0.3,
    mtmf_infeas_threshold: float = 15.0,
    mnf_components: int = 20,
) -> dict[str, Any]:
    """Full spatial-split protocol on a benchmark package.

    Writes metrics_<method>.json and report.md under output_dir.
    """
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
    # labeled train pixels for endmembers
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
    lib_path = out / "train_library.csv"
    write_library_csv(lib_path, library)

    # Remap reference to used library order
    ref_remapped = remap_reference_to_names(reference, class_names, used_names, ignore_index=ignore)
    ref_test = mask_reference_to_split(ref_remapped, split, SPLIT_TEST, ignore_index=ignore)
    ref_val = mask_reference_to_split(ref_remapped, split, SPLIT_VAL, ignore_index=ignore)

    labeled_train = int(((ref_remapped != ignore) & train_mask).sum())
    labeled_val = int((ref_val != ignore).sum())
    labeled_test = int((ref_test != ignore).sum())

    requested = methods or ["sam", "continuum_removal", "mtmf", "mnf_sam"]
    results: dict[str, MethodResult] = {}

    # Shared background mask: train blocks (no test leakage for stats)
    bg_mask = train_mask & valid_pixel_mask(cube)

    for method in requested:
        m = method.strip().lower().replace("-", "_")
        print(f"[spatial_eval] running method={m} ...")
        try:
            if m in ("sam", "continuum_removal", "cr_sam", "fuse", "fuse_classical"):
                if m == "cr_sam":
                    clf = "continuum_removal"
                elif m in ("fuse", "fuse_classical"):
                    clf = "fuse_classical"
                else:
                    clf = m
                class_map, names, warnings = classify_oremapper(
                    cube,
                    wavelengths,
                    lib_path,
                    used_names,
                    classifier=clf,
                    sam_threshold_deg=sam_threshold_deg,
                    min_confidence=min_confidence,
                )
                # names should match used_names
                if names != used_names:
                    # remap class_map if library reordered (should not)
                    name_to_i = {n: i for i, n in enumerate(used_names)}
                    remapped = np.full_like(class_map, UNKNOWN_CLASS)
                    for i, n in enumerate(names):
                        if n in name_to_i:
                            remapped[class_map == i] = name_to_i[n]
                    class_map = remapped
                metrics = evaluate_maps(class_map, ref_test, used_names, ignore_index=ignore)
                results[m] = MethodResult(
                    method=m,
                    metrics=metrics,
                    class_map=class_map,
                    notes="; ".join(warnings) if warnings else "",
                    extra={"classifier": clf},
                )
            elif m == "mtmf":
                class_map = classify_mtmf_hard(
                    cube,
                    library,
                    background_mask=bg_mask,
                    mf_threshold=mtmf_mf_threshold,
                    infeas_threshold=mtmf_infeas_threshold,
                    seed=seed,
                )
                metrics = evaluate_maps(class_map, ref_test, used_names, ignore_index=ignore)
                results[m] = MethodResult(
                    method=m,
                    metrics=metrics,
                    class_map=class_map,
                    notes="hard labels from MF>=thr & infeas<=thr; bg stats from train blocks",
                    extra={
                        "mf_threshold": mtmf_mf_threshold,
                        "infeas_threshold": mtmf_infeas_threshold,
                    },
                )
            elif m in ("mnf_sam", "mnf"):
                # Closed-set hard labels: always assign nearest MNF-space endmember.
                # Reflectance-space degree thresholds do not transfer to MNF components.
                class_map = classify_mnf_sam(
                    cube,
                    library,
                    n_components=mnf_components,
                    sample_mask=bg_mask,
                    sam_threshold_deg=180.0,
                    min_strength=0.0,
                )
                metrics = evaluate_maps(class_map, ref_test, used_names, ignore_index=ignore)
                results[m] = MethodResult(
                    method=m,
                    metrics=metrics,
                    class_map=class_map,
                    notes=(
                        "closed-set SAM in MNF space (always assign); "
                        "MNF fit on train-block samples"
                    ),
                    extra={
                        "n_components": mnf_components,
                        "mode": "closed_set_argmin",
                    },
                )
            else:
                empty = evaluate_maps(
                    np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8),
                    ref_test,
                    used_names,
                    ignore_index=ignore,
                )
                results[m] = MethodResult(
                    method=m,
                    metrics=empty,
                    class_map=np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8),
                    available=False,
                    notes=f"unknown method {m!r}",
                )
        except Exception as exc:  # noqa: BLE001 — research runner must continue
            print(f"[spatial_eval] method={m} FAILED: {exc}")
            empty = evaluate_maps(
                np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8),
                ref_test,
                used_names,
                ignore_index=ignore,
            )
            results[m] = MethodResult(
                method=m,
                metrics=empty,
                class_map=np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8),
                available=False,
                notes=f"failed: {exc}",
            )

        mr = results[m]
        payload = mr.metrics_dict()
        payload["provenance"] = {
            "benchmark": str(data["bench_dir"]),
            "split": "spatial_block",
            "score_region": "test_blocks_only",
            "library": "train-block pure GT endmembers",
            "endmember_counts": em_counts,
            "used_names": used_names,
            "labeled_test": labeled_test,
            "labeled_val": labeled_val,
            "labeled_train": labeled_train,
            "n_row_blocks": n_row_blocks,
            "n_col_blocks": n_col_blocks,
            "seed": seed,
        }
        (out / f"metrics_{m}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        # write class map + test-masked eval artifacts per method
        method_dir = out / m
        write_evaluation_artifacts(
            method_dir,
            mr.class_map,
            ref_test,
            used_names,
            ignore_index=ignore,
            extra_metrics=payload["provenance"],
        )
        print(
            f"[spatial_eval] {m}: OA={mr.metrics.overall_accuracy:.4f} "
            f"kappa={mr.metrics.kappa:.4f} n={mr.metrics.n_labeled} available={mr.available}"
        )

    summary = {
        "benchmark": str(data["bench_dir"]),
        "output_dir": str(out),
        "spatial_split": split.to_dict(),
        "used_names": used_names,
        "endmember_train_counts": em_counts,
        "labeled_pixels": {
            "train": labeled_train,
            "val": labeled_val,
            "test": labeled_test,
        },
        "methods": {
            name: {
                "overall_accuracy": mr.metrics.overall_accuracy,
                "kappa": mr.metrics.kappa,
                "n_labeled": mr.metrics.n_labeled,
                "n_correct": mr.metrics.n_correct,
                "available": mr.available,
                "notes": mr.notes,
            }
            for name, mr in results.items()
        },
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    _write_report(out / "report.md", summary, results, used_names)
    return summary


def _write_report(
    path: Path,
    summary: dict[str, Any],
    results: dict[str, MethodResult],
    used_names: list[str],
) -> None:
    lines = [
        "# Spatial split evaluation report",
        "",
        f"- Benchmark: `{summary['benchmark']}`",
        f"- Protocol: block spatial split (train endmembers → score test blocks only)",
        f"- Classes (train-supported): {', '.join(used_names)}",
        f"- Labeled pixels: train={summary['labeled_pixels']['train']}, "
        f"val={summary['labeled_pixels']['val']}, test={summary['labeled_pixels']['test']}",
        "",
        "## Overall accuracy (test blocks)",
        "",
        "| Method | OA | Kappa | N labeled | Available | Notes |",
        "|--------|----|-------|-----------|-----------|-------|",
    ]
    for name, mr in results.items():
        notes = (mr.notes or "").replace("|", "/")[:80]
        lines.append(
            f"| {name} | {mr.metrics.overall_accuracy:.4f} | {mr.metrics.kappa:.4f} | "
            f"{mr.metrics.n_labeled} | {mr.available} | {notes} |"
        )
    lines.extend(
        [
            "",
            "## Leakage controls",
            "",
            "- Scene endmembers = median spectra of pure GT pixels **inside train blocks only**.",
            "- Metrics use `evaluate_maps` with reference labels zeroed outside **test** blocks.",
            "- MTMF / MNF background statistics estimated from **train-block** valid pixels.",
            "- Random pixel splits are **not** used (spatial autocorrelation).",
            "",
            "## Artifacts",
            "",
            "- `spatial_split.json` — block grid and train/val/test assignment",
            "- `train_library.csv` — leakage-safe endmember library",
            "- `metrics_<method>.json` — full metrics per method",
            "- `<method>/` — confusion, class maps, diff PNGs",
            "- `summary.json` — compact scoreboard",
            "",
        ]
    )
    # per-method per-class for best available
    for name, mr in results.items():
        if not mr.available:
            continue
        lines.append(f"## Per-class: {name}")
        lines.append("")
        lines.append("| Class | Precision | Recall | F1 | Support |")
        lines.append("|-------|-----------|--------|----|---------|")
        for c in mr.metrics.per_class:
            if c.support == 0 and c.predicted == 0:
                continue
            lines.append(
                f"| {c.name} | {c.precision:.3f} | {c.recall:.3f} | {c.f1:.3f} | {c.support} |"
            )
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
