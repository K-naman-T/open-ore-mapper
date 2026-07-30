from __future__ import annotations

import csv
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class SpectralLibrary:
    names: list[str]
    wavelengths: NDArray[np.float32]
    spectra: NDArray[np.float32]
    source: str
    is_authoritative: bool = False


_DEMO_VALUES: dict[str, list[tuple[float, float]]] = {
    "hematite_demo": [(450, 0.42), (550, 0.30), (650, 0.34), (750, 0.46), (850, 0.52)],
    "goethite_demo": [(450, 0.38), (550, 0.44), (650, 0.35), (750, 0.48), (850, 0.55)],
    "jarosite_demo": [(450, 0.52), (550, 0.48), (650, 0.39), (750, 0.50), (850, 0.57)],
    "magnetite_demo": [(450, 0.12), (550, 0.13), (650, 0.14), (750, 0.15), (850, 0.16)],
    "limonite_demo": [(450, 0.36), (550, 0.34), (650, 0.31), (750, 0.43), (850, 0.49)],
    "ferrihydrite_demo": [(450, 0.32), (550, 0.29), (650, 0.33), (750, 0.41), (850, 0.47)],
}


def load_demo_library(target_minerals: list[str]) -> SpectralLibrary:
    missing = [name for name in target_minerals if name not in _DEMO_VALUES]
    if missing:
        raise ValueError(f"Unknown minerals: {', '.join(missing)}")
    names = list(target_minerals)
    wavelengths = np.asarray([pair[0] for pair in _DEMO_VALUES[names[0]]], dtype=np.float32)
    spectra = np.asarray(
        [[reflectance for _wavelength, reflectance in _DEMO_VALUES[name]] for name in names],
        dtype=np.float32,
    )
    return SpectralLibrary(
        names=names,
        wavelengths=cast(NDArray[np.float32], wavelengths),
        spectra=cast(NDArray[np.float32], spectra),
        source="synthetic demo spectra bundled for software testing, not authoritative spectra",
        is_authoritative=False,
    )


def load_csv_library(path: str | Path, target_minerals: list[str] | None) -> SpectralLibrary:
    rows_by_name: OrderedDict[str, list[tuple[float, float]]] = OrderedDict()
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"name", "wavelength", "reflectance"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError("Spectral library CSV requires columns: name, wavelength, reflectance")
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                raise ValueError("Spectral library rows require a mineral name")
            wavelength = _parse_finite_float(row.get("wavelength"), "wavelength")
            reflectance = _parse_finite_float(row.get("reflectance"), "reflectance")
            rows_by_name.setdefault(name, []).append((wavelength, reflectance))

    if not rows_by_name:
        raise ValueError("Spectral library CSV is empty")

    selected_names = list(rows_by_name) if target_minerals is None else list(target_minerals)
    missing = [name for name in selected_names if name not in rows_by_name]
    if missing:
        raise ValueError(f"Unknown minerals: {', '.join(missing)}")

    wavelengths: NDArray[np.float32] | None = None
    spectra_rows: list[list[float]] = []
    for name in selected_names:
        pairs = rows_by_name[name]
        mineral_wavelengths = np.asarray([wavelength for wavelength, _value in pairs], dtype=np.float32)
        if np.any(np.diff(mineral_wavelengths) <= 0):
            raise ValueError(f"Wavelengths for {name} must be strictly increasing")
        if wavelengths is None:
            wavelengths = cast(NDArray[np.float32], mineral_wavelengths)
        elif not np.array_equal(wavelengths, mineral_wavelengths):
            raise ValueError("All selected minerals must use the same wavelength grid")
        spectra_rows.append([reflectance for _wavelength, reflectance in pairs])

    if wavelengths is None:
        raise ValueError("No selected minerals found")

    spectra = np.asarray(spectra_rows, dtype=np.float32)
    return SpectralLibrary(
        names=selected_names,
        wavelengths=wavelengths,
        spectra=cast(NDArray[np.float32], spectra),
        source=f"user CSV: {Path(path)}",
        is_authoritative=False,
    )


def resample_library(library: SpectralLibrary, target_wavelengths: list[float]) -> SpectralLibrary:
    target = np.asarray(target_wavelengths, dtype=np.float32)
    source = np.asarray(library.wavelengths, dtype=np.float32)
    resampled = np.zeros((library.spectra.shape[0], len(target)), dtype=np.float32)
    for idx, spectrum in enumerate(library.spectra):
        resampled[idx] = np.interp(target, source, spectrum).astype(np.float32)
    return SpectralLibrary(
        names=list(library.names),
        wavelengths=cast(NDArray[np.float32], target),
        spectra=cast(NDArray[np.float32], resampled),
        source=library.source,
        is_authoritative=library.is_authoritative,
    )


def _parse_finite_float(value: Any, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not np.isfinite(parsed):
        raise ValueError(f"{field_name} must be finite")
    return parsed
