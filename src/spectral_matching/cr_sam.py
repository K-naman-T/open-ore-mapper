"""Continuum-removed / region-weighted SAM — classical CPU spectral matching.

Addresses full-spectrum SAM failures on mixed-range spectra by:
1. Linear continuum removal (fast, vectorized)
2. Separate VNIR (< 1100 nm) and SWIR (>= 1100 nm) regions
3. Region-gated argmin so a SWIR-featured class is not compared to a
   VNIR-featured class in full space

The region a class belongs to is inferred from its own continuum-removed
reference spectrum: the region holding the bulk of its absorption features.
No domain-specific class names are assumed, keeping the engine universal.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from .sam import compute_sam_angles

# Boundary between VNIR and SWIR regions (nanometers).
_VNIR_SWIR_SPLIT_NM = 1100.0


def linear_continuum_remove(
    spectra: NDArray[np.floating[Any]],
) -> NDArray[np.float32]:
    """Divide each spectrum by a linear continuum between first and last band.

    spectra: (N, B) reflectance. Returns continuum-removed (hull-quotient-like)
    values typically in (0, 1], float32.
    """
    arr = np.asarray(spectra, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] < 2:
        return cast(NDArray[np.float32], arr.astype(np.float32))
    n, b = arr.shape
    _x0, _x1 = 0.0, float(b - 1)
    y0 = arr[:, 0]
    y1 = arr[:, -1]
    t = np.linspace(0.0, 1.0, b, dtype=np.float64)
    continuum = y0[:, None] + t[None, :] * (y1 - y0)[:, None]
    continuum = np.maximum(continuum, 1e-6)
    cr = arr / continuum
    return cast(NDArray[np.float32], np.clip(cr, 0.0, 2.0).astype(np.float32))


def _region_masks(wavelengths: NDArray[np.floating[Any]]) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    wl = np.asarray(wavelengths, dtype=np.float64)
    vnir_m = wl < _VNIR_SWIR_SPLIT_NM
    swir_m = ~vnir_m
    if not np.any(vnir_m):
        vnir_m = np.ones(wl.shape[0], dtype=bool)
    if not np.any(swir_m):
        swir_m = np.ones(wl.shape[0], dtype=bool)
    return vnir_m, swir_m


def _assign_region(cr_row: NDArray[np.floating[Any]], vnir_m: NDArray[np.bool_], swir_m: NDArray[np.bool_]) -> str:
    """Pick the region holding most of a reference's absorption features.

    Returns "vnir", "swir", or "full" (for featureless spectra) based on mean
    absolute deviation from the continuum in each region.
    """
    dev = np.abs(np.asarray(cr_row, dtype=np.float64) - 1.0)
    v_energy = float(dev[vnir_m].mean())
    s_energy = float(dev[swir_m].mean())
    if v_energy < 1e-6 and s_energy < 1e-6:
        return "full"
    return "swir" if s_energy > v_energy else "vnir"


def _l2_normalize(rows: NDArray[np.floating[Any]]) -> NDArray[np.float32]:
    arr = np.asarray(rows, dtype=np.float64)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)
    return cast(NDArray[np.float32], (arr / norms).astype(np.float32))


def classify_cr_sam(
    pixels: NDArray[np.floating[Any]],
    ref_spectra: NDArray[np.floating[Any]],
    wavelengths: NDArray[np.floating[Any]],
    class_names: list[str],
    *,
    sam_threshold_deg: float = 12.0,
    min_strength: float = 0.55,
) -> tuple[NDArray[np.uint8], NDArray[np.float32]]:
    """Classify N pixels with continuum-removed region-weighted SAM.

    Returns (class_idx N, confidence N). Unknown = 255.
    """
    pix = np.asarray(pixels, dtype=np.float32)
    refs = np.asarray(ref_spectra, dtype=np.float32)
    wl = np.asarray(wavelengths, dtype=np.float32)
    n = pix.shape[0]
    k = refs.shape[0]
    if n == 0:
        return np.zeros(0, dtype=np.uint8), np.zeros(0, dtype=np.float32)

    vnir_m, swir_m = _region_masks(wl)

    # Continuum remove full spectrum then slice (CR more stable on full before cut)
    pix_cr = linear_continuum_remove(pix)
    ref_cr = linear_continuum_remove(refs)

    def _angles_on_mask(
        p: NDArray[np.float32], r: NDArray[np.float32], mask: NDArray[np.bool_]
    ) -> NDArray[np.float32]:
        p_m = _l2_normalize(p[:, mask])
        r_m = _l2_normalize(r[:, mask] if r.ndim == 2 else r)
        return compute_sam_angles(p_m, r_m)

    # Full CR-SAM as baseline
    ang_full = _angles_on_mask(pix_cr, ref_cr, np.ones(wl.shape[0], dtype=bool))
    # Region angles
    ang_vnir = _angles_on_mask(pix_cr, ref_cr, vnir_m)
    ang_swir = _angles_on_mask(pix_cr, ref_cr, swir_m)

    # Assign each reference class to its dominant region
    regions = [_assign_region(row, vnir_m, swir_m) for row in ref_cr]
    vnir_idx = [j for j, r in enumerate(regions) if r == "vnir"]
    swir_idx = [j for j, r in enumerate(regions) if r == "swir"]
    full_idx = [j for j, r in enumerate(regions) if r == "full"]

    # For each pixel, score each class with its region-appropriate angle
    scores = np.zeros((n, k), dtype=np.float64)
    for j, region in enumerate(regions):
        if region in ("vnir", "swir"):
            angle = ang_vnir[:, j] if region == "vnir" else ang_swir[:, j]
            scores[:, j] = 0.75 * (1.0 - angle / 90.0) + 0.25 * (1.0 - ang_full[:, j] / 90.0)
        else:
            scores[:, j] = 1.0 - (ang_full[:, j] / 90.0)

    scores = np.clip(scores, 0.0, 1.0)

    # Hierarchical gate: if the best SWIR score clearly beats the best VNIR
    # score, restrict to SWIR classes (and vice versa). Featureless ("full")
    # classes always compete and are never gated out.
    gate_vnir = sorted(set(vnir_idx) | set(full_idx))
    gate_swir = sorted(set(swir_idx) | set(full_idx))
    best_vnir = np.max(scores[:, gate_vnir], axis=1) if gate_vnir else np.zeros(n)
    best_swir = np.max(scores[:, gate_swir], axis=1) if gate_swir else np.zeros(n)
    use_swir = best_swir >= best_vnir - 0.02
    use_vnir = ~use_swir

    final_scores = scores.copy()
    if swir_idx and vnir_idx:
        for j in vnir_idx:
            if j not in swir_idx:
                final_scores[use_swir, j] = -1.0
        for j in swir_idx:
            if j not in vnir_idx:
                final_scores[use_vnir, j] = -1.0

    best_idx = np.argmax(final_scores, axis=1).astype(np.uint8)
    best_conf = np.max(final_scores, axis=1).astype(np.float32)

    # Angle gate using the region used for the winner
    best_angles = np.empty(n, dtype=np.float32)
    for i in range(n):
        j = int(best_idx[i])
        region = regions[j]
        if region == "vnir":
            best_angles[i] = ang_vnir[i, j]
        elif region == "swir":
            best_angles[i] = ang_swir[i, j]
        else:
            best_angles[i] = ang_full[i, j]

    accepted = (best_conf >= min_strength) & (best_angles <= sam_threshold_deg)
    classes = np.full(n, 255, dtype=np.uint8)
    classes[accepted] = best_idx[accepted]
    conf = best_conf.copy()
    conf[~accepted] = best_conf[~accepted]  # keep conf even if rejected
    return classes, conf


def classify_cube_cr_sam(
    cube: NDArray[np.floating[Any]],
    ref_spectra: NDArray[np.floating[Any]],
    wavelengths: list[float] | NDArray[np.floating[Any]],
    class_names: list[str],
    valid_mask: NDArray[np.bool_],
    *,
    tile_size: int = 128,
    sam_threshold_deg: float = 12.0,
    min_strength: float = 0.55,
) -> tuple[NDArray[np.uint8], NDArray[np.float32]]:
    """Tile over H×W×B cube; return class_map and confidence."""
    h, w, _b = cube.shape
    class_map = np.full((h, w), 255, dtype=np.uint8)
    conf_map = np.zeros((h, w), dtype=np.float32)
    wl = np.asarray(wavelengths, dtype=np.float32)
    refs = np.asarray(ref_spectra, dtype=np.float32)

    for r0 in range(0, h, tile_size):
        r1 = min(h, r0 + tile_size)
        for c0 in range(0, w, tile_size):
            c1 = min(w, c0 + tile_size)
            tile = cube[r0:r1, c0:c1, :]
            v = valid_mask[r0:r1, c0:c1]
            flat = tile.reshape(-1, tile.shape[2])
            flat_v = v.reshape(-1)
            if not np.any(flat_v):
                continue
            cls, conf = classify_cr_sam(
                flat[flat_v],
                refs,
                wl,
                class_names,
                sam_threshold_deg=sam_threshold_deg,
                min_strength=min_strength,
            )
            out_c = np.full(flat_v.shape[0], 255, dtype=np.uint8)
            out_f = np.zeros(flat_v.shape[0], dtype=np.float32)
            pos = np.where(flat_v)[0]
            out_c[pos] = cls
            out_f[pos] = conf
            class_map[r0:r1, c0:c1] = out_c.reshape(r1 - r0, c1 - c0)
            conf_map[r0:r1, c0:c1] = out_f.reshape(r1 - r0, c1 - c0)
    return class_map, conf_map
