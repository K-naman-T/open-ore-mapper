from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .qc import RasterQualityReport


DEFAULT_DEMO_MINERALS = [
    "hematite_demo",
    "goethite_demo",
    "jarosite_demo",
    "magnetite_demo",
    "limonite_demo",
    "ferrihydrite_demo",
]

DEFAULT_REAL_MINERALS = [
    "hematite", "goethite", "jarosite", "kaolinite", "montmorillonite",
    "illite", "calcite", "dolomite", "muscovite", "chlorite",
    "epidote", "alunite", "gypsum", "magnetite",
]


def validate_bbox(bbox: dict[str, Any]) -> dict[str, float]:
    """Validate a bbox dict. Returns normalized bbox with float values."""
    for key in ("west", "south", "east", "north"):
        if key not in bbox:
            raise ValueError(f"bbox missing required key: {key}")
        val = bbox[key]
        if not isinstance(val, (int, float)):
            raise ValueError(f"bbox.{key} must be a number, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"bbox.{key} must be finite")

    west = float(bbox["west"])
    south = float(bbox["south"])
    east = float(bbox["east"])
    north = float(bbox["north"])

    if not -180.0 <= west <= 180.0:
        raise ValueError(f"bbox.west must be in [-180, 180], got {west}")
    if not -180.0 <= east <= 180.0:
        raise ValueError(f"bbox.east must be in [-180, 180], got {east}")
    if not -90.0 <= south <= 90.0:
        raise ValueError(f"bbox.south must be in [-90, 90], got {south}")
    if not -90.0 <= north <= 90.0:
        raise ValueError(f"bbox.north must be in [-90, 90], got {north}")
    if west >= east:
        raise ValueError(f"bbox.west ({west}) must be less than bbox.east ({east})")
    if south >= north:
        raise ValueError(f"bbox.south ({south}) must be less than bbox.north ({north})")

    return {"west": west, "south": south, "east": east, "north": north}


@dataclass(frozen=True)
class MapperOptions:
    wavelengths: list[float] | None = None
    sensor: str = "cubert_ultris_s5"
    minerals: list[str] = field(default_factory=lambda: list(DEFAULT_REAL_MINERALS))
    spectral_library: str | None = None
    sam_threshold_deg: float = 12.0
    min_confidence: float = 0.65
    tile_size: int = 128
    normalization: str = "l2"
    excluded_band_indices: list[int] = field(default_factory=list)
    min_band_valid_fraction: float = 0.5
    classifier: str = "continuum_removal"
    use_ace: bool = False
    use_mtmf: bool = False
    mf_threshold: float = 0.5
    infeas_threshold: float = 10.0
    unmixing: str = "auto"
    vegetation_mask: bool = False
    ndvi_threshold: float = 0.3
    topographic_correct: bool = False
    dem_type: str = "COP30"
    solar_azimuth: float | None = None
    solar_elevation: float | None = None


@dataclass(frozen=True)
class MineralStatistics:
    count: int
    percentage: float
    mean_confidence: float
    mean_abundance: float


@dataclass(frozen=True)
class MapperResult:
    status: str
    model_used: str
    sensor: str
    wavelengths: list[float]
    minerals: list[str]
    output_image: str
    confidence_image: str
    top_abundance_image: str
    statistics: dict[str, MineralStatistics]
    warnings: list[str]
    downloads: dict[str, Any]
    quality_report: RasterQualityReport | None = None
