from __future__ import annotations

import numpy as np

from spectral_matching.engine import SpectralMatcher
from spectral_matching.schemas import MatchOptions


def test_auto_large_library() -> None:
    result = SpectralMatcher._auto_classifier(n_classes=60, n_bands=100)
    assert result == "mnf_mtmf"


def test_auto_many_bands() -> None:
    result = SpectralMatcher._auto_classifier(n_classes=10, n_bands=200)
    assert result == "fuse_classical"


def test_auto_default() -> None:
    result = SpectralMatcher._auto_classifier(n_classes=5, n_bands=50)
    assert result == "sam"


def test_auto_classifier_in_match_options(tmp_path) -> None:
    csv_path = tmp_path / "lib.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,450,0.5\n"
        "class_a,550,0.4\n"
        "class_a,650,0.3\n"
        "class_b,450,0.3\n"
        "class_b,550,0.4\n"
        "class_b,650,0.5\n"
        "class_c,450,0.2\n"
        "class_c,550,0.3\n"
        "class_c,650,0.4\n"
        "class_d,450,0.4\n"
        "class_d,550,0.5\n"
        "class_d,650,0.6\n"
        "class_e,450,0.6\n"
        "class_e,550,0.5\n"
        "class_e,650,0.4\n"
    )
    options = MatchOptions(
        spectral_library=str(csv_path),
        wavelengths=[450.0, 550.0, 650.0],
        classifier="auto",
        min_confidence=0.0,
        sam_threshold_deg=180.0,
    )
    cube = np.random.default_rng(42).random((5, 5, 3)).astype(np.float32)
    matcher = SpectralMatcher()
    result = matcher.predict_cube(
        cube,
        [450.0, 550.0, 650.0],
        options,
        sensor="manual",
    )
    assert result.status == "success"
    assert result.model_used != ""


def test_auto_edge_empty_classes() -> None:
    result = SpectralMatcher._auto_classifier(n_classes=0, n_bands=10)
    assert isinstance(result, str)
    assert len(result) > 0
