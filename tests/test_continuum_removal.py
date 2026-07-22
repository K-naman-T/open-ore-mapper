from __future__ import annotations

from typing import cast

import numpy as np
import pytest
from numpy.typing import NDArray

from open_ore_mapper.continuum_removal import (
    AbsorptionFeature,
    FeatureLibrary,
    extract_absorption_features,
    extract_absorption_features_batch,
    hull_quotient,
    hull_quotient_batch,
    match_features,
    match_features_batch,
)
from open_ore_mapper.spectral_library import SpectralLibrary


def test_hull_quotient_on_flat_spectrum_returns_ones() -> None:
    wavelengths = np.array([500, 1000, 1500, 2000, 2500], dtype=np.float32)
    reflectance = np.array([0.5, 0.5, 0.5, 0.5, 0.5], dtype=np.float32)
    result = hull_quotient(wavelengths, reflectance)
    expected = np.ones(5, dtype=np.float32)
    np.testing.assert_array_almost_equal(result, expected)


def test_hull_quotient_on_straight_line_spectrum_returns_ones() -> None:
    wavelengths = np.array([500, 1000, 1500, 2000, 2500], dtype=np.float32)
    reflectance = np.array([0.3, 0.4, 0.5, 0.6, 0.7], dtype=np.float32)
    result = hull_quotient(wavelengths, reflectance)
    expected = np.ones(5, dtype=np.float32)
    np.testing.assert_array_almost_equal(result, expected)


def test_hull_quotient_with_absorption_feature() -> None:
    wavelengths = np.linspace(2000, 2400, 50, dtype=np.float32)
    center = 2200.0
    sigma = 20.0
    gaussian = np.exp(-0.5 * ((wavelengths - center) / sigma) ** 2)
    reflectance = 0.5 - 0.2 * gaussian

    result = hull_quotient(wavelengths, reflectance)

    min_idx = int(np.argmin(result))
    assert abs(float(wavelengths[min_idx]) - 2200.0) < 10.0
    assert float(result[min_idx]) < 1.0
    assert float(result[0]) == pytest.approx(1.0, abs=0.01)
    assert float(result[-1]) == pytest.approx(1.0, abs=0.01)


def test_extract_features_finds_known_absorption() -> None:
    wavelengths = np.linspace(2000, 2400, 101, dtype=np.float32)
    center = 2200.0
    sigma = 15.0
    depth = 0.2
    cr = np.ones_like(wavelengths)
    cr -= depth * np.exp(-0.5 * ((wavelengths - center) / sigma) ** 2)

    features = extract_absorption_features(wavelengths, cr)

    assert len(features) == 1
    assert abs(features[0].position - 2200.0) < 5.0
    assert abs(features[0].depth - 0.2) < 0.05


def test_extract_features_requires_minimum_depth() -> None:
    wavelengths = np.linspace(2000, 2400, 101, dtype=np.float32)
    cr = np.ones_like(wavelengths, dtype=np.float32)
    cr -= 0.01 * np.exp(-0.5 * ((wavelengths - 2200.0) / 15.0) ** 2)

    features = extract_absorption_features(wavelengths, cr, min_depth=0.02)
    assert len(features) == 0


def test_match_features_same_mineral_scores_high() -> None:
    wavelengths = np.linspace(2000, 2400, 101, dtype=np.float32)
    gaussian1 = np.exp(-0.5 * ((wavelengths - 2200.0) / 15.0) ** 2)
    gaussian2 = np.exp(-0.5 * ((wavelengths - 2202.0) / 15.0) ** 2)

    cr1: NDArray[np.float32] = np.ones_like(wavelengths) - 0.2 * gaussian1
    cr2: NDArray[np.float32] = np.ones_like(wavelengths) - 0.19 * gaussian2

    features1 = extract_absorption_features(wavelengths, cr1)
    features2 = extract_absorption_features(wavelengths, cr2)

    lib = FeatureLibrary(mineral_names=["test_mineral"], features=[features2])
    scores = match_features(features1, lib)
    assert float(scores[0]) > 0.8


def test_match_features_different_mineral_scores_low() -> None:
    wl_oxide = np.linspace(400, 1000, 121, dtype=np.float32)
    wl_carb = np.linspace(2000, 2500, 101, dtype=np.float32)

    cr_oxide: NDArray[np.float32] = np.ones_like(wl_oxide)
    cr_oxide -= 0.3 * np.exp(-0.5 * ((wl_oxide - 500.0) / 30.0) ** 2)
    cr_oxide -= 0.2 * np.exp(-0.5 * ((wl_oxide - 900.0) / 40.0) ** 2)

    cr_carb: NDArray[np.float32] = np.ones_like(wl_carb)
    cr_carb -= 0.25 * np.exp(-0.5 * ((wl_carb - 2340.0) / 20.0) ** 2)

    features_oxide = extract_absorption_features(wl_oxide, cr_oxide, min_depth=0.02)
    features_carb = extract_absorption_features(wl_carb, cr_carb, min_depth=0.02)

    lib = FeatureLibrary(mineral_names=["carbonate"], features=[features_carb])
    scores = match_features(features_oxide, lib)
    assert float(scores[0]) < 0.5


def test_feature_library_from_spectral_library_has_correct_length() -> None:
    wavelengths = np.linspace(2000, 2500, 50, dtype=np.float32)
    spectra = np.zeros((3, 50), dtype=np.float32)
    for i in range(3):
        dip = 0.1 * np.exp(-0.5 * ((wavelengths - (2100.0 + i * 150.0)) / 20.0) ** 2)
        spectra[i] = 0.5 - dip

    lib = SpectralLibrary(
        names=["mineral_a", "mineral_b", "mineral_c"],
        wavelengths=wavelengths,
        spectra=cast(NDArray[np.float32], spectra),
        source="test",
    )

    feature_lib = FeatureLibrary.from_spectral_library(lib)
    assert len(feature_lib.mineral_names) == 3
    assert len(feature_lib.features) == 3


def test_hull_quotient_batch_matches_single() -> None:
    rng = np.random.default_rng(42)
    wavelengths = np.linspace(2000, 2500, 50, dtype=np.float32)
    spectra = np.zeros((20, 50), dtype=np.float32)
    for i in range(20):
        center = 2100.0 + i * 20.0
        dip = 0.1 * np.exp(-0.5 * ((wavelengths - center) / 20.0) ** 2)
        spectra[i] = 0.5 - dip + rng.normal(0, 0.01, 50).astype(np.float32)

    batch_result = hull_quotient_batch(wavelengths, spectra)
    assert batch_result.shape == (20, 50)

    for i in range(20):
        single_result = hull_quotient(wavelengths, spectra[i])
        np.testing.assert_array_almost_equal(batch_result[i], single_result, decimal=6)


def test_full_pipeline_vectorized_matches_loop() -> None:
    rng = np.random.default_rng(12345)
    wavelengths = np.linspace(2000, 2500, 50, dtype=np.float32)
    n_spectra = 100
    spectra = np.zeros((n_spectra, 50), dtype=np.float32)
    for i in range(n_spectra):
        center = 2100.0 + rng.uniform(0, 400)
        depth = rng.uniform(0.05, 0.3)
        dip = depth * np.exp(-0.5 * ((wavelengths - center) / 20.0) ** 2)
        spectra[i] = 1.0 - dip

    mineral_names = ["qz", "kln", "ill", "sme", "hly", "gth"]
    lib_features: list[list[AbsorptionFeature]] = []
    for name in mineral_names:
        pos = 2100.0 + (hash(name) % 400)
        lib_features.append([
            AbsorptionFeature(position=float(pos), depth=0.2, fwhm=30.0, asymmetry=1.0),
        ])
    library = FeatureLibrary(mineral_names=mineral_names, features=lib_features)

    hq_batch = hull_quotient_batch(wavelengths, spectra)
    feats_batch = extract_absorption_features_batch(wavelengths, hq_batch)
    scores_batch = match_features_batch(feats_batch, library)
    assert scores_batch.shape == (n_spectra, 6)

    scores_loop = np.zeros((n_spectra, 6), dtype=np.float32)
    for i in range(n_spectra):
        hq = hull_quotient(wavelengths, spectra[i])
        feats = extract_absorption_features(wavelengths, hq)
        scores_loop[i] = match_features(feats, library)

    np.testing.assert_array_almost_equal(scores_batch, scores_loop, decimal=6)
