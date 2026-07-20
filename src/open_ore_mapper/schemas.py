from __future__ import annotations

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


@dataclass(frozen=True)
class MapperOptions:
    wavelengths: list[float] | None = None
    sensor: str = "cubert_ultris_s5"
    minerals: list[str] = field(default_factory=lambda: list(DEFAULT_DEMO_MINERALS))
    spectral_library: str | None = None
    sam_threshold_deg: float = 12.0
    min_confidence: float = 0.65
    tile_size: int = 128
    normalization: str = "l2"
    excluded_band_indices: list[int] = field(default_factory=list)
    min_band_valid_fraction: float = 0.5


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
    quality_report: RasterQualityReport
