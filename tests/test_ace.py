from __future__ import annotations

import numpy as np
import pytest
from open_ore_mapper.ace import (
    ace_detection_map,
    ace_score,
    ace_scores,
    estimate_background_stats,
)
from open_ore_mapper.sam import angles_to_strength, compute_sam_angles


def test_ace_exact_target_returns_near_one() -> None:
    rng = np.random.default_rng(42)
    n_bands = 20
    target = rng.normal(size=n_bands).astype(np.float32)
    target /= np.linalg.norm(target)

    cube = rng.normal(size=(11, 11, n_bands)).astype(np.float32)
    cube[10, 10] = target

    mean, inv_cov = estimate_background_stats(cube)

    score = ace_score(cube[10, 10], target, mean, inv_cov)
    assert float(score) == pytest.approx(1.0, abs=0.15)


def test_ace_orthogonal_target_returns_near_zero() -> None:
    rng = np.random.default_rng(42)
    n_bands = 10

    bg_pixels = rng.normal(size=(50, n_bands)).astype(np.float32)
    mean_bg = bg_pixels.mean(axis=0, keepdims=True)
    bg_pixels_centered = bg_pixels - mean_bg
    bg_pixels_orthogonal = np.hstack(
        [bg_pixels_centered[:, :1] * 0, bg_pixels_centered[:, 1:]]
    ).astype(np.float32)

    target = np.zeros(n_bands, dtype=np.float32)
    target[0] = 1.0

    pixel = np.zeros(n_bands, dtype=np.float32)
    pixel[1] = 1.0

    cube = np.vstack([bg_pixels_orthogonal, pixel.reshape(1, -1)]).reshape(
        51, 1, n_bands
    )

    mean, inv_cov = estimate_background_stats(cube)

    score = ace_score(pixel, target, mean, inv_cov)
    assert float(score) == pytest.approx(0.0, abs=0.15)


def test_ace_subpixel_mixture_detected() -> None:
    rng = np.random.default_rng(42)
    n_bands = 30

    bg_spectrum = np.linspace(0.5, 2.0, n_bands, dtype=np.float32)

    target = np.ones(n_bands, dtype=np.float32) * 1.5
    target[n_bands // 2] = 0.2
    target /= np.linalg.norm(target)

    mixed = (0.05 * target + 0.95 * (bg_spectrum / np.linalg.norm(bg_spectrum))).astype(
        np.float32
    )

    bg_pixels = bg_spectrum[np.newaxis, :] + 0.1 * rng.normal(
        size=(224, n_bands)
    ).astype(np.float32)

    cube_3d = np.zeros((15, 15, n_bands), dtype=np.float32)
    cube_3d.reshape(-1, n_bands)[:-1] = bg_pixels
    cube_3d[14, 14] = mixed

    mean, inv_cov = estimate_background_stats(cube_3d)

    score = ace_score(cube_3d[14, 14], target, mean, inv_cov)
    assert float(score) > 0.1


def test_ace_scores_are_bounded_zero_to_one() -> None:
    rng = np.random.default_rng(42)
    n_bands = 10

    cube = rng.normal(size=(10, 10, n_bands)).astype(np.float32)
    targets = rng.normal(size=(5, n_bands)).astype(np.float32)

    mean, inv_cov = estimate_background_stats(cube)
    scores = ace_scores(cube, targets, mean, inv_cov)

    assert np.all(scores >= 0.0)
    assert np.all(scores <= 1.0)


def test_estimate_background_covariance_handles_regularization() -> None:
    rng = np.random.default_rng(42)
    n_bands = 50
    n_pixels = 10

    cube = rng.normal(size=(n_pixels, 1, n_bands)).astype(np.float32)

    mean, inv_cov = estimate_background_stats(cube)

    assert mean.shape == (n_bands,)
    assert inv_cov.shape == (n_bands, n_bands)
    assert np.all(np.isfinite(inv_cov))


def test_ace_output_shape_correct() -> None:
    rng = np.random.default_rng(42)
    height, width, n_bands = 5, 4, 10
    n_targets = 3

    cube = rng.normal(size=(height, width, n_bands)).astype(np.float32)
    targets = rng.normal(size=(n_targets, n_bands)).astype(np.float32)

    mean, inv_cov = estimate_background_stats(cube)
    scores = ace_scores(cube, targets, mean, inv_cov)

    assert scores.shape == (height, width, n_targets)
    assert scores.dtype == np.float32


def test_ace_vs_sam_on_mixed_pixel() -> None:
    rng = np.random.default_rng(42)
    n_bands = 40

    target_a = rng.normal(size=n_bands).astype(np.float32)
    target_a /= np.linalg.norm(target_a)
    target_b = rng.normal(size=n_bands).astype(np.float32)
    target_b /= np.linalg.norm(target_b)

    bg = rng.normal(size=n_bands).astype(np.float32)
    bg /= np.linalg.norm(bg)

    mixed_5pct = (0.05 * target_a + 0.95 * bg).astype(np.float32)

    mixed_30pct = (0.30 * target_b + 0.70 * bg).astype(np.float32)

    bg_pixels = rng.normal(size=(147, n_bands)).astype(np.float32)
    cube_3d = np.zeros((7, 21, n_bands), dtype=np.float32)
    cube_3d.reshape(-1, n_bands)[:147] = bg_pixels

    cube_3d[3, 10] = mixed_5pct
    cube_3d[3, 11] = mixed_30pct

    targets_for_ace = np.stack([target_a, target_b], axis=0)

    mean, inv_cov = estimate_background_stats(cube_3d)

    ace_scores_result = ace_scores(cube_3d, targets_for_ace, mean, inv_cov)
    ace_for_a = float(ace_scores_result[3, 10, 0])
    ace_for_b = float(ace_scores_result[3, 11, 1])

    flat = cube_3d.reshape(-1, n_bands)
    sam_angles = compute_sam_angles(flat, targets_for_ace).reshape(
        cube_3d.shape[0], cube_3d.shape[1], 2
    )
    sam_strength = angles_to_strength(sam_angles)
    sam_for_a = float(sam_strength[3, 10, 0])

    assert ace_for_a > sam_for_a, "ACE detects 5% subpixel target better than SAM"
    assert ace_for_a > ace_scores_result[3, 10, 1], "ACE correctly identifies target_a vs target_b in pixel"
    assert ace_for_b > ace_scores_result[3, 11, 0], "ACE correctly identifies target_b vs target_a in pixel"


def test_ace_detection_map_convenience() -> None:
    rng = np.random.default_rng(42)
    cube = rng.normal(size=(8, 8, 12)).astype(np.float32)
    targets = rng.normal(size=(2, 12)).astype(np.float32)

    result = ace_detection_map(cube, targets)
    assert result.shape == (8, 8, 2)
    assert result.dtype == np.float32
    assert np.all(result >= 0.0) and np.all(result <= 1.0)
