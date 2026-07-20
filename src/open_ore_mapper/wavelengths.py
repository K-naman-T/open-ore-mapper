from __future__ import annotations

import json

import numpy as np


def parse_wavelengths_text(text: str | None) -> list[float] | None:
    if text is None or text.strip() == "":
        return None
    parsed = json.loads(text)
    if not isinstance(parsed, list):
        raise ValueError("Wavelengths must be a JSON array of numbers")
    try:
        return [float(value) for value in parsed]
    except (TypeError, ValueError) as exc:
        raise ValueError("Wavelengths must be numeric") from exc


def validate_wavelengths(wavelengths: list[float], expected_bands: int) -> list[float]:
    if len(wavelengths) == 0:
        raise ValueError("At least one wavelength is required")
    if len(wavelengths) != expected_bands:
        raise ValueError(f"Expected {expected_bands} wavelengths, got {len(wavelengths)}")
    diffs = np.diff(np.asarray(wavelengths, dtype=np.float64))
    if np.any(diffs <= 0):
        raise ValueError("Wavelengths must be strictly increasing")
    return [float(value) for value in wavelengths]


def resolve_wavelengths(
    wavelengths_text: str | None,
    sensor: str | None,
    expected_bands: int,
) -> tuple[list[float], str]:
    sensor_name = (sensor or "manual").strip().lower()
    parsed = parse_wavelengths_text(wavelengths_text)
    if parsed is not None:
        return validate_wavelengths(parsed, expected_bands), "manual"
    if sensor_name == "cubert_ultris_s5":
        wavelengths = np.linspace(450.0, 850.0, 51).tolist()
        return validate_wavelengths(wavelengths, expected_bands), sensor_name
    raise ValueError(
        "Provide wavelengths as a JSON array, or choose a sensor preset that matches the raster band count"
    )
