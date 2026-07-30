from __future__ import annotations

from typing import Any, cast

import numpy as np
from numpy.typing import NDArray


def compute_sam_angles(
    pixel_spectra: NDArray[np.floating[Any]],
    reference_spectra: NDArray[np.floating[Any]],
) -> NDArray[np.float32]:
    pixels = np.asarray(pixel_spectra, dtype=np.float64)
    refs = np.asarray(reference_spectra, dtype=np.float64)
    pixel_norm = np.maximum(np.linalg.norm(pixels, axis=1, keepdims=True), 1e-10)
    ref_norm = np.maximum(np.linalg.norm(refs, axis=1, keepdims=True).T, 1e-10)
    cos_sim = np.clip((pixels @ refs.T) / (pixel_norm * ref_norm), -1.0, 1.0)
    return cast(NDArray[np.float32], np.degrees(np.arccos(cos_sim)).astype(np.float32))


def compute_sam_cube(
    hsi_cube: NDArray[np.floating[Any]],
    reference_spectra: NDArray[np.floating[Any]],
) -> tuple[NDArray[np.float32], NDArray[np.int32]]:
    height, width, bands = hsi_cube.shape
    flat = hsi_cube.reshape(-1, bands)
    refs = np.asarray(reference_spectra)
    angles = compute_sam_angles(flat, refs).reshape(height, width, refs.shape[0])
    labels = np.argmin(angles, axis=2).astype(np.int32)
    return cast(NDArray[np.float32], angles.astype(np.float32)), cast(NDArray[np.int32], labels)


def angles_to_strength(angles_deg: NDArray[np.floating[Any]]) -> NDArray[np.float32]:
    angles = np.asarray(angles_deg, dtype=np.float32)
    return cast(NDArray[np.float32], np.clip(1.0 - (angles / 90.0), 0.0, 1.0).astype(np.float32))
