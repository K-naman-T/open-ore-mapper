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
    options = MatchOptions(
        classes=["hematite_demo", "goethite_demo", "jarosite_demo"],
        wavelengths=[450.0, 550.0, 650.0],
        classifier="auto",
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
    assert "sam" in result.model_used or "auto" in result.warnings[0] if result.warnings else True
