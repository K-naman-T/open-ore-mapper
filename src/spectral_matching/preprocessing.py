from __future__ import annotations

from typing import Any, cast

import numpy as np
from numpy.typing import NDArray


def ensure_hwc(
    array: NDArray[Any],
    band_count: int | None = None,
) -> NDArray[np.float32]:
    arr = np.asarray(array)
    if arr.ndim != 3:
        raise ValueError(f"Expected a 3D raster cube, got shape {arr.shape}")
    if band_count is not None:
        matching = [i for i, s in enumerate(arr.shape) if s == band_count]
        if not matching:
            raise ValueError(
                f"No axis matches band_count={band_count} in shape {arr.shape}"
            )
        if len(matching) > 1:
            raise ValueError(
                f"Ambiguous band axis: multiple axes ({matching}) match "
                f"band_count={band_count} in shape {arr.shape}"
            )
        if arr.shape[-1] != band_count:
            arr = np.moveaxis(arr, matching[0], -1)
    else:
        if arr.shape[0] <= 128 and arr.shape[0] < arr.shape[1] and arr.shape[0] < arr.shape[2]:
            arr = np.moveaxis(arr, 0, -1)
    return cast(NDArray[np.float32], arr.astype(np.float32, copy=False))


def select_bands(
    cube: NDArray[np.floating[Any]],
    wavelengths: list[float],
    retained_indices: list[int],
) -> tuple[NDArray[np.float32], list[float]]:
    filtered_cube = cube[:, :, retained_indices].astype(np.float32, copy=False)
    filtered_wavelengths = [wavelengths[i] for i in retained_indices]
    return filtered_cube, filtered_wavelengths


def valid_pixel_mask(cube: NDArray[np.floating[Any]]) -> NDArray[np.bool_]:
    finite = np.all(np.isfinite(cube), axis=2)
    nonzero = np.linalg.norm(np.nan_to_num(cube, nan=0.0, posinf=0.0, neginf=0.0), axis=2) > 1e-10
    return cast(NDArray[np.bool_], finite & nonzero)


def normalize_cube(cube: NDArray[np.floating[Any]], mode: str) -> NDArray[np.float32]:
    mode_name = mode.lower()
    arr = cube.astype(np.float32, copy=True)
    if mode_name == "none":
        return cast(NDArray[np.float32], np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0))
    if mode_name == "l2":
        norms = np.linalg.norm(np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0), axis=2, keepdims=True)
        norms = np.maximum(norms, 1e-10)
        normalized = np.nan_to_num(arr / norms, nan=0.0, posinf=0.0, neginf=0.0)
        return cast(NDArray[np.float32], normalized.astype(np.float32))
    if mode_name == "percentile":
        out = np.zeros_like(arr, dtype=np.float32)
        for band_idx in range(arr.shape[2]):
            band = arr[:, :, band_idx]
            finite = np.isfinite(band)
            if not np.any(finite):
                continue
            low, high = np.percentile(band[finite], [2, 98])
            if high > low:
                out[:, :, band_idx] = np.clip((band - low) / (high - low), 0.0, 1.0)
        return cast(NDArray[np.float32], np.nan_to_num(out, nan=0.0, posinf=0.0, neginf=0.0))
    raise ValueError("normalization must be one of: none, l2, percentile")
