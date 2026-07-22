from __future__ import annotations

import numpy as np

from open_ore_mapper.sunsal import should_use_sunsal, sunsal


def test_sunsal_pure_pixel_returns_sparse_solution() -> None:
    rng = np.random.default_rng(42)
    A = rng.normal(size=(20, 10)).astype(np.float64)
    y = A[3:4]

    abundances = sunsal(y, A)

    assert abs(float(abundances[0, 3]) - 1.0) < 0.05
    assert np.max(np.abs(abundances[0, np.arange(20) != 3])) < 0.05
    assert np.sum(np.abs(abundances) > 0.01) <= 3


def test_sunsal_fifty_fifty_mixture() -> None:
    rng = np.random.default_rng(42)
    A = rng.normal(size=(20, 10)).astype(np.float64)
    y = (0.5 * A[1:2] + 0.5 * A[2:3]).astype(np.float64)

    abundances = sunsal(y, A)

    assert abs(float(abundances[0, 1]) - 0.5) < 0.1
    assert abs(float(abundances[0, 2]) - 0.5) < 0.1
    assert abs(float(np.sum(abundances[0]) - 1.0)) < 0.15


def test_sunsal_sparsity_increases_with_lambda() -> None:
    rng = np.random.default_rng(42)
    A = rng.normal(size=(20, 10)).astype(np.float64)
    y = rng.uniform(size=(1, 10)).astype(np.float64)

    x_low = sunsal(y, A, lambda_=0.001)
    x_high = sunsal(y, A, lambda_=0.1)

    count_low = int(np.sum(np.abs(x_low) > 0.01))
    count_high = int(np.sum(np.abs(x_high) > 0.01))

    assert count_high <= count_low


def test_sunsal_converges_within_max_iter() -> None:
    rng = np.random.default_rng(42)
    A = rng.normal(size=(20, 10)).astype(np.float64)
    y = (A[3:4] + 0.01 * rng.normal(size=(1, 10))).astype(np.float64)

    result = sunsal(y, A, max_iter=200, tol=1e-4)

    assert result.shape == (1, 20)
    assert np.all(result >= 0)
    assert abs(float(result[0, 3]) - 1.0) < 0.2


def test_sunsal_output_shape_correct() -> None:
    rng = np.random.default_rng(42)
    A = rng.normal(size=(20, 15)).astype(np.float64)
    pixels = rng.normal(size=(10, 15)).astype(np.float64)

    result = sunsal(pixels, A)

    assert result.shape == (10, 20)


def test_should_use_sunsal_threshold() -> None:
    assert should_use_sunsal(51) is True
    assert should_use_sunsal(49) is False
    assert should_use_sunsal(50) is True
