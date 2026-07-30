from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
import tifffile
from PIL import Image

from spectral_matching.schemas import MatchOptions
from spectral_matching.engine import SpectralMatcher


def _build_test_scene_and_library(tmp_path: Path):
    n_bands = 285
    wavelengths = list(np.linspace(400.0, 2500.0, n_bands))
    H, W = 200, 200

    target_classes = [
        "ClassA", "ClassB", "ClassC", "ClassD", "ClassE",
    ]

    rng = np.random.default_rng(42)
    spectra = rng.uniform(0.05, 0.8, (len(target_classes), n_bands)).astype(np.float32)

    csv_path = tmp_path / "spectral_library.csv"
    lines = ["name,wavelength,reflectance"]
    for i, name in enumerate(target_classes):
        for j in range(n_bands):
            lines.append(f"{name},{wavelengths[j]},{spectra[i, j]}")
    csv_path.write_text("\n".join(lines))

    cube = np.full((H, W, n_bands), 0.3, dtype=np.float32)
    cube += rng.normal(0, 0.005, (H, W, n_bands)).astype(np.float32)

    def _assign(y0, y1, x0, x1, name):
        idx = target_classes.index(name)
        spectrum = spectra[idx]
        patch = np.broadcast_to(spectrum, (y1 - y0, x1 - x0, n_bands)).copy()
        patch += rng.normal(0, 0.005, (y1 - y0, x1 - x0, n_bands)).astype(np.float32)
        cube[y0:y1, x0:x1, :] = np.clip(patch, 0.0, 1.0)

    _assign(0, 90, 0, 90, "ClassA")
    _assign(0, 90, 110, 200, "ClassB")
    _assign(110, 200, 0, 90, "ClassC")
    _assign(110, 200, 110, 200, "ClassD")
    _assign(90, 110, 90, 110, "ClassE")
    cube = np.clip(cube, 0.0, 1.0)

    tif_path = tmp_path / "scene.tif"
    tifffile.imwrite(tif_path, cube, photometric="minisblack")

    return tif_path, csv_path, wavelengths, cube, target_classes


def _opts(wavelengths, classes, csv_path, **kw):
    base = dict(
        wavelengths=wavelengths,
        sensor="manual",
        classes=classes,
        spectral_library=str(csv_path),
        min_confidence=0.0,
        sam_threshold_deg=180.0,
        min_band_valid_fraction=0.0,
    )
    base.update(kw)
    return MatchOptions(**base)


class TestE2ESpectralMatching:
    """End-to-end spectral matching tests."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path) -> None:
        (
            self.tif_path,
            self.csv_path,
            self.wavelengths,
            self.cube,
            self.classes,
        ) = _build_test_scene_and_library(tmp_path)
        self.H, self.W, _ = self.cube.shape

    def test_classifiers_run_without_crashing(self) -> None:
        opts_sam = _opts(self.wavelengths, self.classes, self.csv_path, classifier="sam")
        r1 = SpectralMatcher().predict_file(self.tif_path, opts_sam)
        assert r1.status == "success"

        opts_mtmf = _opts(self.wavelengths, self.classes, self.csv_path, classifier="sam", use_mtmf=True)
        r2 = SpectralMatcher().predict_file(self.tif_path, opts_mtmf)
        assert r2.status == "success"

    def test_classified_pixel_count_is_nonzero(self) -> None:
        opts = _opts(self.wavelengths, self.classes, self.csv_path)
        result = SpectralMatcher().predict_file(self.tif_path, opts)
        total = sum(s.count for s in result.statistics.values())
        assert total > 1000

    def test_class_map_has_correct_spatial_dimensions(self) -> None:
        opts = _opts(self.wavelengths, self.classes, self.csv_path)
        result = SpectralMatcher().predict_file(self.tif_path, opts)
        b64 = result.output_image.removeprefix("data:image/png;base64,")
        img = Image.open(io.BytesIO(__import__("base64").b64decode(b64)))
        assert img.size == (self.W, self.H)

    def test_confidence_in_valid_range(self) -> None:
        opts = _opts(self.wavelengths, self.classes, self.csv_path)
        result = SpectralMatcher().predict_file(self.tif_path, opts)
        for stat in result.statistics.values():
            assert 0.0 <= stat.mean_confidence <= 1.0

    def test_output_images_are_valid_png(self) -> None:
        opts = _opts(self.wavelengths, self.classes, self.csv_path)
        result = SpectralMatcher().predict_file(self.tif_path, opts)
        assert result.output_image.startswith("data:image/png;base64,")
        assert result.confidence_image.startswith("data:image/png;base64,")
        assert result.top_abundance_image.startswith("data:image/png;base64,")

    def test_statistics_sum_does_not_exceed_total(self) -> None:
        opts = _opts(self.wavelengths, self.classes, self.csv_path)
        result = SpectralMatcher().predict_file(self.tif_path, opts)
        total_classified = sum(s.count for s in result.statistics.values())
        assert total_classified <= self.H * self.W

    def test_mtmf_produces_mf_and_infeas_arrays(self) -> None:
        opts = _opts(self.wavelengths, self.classes, self.csv_path, use_mtmf=True)
        result = SpectralMatcher().predict_file(self.tif_path, opts)
        assert result.status == "success"

    def test_no_classes_produces_error(self) -> None:
        opts = _opts(self.wavelengths, [], self.csv_path)
        with pytest.raises(ValueError, match="At least one class is required"):
            SpectralMatcher().predict_file(self.tif_path, opts)
