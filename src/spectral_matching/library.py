from __future__ import annotations

import csv
import io
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


def load_csv_library(path: str | Path, target_classes: list[str] | None) -> SpectralLibrary:
    rows_by_name: OrderedDict[str, list[tuple[float, float]]] = OrderedDict()
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError("Spectral library CSV requires columns: class, wavelength, reflectance")
        has_name = "name" in fieldnames
        has_class = "class" in fieldnames
        if not has_name and not has_class:
            raise ValueError("Spectral library CSV requires a 'class' (or 'name') column")
        class_col = "class" if has_class else "name"
        required = {class_col, "wavelength", "reflectance"}
        if not required.issubset(fieldnames):
            raise ValueError("Spectral library CSV requires columns: class, wavelength, reflectance")
        for row in reader:
            name = (row.get(class_col) or "").strip()
            if not name:
                raise ValueError("Spectral library rows require a class name")
            wavelength = _parse_finite_float(row.get("wavelength"), "wavelength")
            reflectance = _parse_finite_float(row.get("reflectance"), "reflectance")
            rows_by_name.setdefault(name, []).append((wavelength, reflectance))

    if not rows_by_name:
        raise ValueError("Spectral library CSV is empty")

    selected_names = list(rows_by_name) if not target_classes else list(target_classes)
    missing = [name for name in selected_names if name not in rows_by_name]
    if missing:
        raise ValueError(f"Unknown classes: {', '.join(missing)}")

    wavelengths: NDArray[np.float32] | None = None
    spectra_rows: list[list[float]] = []
    for name in selected_names:
        pairs = rows_by_name[name]
        class_wavelengths = np.asarray([wavelength for wavelength, _value in pairs], dtype=np.float32)
        if np.any(np.diff(class_wavelengths) <= 0):
            raise ValueError(f"Wavelengths for {name} must be strictly increasing")
        if wavelengths is None:
            wavelengths = cast(NDArray[np.float32], class_wavelengths)
        elif not np.array_equal(wavelengths, class_wavelengths):
            raise ValueError("All selected classes must use the same wavelength grid")
        spectra_rows.append([reflectance for _wavelength, reflectance in pairs])

    if wavelengths is None:
        raise ValueError("No selected classes found")

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


def load_csv_bytes(data: bytes, target_classes: list[str] | None = None) -> SpectralLibrary:
    rows_by_name: OrderedDict[str, list[tuple[float, float]]] = OrderedDict()
    with io.TextIOWrapper(io.BytesIO(data), encoding="utf-8") as text_stream:
        reader = csv.DictReader(text_stream)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            raise ValueError("Spectral library CSV requires columns: class, wavelength, reflectance")
        has_name = "name" in fieldnames
        has_class = "class" in fieldnames
        if not has_name and not has_class:
            raise ValueError("Spectral library CSV requires a 'class' (or 'name') column")
        class_col = "class" if has_class else "name"
        required = {class_col, "wavelength", "reflectance"}
        if not required.issubset(fieldnames):
            raise ValueError("Spectral library CSV requires columns: class, wavelength, reflectance")
        for row in reader:
            name = (row.get(class_col) or "").strip()
            if not name:
                raise ValueError("Spectral library rows require a class name")
            wavelength = _parse_finite_float(row.get("wavelength"), "wavelength")
            reflectance = _parse_finite_float(row.get("reflectance"), "reflectance")
            rows_by_name.setdefault(name, []).append((wavelength, reflectance))

    if not rows_by_name:
        raise ValueError("Spectral library CSV is empty")

    selected_names = list(rows_by_name) if not target_classes else list(target_classes)
    missing = [name for name in selected_names if name not in rows_by_name]
    if missing:
        raise ValueError(f"Unknown classes: {', '.join(missing)}")

    wavelengths: NDArray[np.float32] | None = None
    spectra_rows: list[list[float]] = []
    for name in selected_names:
        pairs = rows_by_name[name]
        class_wavelengths = np.asarray([wavelength for wavelength, _value in pairs], dtype=np.float32)
        if np.any(np.diff(class_wavelengths) <= 0):
            raise ValueError(f"Wavelengths for {name} must be strictly increasing")
        if wavelengths is None:
            wavelengths = cast(NDArray[np.float32], class_wavelengths)
        elif not np.array_equal(wavelengths, class_wavelengths):
            raise ValueError("All selected classes must use the same wavelength grid")
        spectra_rows.append([reflectance for _wavelength, reflectance in pairs])

    if wavelengths is None:
        raise ValueError("No selected classes found")

    spectra = np.asarray(spectra_rows, dtype=np.float32)
    return SpectralLibrary(
        names=selected_names,
        wavelengths=wavelengths,
        spectra=cast(NDArray[np.float32], spectra),
        source="user CSV: uploaded bytes",
        is_authoritative=False,
    )


def _parse_finite_float(value: Any, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not np.isfinite(parsed):
        raise ValueError(f"{field_name} must be finite")
    return parsed
