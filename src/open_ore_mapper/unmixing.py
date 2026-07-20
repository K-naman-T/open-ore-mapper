from __future__ import annotations

from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import nnls


def estimate_nnls_abundances(
    pixel_spectra: NDArray[np.floating[Any]],
    reference_spectra: NDArray[np.floating[Any]],
) -> NDArray[np.float32]:
    pixels = np.asarray(pixel_spectra, dtype=np.float64)
    refs = np.asarray(reference_spectra, dtype=np.float64)
    mixing_matrix = refs.T
    abundances = np.zeros((pixels.shape[0], refs.shape[0]), dtype=np.float32)
    for idx, pixel in enumerate(pixels):
        coeffs, _residual = nnls(mixing_matrix, pixel)
        total = float(coeffs.sum())
        if total > 1e-10:
            coeffs = coeffs / total
        abundances[idx] = coeffs.astype(np.float32)
    return cast(NDArray[np.float32], abundances)
