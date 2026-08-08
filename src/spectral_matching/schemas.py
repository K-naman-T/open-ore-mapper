from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MatchOptions:
    wavelengths: list[float] | None = None
    sensor: str = "aviris"
    classes: list[str] = field(default_factory=list)
    spectral_library: str | None = None
    spectral_library_bytes: bytes | None = field(default=None, compare=False)  # in-memory CSV for API uploads
    sam_threshold_deg: float = 12.0
    min_confidence: float = 0.65
    tile_size: int = 128
    normalization: str = "l2"
    excluded_band_indices: list[int] = field(default_factory=list)
    min_band_valid_fraction: float = 0.5
    classifier: str = "auto"
    use_mtmf: bool = False
    mf_threshold: float = 0.5
    infeas_threshold: float = 10.0
    n_mnf_components: int = 20


@dataclass(frozen=True)
class ClassStatistics:
    count: int
    percentage: float
    mean_confidence: float
    mean_abundance: float


@dataclass(frozen=True)
class MatchResult:
    status: str
    model_used: str
    sensor: str
    wavelengths: list[float]
    classes: list[str]
    output_image: str
    confidence_image: str
    top_abundance_image: str
    statistics: dict[str, ClassStatistics]
    warnings: list[str]
    downloads: dict[str, Any]
