from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import cast

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import ConvexHull, QhullError

from .spectral_library import SpectralLibrary


@dataclass(frozen=True)
class AbsorptionFeature:
    position: float
    depth: float
    fwhm: float
    asymmetry: float


class FeatureLibrary:
    def __init__(
        self, mineral_names: list[str], features: list[list[AbsorptionFeature]]
    ) -> None:
        self.mineral_names = mineral_names
        self.features = features

    @classmethod
    def from_spectral_library(
        cls, lib: SpectralLibrary, min_depth: float = 0.02
    ) -> FeatureLibrary:
        features: list[list[AbsorptionFeature]] = []
        for spectrum in lib.spectra:
            hq = hull_quotient(lib.wavelengths, spectrum)
            feats = extract_absorption_features(lib.wavelengths, hq, min_depth)
            features.append(feats)
        return cls(mineral_names=list(lib.names), features=features)


def hull_quotient(
    wavelengths: NDArray[np.float32],
    reflectance: NDArray[np.float32],
) -> NDArray[np.float32]:
    points = np.column_stack([wavelengths, reflectance])
    try:
        hull = ConvexHull(points)
    except QhullError:
        return np.ones_like(reflectance)

    vtx = hull.vertices
    vtx_sorted = vtx[np.argsort(wavelengths[vtx])]

    leftmost = vtx_sorted[0]
    rightmost = vtx_sorted[-1]

    x_left = wavelengths[leftmost]
    y_left = reflectance[leftmost]
    x_right = wavelengths[rightmost]
    y_right = reflectance[rightmost]
    denom = x_right - x_left

    upper_indices: list[int] = [leftmost]
    for idx in vtx_sorted[1:-1]:
        x = wavelengths[idx]
        y = reflectance[idx]
        t = (x - x_left) / denom if denom != 0 else 0.0
        y_line = y_left + t * (y_right - y_left)
        if y >= y_line - 1e-10:
            upper_indices.append(idx)
    upper_indices.append(rightmost)

    hull_x = wavelengths[upper_indices]
    hull_y = reflectance[upper_indices]
    hull_interp = np.interp(wavelengths, hull_x, hull_y)

    result = reflectance / hull_interp
    return cast(NDArray[np.float32], result)


def extract_absorption_features(
    wavelengths: NDArray[np.float32],
    continuum_removed: NDArray[np.float32],
    min_depth: float = 0.02,
) -> list[AbsorptionFeature]:
    features: list[AbsorptionFeature] = []
    n = len(continuum_removed)
    if n < 3:
        return features

    minima_indices: list[int] = []
    for i in range(1, n - 1):
        if (
            continuum_removed[i] <= continuum_removed[i - 1]
            and continuum_removed[i] <= continuum_removed[i + 1]
        ):
            depth = 1.0 - continuum_removed[i]
            if depth >= min_depth:
                minima_indices.append(i)

    for idx in minima_indices:
        min_val = continuum_removed[idx]
        depth = 1.0 - min_val

        left_boundary = 0
        for j in range(idx, -1, -1):
            if continuum_removed[j] >= 0.995:
                left_boundary = j
                break

        right_boundary = n - 1
        for j in range(idx, n):
            if continuum_removed[j] >= 0.995:
                right_boundary = j
                break

        half_level = 1.0 - depth / 2.0

        left_half_wl = float(wavelengths[left_boundary])
        for j in range(idx, left_boundary - 1, -1):
            if j > 0 and continuum_removed[j] < half_level <= continuum_removed[j - 1]:
                t = (half_level - continuum_removed[j]) / (
                    continuum_removed[j - 1] - continuum_removed[j]
                )
                left_half_wl = wavelengths[j] + t * (wavelengths[j - 1] - wavelengths[j])
                break

        right_half_wl = float(wavelengths[right_boundary])
        for j in range(idx, right_boundary + 1):
            if j < n - 1 and continuum_removed[j] < half_level <= continuum_removed[j + 1]:
                t = (half_level - continuum_removed[j]) / (
                    continuum_removed[j + 1] - continuum_removed[j]
                )
                right_half_wl = wavelengths[j] + t * (wavelengths[j + 1] - wavelengths[j])
                break

        fwhm = right_half_wl - left_half_wl
        left_width = wavelengths[idx] - left_half_wl
        right_width = right_half_wl - wavelengths[idx]
        asymmetry = left_width / right_width if right_width > 0 else 1.0

        features.append(
            AbsorptionFeature(
                position=float(wavelengths[idx]),
                depth=float(depth),
                fwhm=float(fwhm),
                asymmetry=float(asymmetry),
            )
        )

    return features


def match_features(
    pixel_features: list[AbsorptionFeature],
    library: FeatureLibrary,
) -> NDArray[np.float32]:
    n_minerals = len(library.mineral_names)
    scores: NDArray[np.float32] = np.zeros(n_minerals, dtype=np.float32)

    for mineral_idx in range(n_minerals):
        lib_features = library.features[mineral_idx]
        if not lib_features or not pixel_features:
            continue

        total_score = 0.0
        for lf in lib_features:
            best_score = 0.0
            for pf in pixel_features:
                pos_diff = lf.position - pf.position
                depth_diff = lf.depth - pf.depth
                score = np.exp(-(pos_diff**2) / (2.0 * 20.0**2)) * np.exp(
                    -(depth_diff**2) / (2.0 * 0.01)
                )
                best_score = max(best_score, score)
            total_score += best_score

        avg_score = total_score / len(lib_features)
        scores[mineral_idx] = np.clip(float(avg_score), 0.0, 1.0)

    return scores


def hull_quotient_batch(
    wavelengths: NDArray[np.float32],
    reflectance_2d: NDArray[np.float32],
) -> NDArray[np.float32]:
    N = reflectance_2d.shape[0]
    results = np.empty_like(reflectance_2d)
    with ThreadPoolExecutor(max_workers=min(8, N)) as ex:
        futures = [ex.submit(hull_quotient, wavelengths, reflectance_2d[i]) for i in range(N)]
        for i, f in enumerate(futures):
            results[i] = f.result()
    return results


def extract_absorption_features_batch(
    wavelengths: NDArray[np.float32],
    continuum_removed_2d: NDArray[np.float32],
    min_depth: float = 0.02,
) -> list[list[AbsorptionFeature]]:
    return [
        extract_absorption_features(wavelengths, continuum_removed_2d[i], min_depth)
        for i in range(continuum_removed_2d.shape[0])
    ]


def match_features_batch(
    pixel_features: list[list[AbsorptionFeature]],
    library: FeatureLibrary,
) -> NDArray[np.float32]:
    N = len(pixel_features)
    M = len(library.mineral_names)
    scores: NDArray[np.float32] = np.zeros((N, M), dtype=np.float32)
    for i in range(N):
        scores[i] = match_features(pixel_features[i], library)
    return scores
