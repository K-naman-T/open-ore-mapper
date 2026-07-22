from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


def _soft_threshold(z: NDArray[np.float64], tau: float) -> NDArray[np.float64]:
    return np.sign(z) * np.maximum(np.abs(z) - tau, 0.0)


def sunsal(
    pixels: NDArray[np.floating[Any]],
    library: NDArray[np.floating[Any]],
    lambda_: float = 0.01,
    max_iter: int = 200,
    tol: float = 1e-4,
) -> NDArray[np.float32]:
    pixels = np.asarray(pixels, dtype=np.float64)
    library = np.asarray(library, dtype=np.float64)

    n_pixels, n_bands = pixels.shape
    n_endmembers = library.shape[0]

    A = library
    Y = pixels.T

    rho = 1.0
    K = n_endmembers
    N = n_pixels

    R = np.linalg.inv(A @ A.T + rho * np.eye(K))

    X = np.zeros((K, N), dtype=np.float64)
    V = np.zeros((K, N), dtype=np.float64)
    U = np.zeros((K, N), dtype=np.float64)

    AY = A @ Y

    for _ in range(max_iter):
        X = R @ (AY + rho * (V - U))

        V = _soft_threshold(X + U, lambda_ / rho)
        V = np.maximum(V, 0.0)

        U = U + X - V

        denom = max(np.linalg.norm(X, "fro"), 1e-16)
        change = np.linalg.norm(X - V, "fro") / denom
        if change < tol:
            break

    return np.maximum(X.T, 0.0).astype(np.float32)


def should_use_sunsal(library_size: int) -> bool:
    return library_size >= 50
