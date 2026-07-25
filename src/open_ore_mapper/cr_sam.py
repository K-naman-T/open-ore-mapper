"""Continuum-removed / region-weighted SAM — classical CPU spectral matching.

Addresses full-spectrum SAM failures on Cuprite-style SWIR minerals by:
1. Linear continuum removal (fast, vectorized)
2. Separate VNIR (Fe-oxides) and SWIR (clays/carbonates/silica) windows
3. Region-gated argmin so kaolinite is not compared to hematite in full space
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

from .sam import compute_sam_angles

# Mineral groups for hierarchical matching
FE_OXIDES = frozenset({"hematite", "goethite", "magnetite", "limonite", "ferrihydrite"})
SWIR_MINERALS = frozenset(
    {
        "kaolinite",
        "alunite",
        "calcite",
        "chalcedony",
        "buddingtonite",
        "muscovite",
        "montmorillonite",
        "illite",
        "dickite",
        "dolomite",
        "gypsum",
        "chlorite",
        "epidote",
    }
)


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
    x0, x1 = 0.0, float(b - 1)
    y0 = arr[:, 0]
    y1 = arr[:, -1]
    t = np.linspace(0.0, 1.0, b, dtype=np.float64)
    continuum = y0[:, None] + t[None, :] * (y1 - y0)[:, None]
    continuum = np.maximum(continuum, 1e-6)
    cr = arr / continuum
    return cast(NDArray[np.float32], np.clip(cr, 0.0, 2.0).astype(np.float32))


def band_mask(wavelengths: NDArray[np.floating[Any]], lo: float, hi: float) -> NDArray[np.bool_]:
    wl = np.asarray(wavelengths, dtype=np.float64)
    return (wl >= lo) & (wl <= hi)


def _l2_normalize(rows: NDArray[np.floating[Any]]) -> NDArray[np.float32]:
    arr = np.asarray(rows, dtype=np.float64)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)
    return cast(NDArray[np.float32], (arr / norms).astype(np.float32))


def classify_cr_sam(
    pixels: NDArray[np.floating[Any]],
    ref_spectra: NDArray[np.floating[Any]],
    wavelengths: NDArray[np.floating[Any]],
    mineral_names: list[str],
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

    names_l = [m.lower() for m in mineral_names]
    fe_idx = [i for i, m in enumerate(names_l) if m in FE_OXIDES]
    swir_idx = [i for i, m in enumerate(names_l) if m in SWIR_MINERALS]
    # ungrouped go to both
    other = [i for i in range(k) if i not in fe_idx and i not in swir_idx]
    fe_idx = fe_idx + other
    swir_idx = swir_idx + other

    vnir_m = band_mask(wl, 450.0, 1100.0)
    swir_m = band_mask(wl, 2000.0, 2450.0)
    # fallback if masks empty
    if not np.any(vnir_m):
        vnir_m = np.ones(wl.shape[0], dtype=bool)
    if not np.any(swir_m):
        swir_m = np.ones(wl.shape[0], dtype=bool)

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

    # For each pixel, score each mineral with region-appropriate angle
    scores = np.zeros((n, k), dtype=np.float64)
    for j, name in enumerate(names_l):
        if name in FE_OXIDES:
            scores[:, j] = 1.0 - (ang_vnir[:, j] / 90.0)
            # small bonus from full CR
            scores[:, j] = 0.75 * scores[:, j] + 0.25 * (1.0 - ang_full[:, j] / 90.0)
        elif name in SWIR_MINERALS:
            scores[:, j] = 1.0 - (ang_swir[:, j] / 90.0)
            scores[:, j] = 0.8 * scores[:, j] + 0.2 * (1.0 - ang_full[:, j] / 90.0)
        else:
            scores[:, j] = 1.0 - (ang_full[:, j] / 90.0)

    scores = np.clip(scores, 0.0, 1.0)

    # Hierarchical gate: if best SWIR score clearly beats best Fe, restrict to SWIR minerals
    best_fe = np.max(scores[:, fe_idx], axis=1) if fe_idx else np.zeros(n)
    best_sw = np.max(scores[:, swir_idx], axis=1) if swir_idx else np.zeros(n)
    use_swir = best_sw >= best_fe - 0.02
    use_fe = ~use_swir

    final_scores = scores.copy()
    if swir_idx and fe_idx:
        mask_sw = np.ones(k, dtype=bool)
        mask_sw[fe_idx] = False
        # zero Fe scores when SWIR wins
        for j in fe_idx:
            if j not in swir_idx:
                final_scores[use_swir, j] = -1.0
        for j in swir_idx:
            if j not in fe_idx:
                final_scores[use_fe, j] = -1.0

    best_idx = np.argmax(final_scores, axis=1).astype(np.uint8)
    best_conf = np.max(final_scores, axis=1).astype(np.float32)

    # Angle gate using the region used for the winner
    best_angles = np.empty(n, dtype=np.float32)
    for i in range(n):
        j = int(best_idx[i])
        name = names_l[j]
        if name in FE_OXIDES:
            best_angles[i] = ang_vnir[i, j]
        elif name in SWIR_MINERALS:
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
    mineral_names: list[str],
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
                mineral_names,
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
