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


_SENSOR_PRESETS: dict[str, tuple[float, float, int, str]] = {
    # name -> (start, stop, band_count, label)
    "aviris": (366.0, 2510.0, 204, "aviris"),
    "cubert_ultris_s5": (450.0, 850.0, 51, "cubert_ultris_s5"),
    "emit": (381.0, 2493.0, 285, "emit"),
}


def _preset_grid(name: str, expected_bands: int) -> tuple[list[float], str] | None:
    preset = _SENSOR_PRESETS.get(name)
    if preset is None:
        return None
    start, stop, count, label = preset
    if count == expected_bands:
        return np.linspace(start, stop, count).tolist(), label
    return None


def _auto_grid(expected_bands: int) -> tuple[list[float], str] | None:
    # If the raster band count matches a known sensor grid exactly, reuse it
    # so browser uploads (which never send wavelengths) just work.
    if expected_bands == 51:
        return np.linspace(450.0, 850.0, 51).tolist(), "aviris"
    if expected_bands == 204:
        return np.linspace(366.0, 2510.0, 204).tolist(), "aviris"
    if expected_bands == 285:
        return np.linspace(381.0, 2493.0, 285).tolist(), "emit"
    return None


def resolve_wavelengths(
    wavelengths_text: str | None,
    sensor: str | None,
    expected_bands: int,
) -> tuple[list[float], str]:
    sensor_name = (sensor or "manual").strip().lower()
    parsed = parse_wavelengths_text(wavelengths_text)
    if parsed is not None:
        return validate_wavelengths(parsed, expected_bands), "manual"

    if sensor_name != "manual":
        grid = _preset_grid(sensor_name, expected_bands)
        if grid is not None:
            return validate_wavelengths(grid[0], expected_bands), grid[1]

    grid = _auto_grid(expected_bands)
    if grid is not None:
        return validate_wavelengths(grid[0], expected_bands), grid[1]

    known = ", ".join(sorted(_SENSOR_PRESETS))
    raise ValueError(
        f"No wavelength preset for sensor '{sensor_name}' with {expected_bands} bands. "
        f"Provide wavelengths as a JSON array, or choose a sensor preset that matches "
        f"the raster band count ({known})"
    )
