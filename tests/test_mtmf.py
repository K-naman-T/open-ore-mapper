from __future__ import annotations

import numpy as np
import pytest
from open_ore_mapper.mtmf import estimate_background_stats, mtmf, mtmf_detect


def test_mtmf_exact_target_returns_mf_one_infeas_zero() -> None:
    rng = np.random.default_rng(42)
    n_bands = 20
    cube = rng.normal(size=(10, 10, n_bands)).astype(np.float32)
    target = rng.normal(size=n_bands).astype(np.float32)
    target /= np.linalg.norm(target)
    cube[5, 5] = target.copy()

    valid_mask = np.ones((10, 10), dtype=bool)
    valid_mask[5, 5] = False

    targets_2d = target[np.newaxis, :]
    mf, infeas = mtmf(cube, targets_2d, valid_mask=valid_mask)

    assert mf[5, 5, 0] == pytest.approx(1.0, abs=1e-4)
    assert infeas[5, 5, 0] == pytest.approx(0.0, abs=1e-5)


def test_mtmf_background_pixel_returns_mf_near_zero() -> None:
    rng = np.random.default_rng(42)
    n_bands = 15
    cube = rng.normal(size=(10, 10, n_bands)).astype(np.float32)
    target = rng.normal(size=n_bands).astype(np.float32)
    target /= np.linalg.norm(target)

    targets_2d = target[np.newaxis, :]
    mf, _ = mtmf(cube, targets_2d)

    flat_mf = mf.ravel()
    # background MF scores should cluster near 0
    assert float(np.mean(flat_mf)) == pytest.approx(0.0, abs=0.1)


def test_mtmf_subpixel_mixture_detected() -> None:
    rng = np.random.default_rng(42)
    n_bands = 30

    bg_spectrum = np.linspace(0.5, 2.0, n_bands, dtype=np.float32)

    target = np.ones(n_bands, dtype=np.float32) * 1.5
    target[n_bands // 2] = 0.2
    target /= np.linalg.norm(target)

    mixed = (0.05 * target + 0.95 * (bg_spectrum / np.linalg.norm(bg_spectrum))).astype(
        np.float32,
    )

    bg_pixels = bg_spectrum[np.newaxis, :] + 0.1 * rng.normal(
        size=(224, n_bands)
    ).astype(np.float32)

    cube = np.zeros((15, 15, n_bands), dtype=np.float32)
    cube.reshape(-1, n_bands)[:-1] = bg_pixels
    cube[14, 14] = mixed

    targets_2d = target[np.newaxis, :]
    mf, _ = mtmf(cube, targets_2d)

    mf_value = float(mf[14, 14, 0])
    assert mf_value > 0.01, f"MF={mf_value} should detect 5% subpixel target"


def test_mtmf_output_shapes_correct() -> None:
    rng = np.random.default_rng(42)
    height, width, n_bands = 8, 6, 15
    n_targets = 3

    cube = rng.normal(size=(height, width, n_bands)).astype(np.float32)
    targets = rng.normal(size=(n_targets, n_bands)).astype(np.float32)

    mf, infeas = mtmf(cube, targets)

    assert mf.shape == (height, width, n_targets)
    assert infeas.shape == (height, width, n_targets)
    assert mf.dtype == np.float32
    assert infeas.dtype == np.float32


def test_mtmf_covariance_regularization_prevents_nans() -> None:
    rng = np.random.default_rng(42)
    n_bands = 50
    n_pixels = 10
    n_targets = 2

    cube = rng.normal(size=(n_pixels, 1, n_bands)).astype(np.float32)
    targets = rng.normal(size=(n_targets, n_bands)).astype(np.float32)

    mf, infeas = mtmf(cube, targets)

    assert np.all(np.isfinite(mf))
    assert np.all(np.isfinite(infeas))


def test_mtmf_infeasibility_acts_as_false_positive_rejection() -> None:
    rng = np.random.default_rng(42)
    B = 20

    # Construct background with known mean and diagonal covariance
    mean_bg = np.zeros(B, dtype=np.float64)
    scales = np.linspace(0.5, 2.0, B)
    cov_bg = np.diag(scales ** 2)

    bg = rng.multivariate_normal(mean_bg, cov_bg, size=300).astype(np.float32)
    cube = bg.reshape(30, 10, B)

    # Target: strong feature in band 0 only
    target = np.zeros(B, dtype=np.float32)
    target[0] = 3.0

    # True mixture pixel: 20% target along d = target - mean_bg
    # z_mixed = 0.2 * target  → MF ≈ 0.2, Infeas ≈ 0
    mixed = (0.2 * target).astype(np.float32)

    # False positive: same MF as mixed but huge orthogonal component
    # z_fp = 0.2 * target + [0, 8, 0, ..., 0]
    # band-1 value is far from bg → high Mahalanobis distance → high Infeas
    # MF stays ≈ 0.2 because fp[0] is same as mixed[0]
    fp = np.zeros(B, dtype=np.float32)
    fp[0] = 0.6
    fp[1] = 8.0

    cube[15, 5] = mixed
    cube[15, 6] = fp

    valid_mask = np.ones((30, 10), dtype=bool)
    valid_mask[15, 5] = False
    valid_mask[15, 6] = False

    mf, infeas = mtmf(cube, target[np.newaxis, :], valid_mask=valid_mask)

    # Both should have similar MF
    assert mf[15, 5, 0] == pytest.approx(0.2, abs=0.05)
    assert mf[15, 6, 0] == pytest.approx(0.2, abs=0.05)

    # True mixture: low infeasibility
    assert infeas[15, 5, 0] < 0.5

    # False positive: high infeasibility (rejected)
    assert infeas[15, 6, 0] > 5.0


def test_mtmf_scores_bounded() -> None:
    rng = np.random.default_rng(42)
    cube = rng.normal(size=(10, 10, 15)).astype(np.float32)
    targets = rng.normal(size=(3, 15)).astype(np.float32)

    mf, infeas = mtmf(cube, targets)

    assert np.all(infeas >= 0.0), "Infeasibility scores must be >= 0"
    assert np.all(np.isfinite(mf))


def test_mtmf_vs_existing_ace() -> None:
    rng = np.random.default_rng(42)
    n_bands = 20
    n_bg = 200
    n_mixed = 300

    # Background pixels with heavy tails (varying scales)
    scales = 0.3 + 1.2 * np.sqrt(rng.random(n_bg))
    bg = (rng.normal(size=(n_bg, n_bands)) * scales[:, np.newaxis]).astype(np.float32)

    # Target: strong signal in a single band
    target = np.zeros(n_bands, dtype=np.float32)
    target[0] = 10.0

    # Mixed pixels: bg + f * target (no (1-f) scaling keeps Mahalanobis variance)
    fractions = np.linspace(0.05, 1.0, n_mixed)
    mixed = []
    for f in fractions:
        bg_idx = rng.integers(0, n_bg)
        px = (f * target + bg[bg_idx]).astype(np.float32)
        mixed.append(px)

    all_pixels = np.vstack([bg, np.array(mixed)])
    N = all_pixels.shape[0]
    side = int(np.ceil(np.sqrt(N)))
    cube = np.zeros((side, side, n_bands), dtype=np.float32)
    cube.reshape(-1, n_bands)[:N] = all_pixels

    # Exclude mixed pixels from background estimation
    valid_mask = np.ones((side, side), dtype=bool)
    flat_valid = np.ones(N, dtype=bool)
    flat_valid[n_bg:] = False
    valid_mask.flat[:N] = flat_valid

    # MTMF with clean background stats
    mf, infeas = mtmf(cube, target[np.newaxis, :], valid_mask=valid_mask)

    # ACE using same clean background stats
    mean, inv_cov = estimate_background_stats(cube, valid_mask=valid_mask)
    Z = cube.reshape(-1, n_bands).astype(np.float64) - mean[np.newaxis, :]
    d = np.asarray(target, dtype=np.float64) - mean
    denom = d @ inv_cov @ d
    Z_inv_cov = Z @ inv_cov
    numer = (d @ inv_cov @ Z.T) ** 2
    z_denom = np.sum(Z_inv_cov * Z, axis=1)
    ace = np.clip(numer / (denom * z_denom + 1e-15), 0.0, 1.0)

    mf_flat = mf.ravel()[:N]
    ace_flat = ace[:N]
    infeas_flat = infeas.ravel()[:N]

    r_mf_ace = np.corrcoef(mf_flat, ace_flat)[0, 1]
    assert r_mf_ace > 0.9, f"MF/ACE correlation r={r_mf_ace:.3f} (expected >0.9)"

    r_infeas_mf = np.corrcoef(infeas_flat, mf_flat)[0, 1]
    assert abs(r_infeas_mf) < 0.2, (
        f"Infeas/MF correlation |r|={abs(r_infeas_mf):.3f} (expected <0.2)"
    )


def test_mtmf_detect_threshold() -> None:
    rng = np.random.default_rng(42)
    n_bands = 20

    # Create a cube with an embedded target
    cube = rng.normal(size=(10, 10, n_bands)).astype(np.float32)
    target = rng.normal(size=n_bands).astype(np.float32)
    target /= np.linalg.norm(target)
    cube[3, 4] = target.copy()

    targets_2d = target[np.newaxis, :]
    mask = mtmf_detect(cube, targets_2d, mf_threshold=0.5, infeas_threshold=5.0)

    assert mask.shape == (10, 10, 1)
    assert mask.dtype == bool
    assert mask[3, 4, 0]


def test_mtmf_detect_default_thresholds_type() -> None:
    rng = np.random.default_rng(42)
    cube = rng.normal(size=(6, 6, 10)).astype(np.float32)
    targets = rng.normal(size=(2, 10)).astype(np.float32)

    mask = mtmf_detect(cube, targets)
    assert mask.shape == (6, 6, 2)
    assert mask.dtype == bool
