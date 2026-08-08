from __future__ import annotations

import json
from dataclasses import dataclass

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


@dataclass(frozen=True)
class SensorPreset:
    """Wavelength-grid definition for a known hyperspectral sensor.

    Grid resolution precedence:
    1. ``exact`` — a fully-verified per-band center-wavelength array (nm).
    2. ``start``/``step``/``count`` — a verified uniform grid, built lazily.
    3. ``start``/``stop``/``count`` — a documented (nominal) linear range
       fallback, used only when no exact grid is available.
    """

    name: str
    description: str
    source: str
    bands: int
    exact: tuple[float, ...] = ()
    start: float = 0.0
    step: float = 0.0
    stop: float = 0.0
    uniform: bool = False
    bad_bands: tuple[tuple[float, float], ...] = ()

    def wavelengths(self) -> list[float]:
        if self.exact:
            return list(self.exact)
        if self.step > 0:
            return [self.start + i * self.step for i in range(self.bands)]
        return list(np.linspace(self.start, self.stop, self.bands))


def _uniform(start: float, step: float, count: int) -> tuple[float, ...]:
    return tuple(round(start + i * step, 6) for i in range(count))


# Verified exact / uniform grids from primary sources (see research docs):
#   .superpowers/sdd/PLAN_V2/research-airborne-sensors.md
#   .superpowers/sdd/PLAN_V2/research-satellite-sensors.md
SENSOR_PRESETS: dict[str, SensorPreset] = {
    # ── Airborne ──────────────────────────────────────────────────────────
    "aviris": SensorPreset(
        name="aviris",
        description="NASA JPL AVIRIS classic (224 channels nominal; ~10 nm sampling, calibrated within 1 nm)",
        source="https://aviris.jpl.nasa.gov/",
        bands=224,
        start=400.0,
        stop=2500.0,
        uniform=False,
    ),
    "aviris_ng": SensorPreset(
        name="aviris_ng",
        description="NASA JPL AVIRIS-NG (425 bands, uniform 5 nm, 376.86-2496.86 nm)",
        source="https://avirisng.jpl.nasa.gov/specifications.html",
        bands=425,
        exact=_uniform(376.86, 5.0, 425),
        uniform=True,
    ),
    "hyspex_vnir": SensorPreset(
        name="hyspex_vnir",
        description="HySpex VNIR-1800 (186 usable bands, uniform 3.19344621 nm, 405.70-996.49 nm)",
        source="https://github.com/evan-greenbrg/isofit-hyspex",
        bands=186,
        exact=_uniform(405.7000607, 3.19344621, 186),
        uniform=True,
    ),
    "hyspex_swir": SensorPreset(
        name="hyspex_swir",
        description="HySpex SWIR-384 (288 bands, uniform 5.448840168 nm, 952.83-2516.64 nm)",
        source="https://github.com/evan-greenbrg/isofit-hyspex",
        bands=288,
        exact=_uniform(952.8263378, 5.448840168, 288),
        uniform=True,
        bad_bands=((1334.25, 1437.77), (1802.85, 1977.21), (2451.26, 2516.64)),
    ),
    "casi_1500": SensorPreset(
        name="casi_1500",
        description="ITRES CASI-1500 (up to 288 VNIR bands, 380-1050 nm, ~2.4 nm sampling; configurable)",
        source="https://itres.com/sensor-line-1-high-fidelity-hyperspectral-sensor-system/",
        bands=288,
        start=380.0,
        stop=1050.0,
        uniform=False,
    ),
    "aisafenix": SensorPreset(
        name="aisafenix",
        description="SPECIM AisaFENIX (up to 620 bands, 380-2500 nm, dual VNIR+SWIR spectrograph)",
        source="https://www.specim.com/products/aisafenix/",
        bands=620,
        start=380.0,
        stop=2500.0,
        uniform=False,
    ),
    # ── Satellite / spaceborne ────────────────────────────────────────────
    "emit": SensorPreset(
        name="emit",
        description="NASA EMIT (285 bands, 381-2497.5 nm; non-uniform per-granule grid, read from product NetCDF)",
        source="https://lpdaac.usgs.gov/products/emitl2arflv001/",
        bands=285,
        start=381.0,
        stop=2497.5,
        uniform=False,
        bad_bands=((1325.0, 1435.0), (1770.0, 1962.0)),
    ),
    "enmap": SensorPreset(
        name="enmap",
        description="DLR EnMAP (244 bands: 92 VNIR + 152 SWIR, 418-2445 nm; non-uniform)",
        source="https://www.enmap.org/data/doc/EnMAP_Specs.pdf",
        bands=244,
        start=418.0,
        stop=2445.0,
        uniform=False,
    ),
    "prisma": SensorPreset(
        name="prisma",
        description="ASI PRISMA (239 bands: 66 VNIR + 173 SWIR, 400-2505 nm; non-uniform)",
        source="https://prisma.asi.it/missionselect/docs/PRISMA%20Product%20Specifications_Is2_3.pdf",
        bands=239,
        start=400.0,
        stop=2505.0,
        uniform=False,
    ),
    "hyperion": SensorPreset(
        name="hyperion",
        description="NASA EO-1 Hyperion (242 bands, 220 unique, ~196 calibrated; useful 400-2500 nm)",
        source="https://eo1.gsfc.nasa.gov/new/validationReport/Technology/Documents/EO1_USG_Final_508.pdf",
        bands=220,
        start=400.0,
        stop=2500.0,
        uniform=False,
    ),
    "hico": SensorPreset(
        name="hico",
        description="NASA HICO (128 bands, uniform 5.728 nm, 352.528-1079.984 nm)",
        source="https://oceancolor.gsfc.nasa.gov/data/hico/",
        bands=128,
        exact=_uniform(352.528, 5.728, 128),
        uniform=True,
    ),
    "desis": SensorPreset(
        name="desis",
        description="DLR DESIS (235 VNIR bands, 400-1000 nm; per-product centers)",
        source="https://www.dlr.de/eoc/en/",
        bands=235,
        start=400.0,
        stop=1000.0,
        uniform=False,
    ),
    "m3": SensorPreset(
        name="m3",
        description="Chandrayaan-1 Moon Mineralogy Mapper (260 target-mode bands, 430-3000 nm; non-linear)",
        source="https://pds-imaging.jpl.nasa.gov/portal/m3_mission.html",
        bands=260,
        start=430.0,
        stop=3000.0,
        uniform=False,
    ),
}


def _preset_grid(name: str, expected_bands: int) -> tuple[list[float], str] | None:
    preset = SENSOR_PRESETS.get(name)
    if preset is None:
        return None
    if preset.bands != expected_bands:
        return None
    return preset.wavelengths(), preset.name


def _auto_grid(expected_bands: int) -> tuple[list[float], str] | None:
    # If the raster band count matches a known sensor grid exactly, reuse it
    # so browser uploads (which never send wavelengths) just work.
    for preset in SENSOR_PRESETS.values():
        if preset.bands == expected_bands:
            return preset.wavelengths(), preset.name
    return None


def _generic_grid(expected_bands: int) -> tuple[list[float], str]:
    """Fallback: synthesize a linear VNIR-SWIR grid when no sensor matches.

    Used when the cube has no wavelength metadata and its band count matches
    no known sensor preset. 400-2500 nm is the standard VNIR-SWIR
    hyperspectral range; the grid is approximate and labeled ``generic`` so
    callers know the bands were not read from real sensor calibration.
    """
    return list(np.linspace(400.0, 2500.0, expected_bands)), "generic"


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

    return _generic_grid(expected_bands)


def list_sensor_presets() -> list[dict[str, object]]:
    """Expose sensor preset metadata (used by CLI/docs, never paths)."""
    return [
        {
            "name": preset.name,
            "description": preset.description,
            "source": preset.source,
            "bands": preset.bands,
            "uniform": preset.uniform,
            "bad_bands": list(preset.bad_bands),
        }
        for preset in SENSOR_PRESETS.values()
    ]
