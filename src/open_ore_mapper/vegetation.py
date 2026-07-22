from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def ndvi_mask(
    cube: NDArray[np.float32],
    wavelengths: list[float],
    threshold: float = 0.3,
) -> NDArray[np.bool_]:
    nir_idx = _closest_band(wavelengths, 850.0)
    red_idx = _closest_band(wavelengths, 665.0)

    if nir_idx is None or red_idx is None:
        return np.zeros((cube.shape[0], cube.shape[1]), dtype=np.bool_)

    nir_band = cube[:, :, nir_idx]
    red_band = cube[:, :, red_idx]

    denominator = nir_band + red_band

    safe_denom = np.where(denominator == 0, 1.0, denominator)
    ndvi = (nir_band - red_band) / safe_denom
    ndvi = np.where(denominator == 0, 0.0, ndvi)

    return ndvi > threshold


def _closest_band(wavelengths: list[float], target: float) -> int | None:
    if not wavelengths:
        return None
    wl = np.asarray(wavelengths, dtype=np.float32)
    if target < wl.min() - 50.0 or target > wl.max() + 50.0:
        return None
    return int(np.argmin(np.abs(wl - target)))
