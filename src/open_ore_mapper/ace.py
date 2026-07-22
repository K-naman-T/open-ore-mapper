from __future__ import annotations

from typing import cast

import numpy as np
from numpy.typing import NDArray


def estimate_background_stats(
    cube: NDArray[np.float32],
    valid_mask: NDArray[np.bool_] | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    H, W, B = cube.shape

    if valid_mask is not None:
        pixels = cube[valid_mask].reshape(-1, B)
    else:
        pixels = cube.reshape(-1, B)

    N = pixels.shape[0]

    if N > 5000:
        rng = np.random.default_rng()
        idx = rng.choice(N, size=5000, replace=False)
        sampled = pixels[idx]
    else:
        sampled = pixels

    sampled_64 = np.asarray(sampled, dtype=np.float64)
    mean = np.mean(sampled_64, axis=0)

    cov = np.cov(sampled_64, rowvar=False)

    cond = np.linalg.cond(cov)
    epsilon = 1e-4 * np.trace(cov)
    if cond > 1e4:
        cov_reg = cov + epsilon * np.eye(B, dtype=np.float64)
    else:
        cov_reg = cov

    inv_cov = np.linalg.pinv(cov_reg)

    return mean.astype(np.float64), inv_cov.astype(np.float64)


def ace_score(
    pixel: NDArray[np.float32],
    target: NDArray[np.float32],
    mean: NDArray[np.float64],
    inv_cov: NDArray[np.float64],
) -> float:
    z = np.asarray(pixel, dtype=np.float64) - mean
    t = np.asarray(target, dtype=np.float64) - mean

    t_inv_cov = t @ inv_cov
    z_inv_cov = z @ inv_cov

    numerator = (t_inv_cov @ z) ** 2
    denominator = (t_inv_cov @ t) * (z_inv_cov @ z)

    if denominator < 1e-15:
        return 0.0

    score = numerator / denominator
    return float(np.clip(score, 0.0, 1.0))


def ace_scores(
    cube: NDArray[np.float32],
    targets: NDArray[np.float32],
    mean: NDArray[np.float64],
    inv_cov: NDArray[np.float64],
    valid_mask: NDArray[np.bool_] | None = None,
) -> NDArray[np.float32]:
    H, W, B = cube.shape
    K = targets.shape[0]

    if valid_mask is not None:
        flat = cube[valid_mask].reshape(-1, B)
    else:
        flat = cube.reshape(-1, B)

    Z = np.asarray(flat, dtype=np.float64) - mean[np.newaxis, :]
    T = np.asarray(targets, dtype=np.float64) - mean[np.newaxis, :]

    Z_inv_cov = Z @ inv_cov
    T_inv_cov = T @ inv_cov

    numer = (Z_inv_cov @ T.T) ** 2

    z_denom = np.sum(Z_inv_cov * Z, axis=1)
    t_denom = np.sum(T_inv_cov * T, axis=1)

    denom = z_denom[:, np.newaxis] * t_denom[np.newaxis, :]

    scores = np.where(denom < 1e-15, 0.0, numer / denom)
    scores = np.clip(scores, 0.0, 1.0)

    result = np.zeros((H, W, K), dtype=np.float32)
    if valid_mask is not None:
        result[valid_mask] = scores.astype(np.float32)
    else:
        result = scores.reshape(H, W, K).astype(np.float32)

    return cast(NDArray[np.float32], result)


def ace_detection_map(
    cube: NDArray[np.float32],
    targets: NDArray[np.float32],
    valid_mask: NDArray[np.bool_] | None = None,
) -> NDArray[np.float32]:
    mean, inv_cov = estimate_background_stats(cube, valid_mask=valid_mask)
    return ace_scores(cube, targets, mean, inv_cov, valid_mask=valid_mask)
