from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from open_ore_mapper.continuum_removal import hull_quotient
from open_ore_mapper.mineral_features import all_mineral_names, lookup_mineral
from open_ore_mapper.sff import SffResult, sff_classify, sff_classify_cube, sff_classify_details


def _gaussian_cr(
    wavelengths: NDArray[np.float32],
    absorptions: list[tuple[float, float, float]],
) -> NDArray[np.float32]:
    cr = np.ones_like(wavelengths, dtype=np.float32)
    for position, depth, sigma in absorptions:
        cr -= depth * np.exp(-0.5 * ((wavelengths - position) / sigma) ** 2)
    return cr


def _make_reflectance(
    wavelengths: NDArray[np.float32],
    absorptions: list[tuple[float, float, float]],
    base: float = 0.5,
) -> NDArray[np.float32]:
    ref = np.full_like(wavelengths, base, dtype=np.float32)
    for position, depth, sigma in absorptions:
        ref -= depth * np.exp(-0.5 * ((wavelengths - position) / sigma) ** 2)
    return ref


def test_kaolinite_doublet_detected() -> None:
    wavelengths = np.linspace(400, 2500, 500, dtype=np.float32)
    ref = _make_reflectance(wavelengths, [
        (1400.0, 0.10, 12.0),
        (2160.0, 0.12, 12.0),   # distinct shoulder
        (2200.0, 0.22, 15.0),   # main peak, pair visible as doublet
        (2320.0, 0.05, 12.0),
    ])
    cr = hull_quotient(wavelengths, ref)
    result = sff_classify_details(wavelengths, cr, ["kaolinite", "dickite"])
    assert result is not None
    assert result.mineral == "kaolinite"
    assert result.score > 0.5


def test_calcite_distinguished_from_dolomite() -> None:
    wavelengths = np.linspace(1800, 2510, 300, dtype=np.float32)

    calcite_ref = _make_reflectance(wavelengths, [
        (1870.0, 0.05, 12.0),
        (2000.0, 0.04, 12.0),
        (2160.0, 0.05, 12.0),
        (2340.0, 0.30, 15.0),
        (2500.0, 0.10, 12.0),
    ])
    calcite_cr = hull_quotient(wavelengths, calcite_ref)
    assert sff_classify(wavelengths, calcite_cr, ["calcite", "dolomite"]) == "calcite"

    dolomite_ref = _make_reflectance(wavelengths, [
        (2320.0, 0.30, 15.0),
        (2250.0, 0.05, 12.0),
        (2480.0, 0.10, 12.0),
    ])
    dolomite_cr = hull_quotient(wavelengths, dolomite_ref)
    assert sff_classify(wavelengths, dolomite_cr, ["calcite", "dolomite"]) == "dolomite"


def test_hematite_distinguished_from_goethite() -> None:
    wavelengths = np.linspace(400, 1300, 300, dtype=np.float32)

    hematite_cr = _gaussian_cr(wavelengths, [
        (530.0, 0.20, 20.0),
        (650.0, 0.08, 15.0),
        (860.0, 0.30, 30.0),
    ])
    assert sff_classify(wavelengths, hematite_cr, ["hematite", "goethite"]) == "hematite"

    goethite_cr = _gaussian_cr(wavelengths, [
        (500.0, 0.15, 20.0),
        (650.0, 0.05, 15.0),
        (930.0, 0.25, 40.0),
    ])
    assert sff_classify(wavelengths, goethite_cr, ["hematite", "goethite"]) == "goethite"


def test_alunite_distinguished_from_kaolinite() -> None:
    wavelengths = np.linspace(1300, 2510, 400, dtype=np.float32)

    alunite_cr = _gaussian_cr(wavelengths, [
        (1480.0, 0.05, 12.0),
        (1760.0, 0.04, 12.0),
        (2165.0, 0.25, 12.0),
        (2200.0, 0.15, 12.0),
    ])
    assert sff_classify(wavelengths, alunite_cr, ["alunite", "kaolinite"]) == "alunite"

    kaolinite_cr = _gaussian_cr(wavelengths, [
        (2160.0, 0.08, 12.0),
        (2205.0, 0.30, 15.0),
    ])
    result = sff_classify(wavelengths, kaolinite_cr, ["alunite", "kaolinite"])
    assert result == "kaolinite"


def test_montmorillonite_distinguished_from_illite() -> None:
    wavelengths = np.linspace(1300, 2510, 400, dtype=np.float32)

    mont_cr = _gaussian_cr(wavelengths, [
        (1400.0, 0.15, 15.0),
        (1900.0, 0.30, 20.0),
        (2210.0, 0.25, 20.0),
        (2340.0, 0.05, 12.0),
    ])
    assert sff_classify(wavelengths, mont_cr, ["montmorillonite", "illite"]) == "montmorillonite"

    illite_cr = _gaussian_cr(wavelengths, [
        (1900.0, 0.03, 15.0),
        (2200.0, 0.25, 18.0),
        (2340.0, 0.10, 12.0),
        (2440.0, 0.05, 12.0),
    ])
    assert sff_classify(wavelengths, illite_cr, ["montmorillonite", "illite"]) == "illite"


def test_sff_output_contains_score_and_rationale() -> None:
    wavelengths = np.linspace(400, 2500, 500, dtype=np.float32)
    ref = _make_reflectance(wavelengths, [
        (2160.0, 0.08, 12.0),
        (2200.0, 0.30, 15.0),
    ])
    cr = hull_quotient(wavelengths, ref)
    result = sff_classify_details(wavelengths, cr)
    assert result is not None
    assert isinstance(result, SffResult)
    assert isinstance(result.mineral, str) and len(result.mineral) > 0
    assert isinstance(result.score, float) and 0.0 <= result.score <= 1.0
    assert isinstance(result.matched_features, list)
    assert isinstance(result.reason, str) and len(result.reason) > 0


def test_unclassifiable_spectrum_returns_none() -> None:
    wavelengths = np.linspace(400, 2500, 100, dtype=np.float32)
    cr = np.ones_like(wavelengths, dtype=np.float32)
    assert sff_classify(wavelengths, cr) is None
    assert sff_classify_details(wavelengths, cr) is None


def test_sff_matches_against_known_reference_spectra() -> None:
    wavelengths = np.linspace(400, 2500, 500, dtype=np.float32)

    for mineral in ["hematite", "kaolinite"]:
        profile = lookup_mineral(mineral)
        assert profile is not None
        absorptions: list[tuple[float, float, float]] = [
            (f.position_nm, (f.depth_min + f.depth_max) / 2.0, 12.0)
            for f in profile.features
        ]
        ref = _make_reflectance(wavelengths, absorptions)
        cr = hull_quotient(wavelengths, ref)
        result = sff_classify(wavelengths, cr)
        assert result == mineral, f"Expected {mineral}, got {result}"


def test_all_35_minerals_have_diagnostic_rules() -> None:
    names = all_mineral_names()
    assert len(names) == 35
    featureless = {
        "magnetite", "quartz", "coal", "pyrite",
        "unclassified_low_albedo", "unclassified_high_albedo",
    }
    for name in names:
        profile = lookup_mineral(name)
        assert profile is not None, f"{name} not found"
        if name not in featureless:
            assert len(profile.features) >= 1, f"{name} has no diagnostic features"
        else:
            assert len(profile.features) == 0, f"{name} should be featureless"
            assert len(profile.notes) > 0, f"{name} has no notes explaining featurelessness"


def test_sff_vectorized_matches_pixel_by_pixel() -> None:
    wavelengths = np.linspace(400, 2500, 200, dtype=np.float32)

    kao = _make_reflectance(wavelengths, [
        (1400.0, 0.15, 12.0), (2160.0, 0.08, 12.0),
        (2200.0, 0.30, 15.0), (2320.0, 0.05, 12.0), (2380.0, 0.05, 12.0),
    ])
    cal = _make_reflectance(wavelengths, [
        (1870.0, 0.05, 12.0), (2000.0, 0.04, 12.0),
        (2160.0, 0.05, 12.0), (2340.0, 0.30, 15.0), (2500.0, 0.10, 12.0),
    ])
    hem = _make_reflectance(wavelengths, [
        (530.0, 0.20, 20.0), (650.0, 0.08, 15.0), (860.0, 0.30, 30.0),
    ])
    flat = np.full_like(wavelengths, 0.5, dtype=np.float32)

    cube = np.stack([[kao, cal], [hem, flat]], dtype=np.float32)
    class_map, confidence = sff_classify_cube(cube, wavelengths)

    all_names = all_mineral_names()
    for h in range(2):
        for w in range(2):
            cr = hull_quotient(wavelengths, cube[h, w, :])
            single = sff_classify_details(wavelengths, cr)
            if single is not None:
                expected_idx = np.uint8(all_names.index(single.mineral) + 1)
                assert class_map[h, w] == expected_idx, f"Mismatch at ({h},{w})"
                assert confidence[h, w] == pytest.approx(single.score, abs=0.01)
            else:
                assert class_map[h, w] == 0, f"Expected 0 at ({h},{w})"
                assert confidence[h, w] == 0.0
