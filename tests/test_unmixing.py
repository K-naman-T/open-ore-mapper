import numpy as np
import pytest

from spectral_matching.unmixing import estimate_nnls_abundances


def test_pure_reference_maps_to_single_high_abundance() -> None:
    refs = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    pixels = np.array([[1.0, 0.0]], dtype=np.float32)
    abundances = estimate_nnls_abundances(pixels, refs)
    assert abundances.shape == (1, 2)
    assert float(abundances[0, 0]) > 0.99
    assert float(abundances[0, 1]) < 0.01


def test_mixed_pixel_abundance_is_normalized() -> None:
    refs = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    pixels = np.array([[0.25, 0.75]], dtype=np.float32)
    abundances = estimate_nnls_abundances(pixels, refs)
    assert float(abundances.sum()) == pytest.approx(1.0)
    assert float(abundances[0, 1]) > float(abundances[0, 0])


def test_single_reference_abundance_is_one() -> None:
    refs = np.array([[1.0, 0.0]], dtype=np.float32)
    pixels = np.array([[0.5, 0.0]], dtype=np.float32)
    abundances = estimate_nnls_abundances(pixels, refs)
    assert abundances.shape == (1, 1)
    assert float(abundances[0, 0]) == pytest.approx(1.0)


def test_many_endmembers_abundance_sum_is_positive() -> None:
    n = 30
    refs = np.random.default_rng(0).normal(size=(n, 5)).astype(np.float32)
    pixels = np.random.default_rng(1).normal(size=(3, 5)).astype(np.float32)
    abundances = estimate_nnls_abundances(pixels, refs)
    assert abundances.shape == (3, n)
    assert np.all(abundances >= -1e-6)
    assert np.all(np.isfinite(abundances))


def test_abundance_sum_does_not_exceed_one() -> None:
    refs = np.array([[1.0, 0.0], [2.0, 0.0]], dtype=np.float32)
    pixels = np.array([[3.0, 0.0]], dtype=np.float32)
    abundances = estimate_nnls_abundances(pixels, refs)
    assert float(abundances.sum()) <= 1.0 + 1e-6
