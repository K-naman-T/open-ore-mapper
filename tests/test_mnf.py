"""Unit tests for Minimum Noise Fraction (MNF) transform."""

from __future__ import annotations

import numpy as np
import pytest

from open_ore_mapper.mnf import apply_mnf, mnf_data_mean, mnf_transform


def _synthetic_signal_noise_cube(
    height: int = 40,
    width: int = 40,
    n_bands: int = 30,
    n_signal: int = 3,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Build cube = low-rank spatial signal + spatially uncorrelated noise.

    Signal lives in a known n_signal-dimensional subspace so top MNF
    components should capture most signal energy.
    """
    rng = np.random.default_rng(seed)
    # Signal basis (orthonormal-ish band vectors)
    basis = rng.normal(size=(n_bands, n_signal)).astype(np.float64)
    basis, _ = np.linalg.qr(basis)

    # Smooth spatial abundance maps
    yy, xx = np.mgrid[0:height, 0:width]
    maps = np.stack(
        [
            np.sin(2 * np.pi * xx / width),
            np.cos(2 * np.pi * yy / height),
            np.sin(2 * np.pi * (xx + yy) / (width + height)),
        ][:n_signal],
        axis=-1,
    )  # HxWxS
    signal = maps @ basis.T  # HxWxB

    # Spatially uncorrelated noise with band-dependent scale
    noise_scale = 0.05 + 0.15 * rng.random(n_bands)
    noise = rng.normal(size=(height, width, n_bands)) * noise_scale

    cube = (signal + noise).astype(np.float32)
    return cube, basis.astype(np.float64)


def test_mnf_output_shapes() -> None:
    cube, _ = _synthetic_signal_noise_cube()
    mask = np.ones(cube.shape[:2], dtype=bool)
    n_comp = 10
    transformed, tmat = mnf_transform(cube, mask, n_components=n_comp)
    assert transformed.shape == (cube.shape[0], cube.shape[1], n_comp)
    assert tmat.shape == (cube.shape[2], n_comp)
    assert transformed.dtype == np.float32
    assert np.all(np.isfinite(transformed))


def test_mnf_n_components_capped_at_bands() -> None:
    cube, _ = _synthetic_signal_noise_cube(n_bands=8)
    mask = np.ones(cube.shape[:2], dtype=bool)
    transformed, tmat = mnf_transform(cube, mask, n_components=50)
    assert transformed.shape[2] == 8
    assert tmat.shape == (8, 8)


def test_mnf_signal_energy_in_top_components() -> None:
    """Signal subspace energy should concentrate in the first few MNF bands."""
    n_signal = 3
    cube, _basis = _synthetic_signal_noise_cube(
        height=50, width=50, n_bands=40, n_signal=n_signal, seed=7
    )
    mask = np.ones(cube.shape[:2], dtype=bool)
    transformed, _tmat = mnf_transform(cube, mask, n_components=40)

    # Variance per MNF component over space
    flat = transformed.reshape(-1, transformed.shape[2])
    var = np.var(flat, axis=0)
    total = float(np.sum(var))
    assert total > 0
    top_k = float(np.sum(var[:n_signal]))
    # Top n_signal components should hold a large share of total variance
    # (noise-whitened signal concentrates in high-SNR axes)
    assert top_k / total > 0.4, f"top-{n_signal} variance fraction={top_k/total:.3f}"

    # First component should have more variance than last
    assert var[0] > var[-1]


def test_mnf_apply_matches_cube_projection() -> None:
    cube, _ = _synthetic_signal_noise_cube(height=16, width=16, n_bands=20, seed=1)
    mask = np.ones(cube.shape[:2], dtype=bool)
    transformed, tmat = mnf_transform(cube, mask, n_components=8)
    mu = mnf_data_mean(cube, mask)

    # Reproject a few pixels with apply_mnf
    pixels = cube[0:3, 0:3, :].reshape(-1, cube.shape[2])
    expected = transformed[0:3, 0:3, :].reshape(-1, 8)
    got = apply_mnf(pixels, tmat, data_mean=mu)
    np.testing.assert_allclose(got, expected, rtol=1e-4, atol=1e-4)


def test_mnf_library_projection_shape() -> None:
    cube, _ = _synthetic_signal_noise_cube(n_bands=15)
    mask = np.ones(cube.shape[:2], dtype=bool)
    _tr, tmat = mnf_transform(cube, mask, n_components=5)
    mu = mnf_data_mean(cube, mask)
    refs = np.random.default_rng(0).normal(size=(4, 15)).astype(np.float32)
    proj = apply_mnf(refs, tmat, data_mean=mu)
    assert proj.shape == (4, 5)
    assert np.all(np.isfinite(proj))


def test_mnf_empty_mask_returns_zeros() -> None:
    cube = np.ones((5, 5, 10), dtype=np.float32)
    mask = np.zeros((5, 5), dtype=bool)
    transformed, tmat = mnf_transform(cube, mask, n_components=4)
    assert transformed.shape == (5, 5, 4)
    assert tmat.shape == (10, 4)
    assert np.allclose(transformed, 0.0)


def test_mnf_valid_mask_excludes_invalid() -> None:
    cube, _ = _synthetic_signal_noise_cube(height=20, width=20, n_bands=12, seed=3)
    mask = np.ones((20, 20), dtype=bool)
    mask[:5, :] = False
    transformed, tmat = mnf_transform(cube, mask, n_components=6)
    assert transformed.shape == (20, 20, 6)
    assert tmat.shape == (12, 6)
    assert np.all(np.isfinite(transformed))


def test_apply_mnf_1d_spectrum() -> None:
    tmat = np.eye(6, 3, dtype=np.float64)
    spec = np.arange(6, dtype=np.float32)
    out = apply_mnf(spec, tmat)
    assert out.shape == (3,)
    np.testing.assert_allclose(out, spec[:3], atol=1e-6)


def test_apply_mnf_band_mismatch_raises() -> None:
    tmat = np.eye(5, 2)
    with pytest.raises(ValueError, match="bands"):
        apply_mnf(np.ones(3), tmat)
