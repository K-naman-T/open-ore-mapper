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


def mtmf(
    cube: NDArray[np.float32],
    targets: NDArray[np.float32],
    valid_mask: NDArray[np.bool_] | None = None,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    H, W, B = cube.shape
    K = targets.shape[0]

    mean, inv_cov = estimate_background_stats(cube, valid_mask=valid_mask)

    flat = cube.reshape(-1, B)

    Z = np.asarray(flat, dtype=np.float64) - mean[np.newaxis, :]
    T = np.asarray(targets, dtype=np.float64) - mean[np.newaxis, :]

    Z_inv_cov = Z @ inv_cov
    mahalanobis2 = np.sum(Z_inv_cov * Z, axis=1)

    mf_flat = np.zeros((Z.shape[0], K), dtype=np.float64)
    infeas_flat = np.zeros((Z.shape[0], K), dtype=np.float64)

    for k in range(K):
        d = T[k]
        denom = d @ inv_cov @ d
        w = inv_cov @ d / denom
        mf = Z @ w
        mf_flat[:, k] = mf
        infeas_flat[:, k] = np.sqrt(
            np.maximum(0.0, mahalanobis2 - mf ** 2 * denom)
        )

    mf_result = mf_flat.reshape(H, W, K).astype(np.float32)
    infeas_result = infeas_flat.reshape(H, W, K).astype(np.float32)

    return cast(NDArray[np.float32], mf_result), cast(NDArray[np.float32], infeas_result)


def mtmf_detect(
    cube: NDArray[np.float32],
    targets: NDArray[np.float32],
    valid_mask: NDArray[np.bool_] | None = None,
    mf_threshold: float = 0.5,
    infeas_threshold: float = 10.0,
) -> NDArray[np.bool_]:
    mf, infeas = mtmf(cube, targets, valid_mask=valid_mask)
    return cast(NDArray[np.bool_], (mf >= mf_threshold) & (infeas <= infeas_threshold))
