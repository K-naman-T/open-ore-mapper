from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class BandQuality:
    index: int
    wavelength: float
    finite_fraction: float
    mean: float | None
    std: float | None
    excluded: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class RasterQualityReport:
    status: str
    shape: tuple[int, int, int]
    band_count: int
    wavelength_min: float
    wavelength_max: float
    retained_band_indices: list[int]
    excluded_band_indices: list[int]
    valid_pixel_fraction: float
    warnings: list[str]
    bands: list[BandQuality]


def analyze_raster_quality(
    cube: NDArray[Any],
    wavelengths: list[float],
    excluded_band_indices: list[int] | None = None,
    min_band_valid_fraction: float = 0.5,
) -> RasterQualityReport:
    if cube.ndim != 3:
        raise ValueError(f"Expected a 3D raster cube, got shape {cube.shape}")
    if len(wavelengths) != cube.shape[2]:
        raise ValueError(
            f"Wavelength count ({len(wavelengths)}) does not match band count ({cube.shape[2]})"
        )

    if excluded_band_indices is not None:
        for idx in excluded_band_indices:
            if idx < 0 or idx >= cube.shape[2]:
                raise ValueError(
                    f"excluded_band_index {idx} is out of range for {cube.shape[2]} bands"
                )
    exclusions: set[int] = set(excluded_band_indices) if excluded_band_indices else set()

    bands: list[BandQuality] = []
    total_pixels = cube.shape[0] * cube.shape[1]
    for i in range(cube.shape[2]):
        band_flat = cube[:, :, i].ravel()
        finite_mask = np.isfinite(band_flat)
        finite_count = int(np.count_nonzero(finite_mask))
        finite_fraction = finite_count / total_pixels

        finite_vals = band_flat[finite_mask]
        mean = float(np.mean(finite_vals)) if finite_count > 0 else None
        std = float(np.std(finite_vals)) if finite_count > 0 else None

        reasons: list[str] = []
        if i in exclusions:
            reasons.append("user_excluded")
        if finite_fraction < min_band_valid_fraction:
            reasons.append("low_finite_fraction")

        is_excluded = bool(reasons)

        bands.append(
            BandQuality(
                index=i,
                wavelength=wavelengths[i],
                finite_fraction=finite_fraction,
                mean=mean,
                std=std,
                excluded=is_excluded,
                reasons=reasons,
            )
        )

    retained_band_indices = [b.index for b in bands if not b.excluded]
    excluded_band_indices_list = [b.index for b in bands if b.excluded]

    wavelength_min = min(wavelengths)
    wavelength_max = max(wavelengths)

    if len(retained_band_indices) > 0:
        retained_pixels = cube[:, :, retained_band_indices]
        finite_across = np.all(np.isfinite(retained_pixels), axis=2)
        nonzero = (
            np.linalg.norm(np.nan_to_num(retained_pixels, nan=0.0, posinf=0.0, neginf=0.0), axis=2) > 1e-10
        )
        valid_pixel_fraction = float(
            np.count_nonzero(finite_across & nonzero) / total_pixels
        )
    else:
        valid_pixel_fraction = 0.0

    warnings: list[str] = []
    if valid_pixel_fraction < 1.0:
        invalid_pixels = total_pixels - int(round(valid_pixel_fraction * total_pixels))
        warnings.append(
            f"{invalid_pixels} of {total_pixels} pixels ({100.0 - valid_pixel_fraction * 100.0:.2f}%) are invalid (NaN or zero magnitude)"
        )
    if len(excluded_band_indices_list) > 0:
        warnings.append(
            f"{len(excluded_band_indices_list)} band(s) were excluded"
        )
    if len(retained_band_indices) < 2:
        warnings.append(
            "Insufficient usable bands: at least 2 are required for mineral mapping"
        )

    if len(retained_band_indices) < 2:
        status = "fail"
    elif len(excluded_band_indices_list) > 0 or valid_pixel_fraction < 1.0:
        status = "warn"
    else:
        status = "pass"

    return RasterQualityReport(
        status=status,
        shape=cube.shape,
        band_count=cube.shape[2],
        wavelength_min=wavelength_min,
        wavelength_max=wavelength_max,
        retained_band_indices=retained_band_indices,
        excluded_band_indices=excluded_band_indices_list,
        valid_pixel_fraction=valid_pixel_fraction,
        warnings=warnings,
        bands=bands,
    )
