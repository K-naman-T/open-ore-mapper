"""Minimum Noise Fraction (MNF) transform — classical spectral noise whitening + PCA.

Standard Green et al. / ENVI-style MNF (CPU, NumPy only):

1. Estimate noise covariance from horizontal adjacent pixel differences
2. Whiten the data with the inverse square-root of the noise covariance
3. PCA on the whitened signal; components ordered by decreasing SNR
4. Project the cube into the top ``n_components`` MNF bands

Used as a preprocessor for SAM (``mnf_sam``) or MTMF (``mnf_mtmf``).

Projection of library endmembers must use the same linear map and the same
training mean via :func:`apply_mnf` / :func:`mnf_data_mean`.
"""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from numpy.typing import NDArray


def _noise_covariance_horizontal(
    cube: NDArray[np.floating[Any]],
    valid_mask: NDArray[np.bool_],
    max_pairs: int = 20000,
) -> NDArray[np.float64]:
    """Estimate noise covariance from horizontal adjacent differences.

    For each valid pair (i, j) and (i, j+1), use d = x_{j+1} - x_j.
    Noise cov ≈ 0.5 * cov(d) under the usual uncorrelated spatial-noise model.
    """
    h, w, b = cube.shape
    if w < 2:
        pixels = cube[valid_mask].reshape(-1, b).astype(np.float64)
        if pixels.shape[0] < 2:
            return np.eye(b, dtype=np.float64)
        var = np.maximum(np.var(pixels, axis=0), 1e-12)
        return np.diag(var * 0.01)

    left = cube[:, :-1, :]
    right = cube[:, 1:, :]
    both_valid = valid_mask[:, :-1] & valid_mask[:, 1:]
    if not np.any(both_valid):
        pixels = cube[valid_mask].reshape(-1, b).astype(np.float64)
        if pixels.shape[0] < 2:
            return np.eye(b, dtype=np.float64)
        var = np.maximum(np.var(pixels, axis=0), 1e-12)
        return np.diag(var * 0.01)

    diffs = (right - left)[both_valid].astype(np.float64)
    n = diffs.shape[0]
    if n > max_pairs:
        rng = np.random.default_rng(0)
        idx = rng.choice(n, size=max_pairs, replace=False)
        diffs = diffs[idx]

    cov_d = np.cov(diffs, rowvar=False)
    if cov_d.ndim == 0:
        cov_d = np.array([[float(cov_d)]], dtype=np.float64)
    rn = 0.5 * cov_d
    rn = 0.5 * (rn + rn.T)
    tr = float(np.trace(rn))
    eps = max(1e-10 * tr / max(b, 1), 1e-12)
    return rn + eps * np.eye(b, dtype=np.float64)


def _matrix_inv_sqrt(mat: NDArray[np.float64]) -> NDArray[np.float64]:
    """Symmetric positive-definite inverse square root via eigendecomposition."""
    m = 0.5 * (mat + mat.T)
    evals, evecs = np.linalg.eigh(m)
    evals = np.maximum(evals, 1e-12)
    inv_sqrt = evecs @ np.diag(1.0 / np.sqrt(evals)) @ evecs.T
    return inv_sqrt.astype(np.float64)


def mnf_data_mean(
    cube: NDArray[np.floating[Any]],
    valid_mask: NDArray[np.bool_],
) -> NDArray[np.float64]:
    """Mean spectrum of valid pixels (for consistent MNF library projection)."""
    arr = np.asarray(cube, dtype=np.float64)
    b = arr.shape[2]
    mask = np.asarray(valid_mask, dtype=bool)
    if not np.any(mask):
        return np.zeros(b, dtype=np.float64)
    return np.mean(arr[mask].reshape(-1, b), axis=0)


def apply_mnf(
    spectra: NDArray[np.floating[Any]],
    transform_matrix: NDArray[np.floating[Any]],
    data_mean: NDArray[np.floating[Any]] | None = None,
) -> NDArray[np.float32]:
    """Project (N, B) or (B,) spectra into MNF space with optional mean centering.

    If ``data_mean`` is provided (B,), uses ``(spectra - data_mean) @ transform``.
    If omitted, applies the linear map only.
    """
    t = np.asarray(transform_matrix, dtype=np.float64)
    s = np.asarray(spectra, dtype=np.float64)
    squeeze = False
    if s.ndim == 1:
        s = s[np.newaxis, :]
        squeeze = True
    if s.shape[1] != t.shape[0]:
        raise ValueError(
            f"spectra bands {s.shape[1]} != transform rows {t.shape[0]}"
        )
    if data_mean is not None:
        mu = np.asarray(data_mean, dtype=np.float64).reshape(1, -1)
        s = s - mu
    out = (s @ t).astype(np.float32)
    if squeeze:
        return cast(NDArray[np.float32], out[0])
    return cast(NDArray[np.float32], out)


def mnf_transform(
    cube: NDArray[np.floating[Any]],
    valid_mask: NDArray[np.bool_],
    n_components: int = 20,
) -> tuple[NDArray[np.float32], NDArray[np.float64]]:
    """Apply Minimum Noise Fraction transform.

    Parameters
    ----------
    cube:
        HxWxB hyperspectral cube (float).
    valid_mask:
        HxW boolean mask of valid pixels used for noise/signal stats.
    n_components:
        Number of MNF components to retain (capped at B).

    Returns
    -------
    transformed_cube:
        HxWxC float32 cube in MNF space (C = min(n_components, B)).
        Centered with the valid-pixel mean (same mean for :func:`apply_mnf`).
    transform_matrix:
        BxC float64 matrix. Project library endmembers with::

            apply_mnf(refs, transform_matrix, data_mean=mnf_data_mean(cube, mask))
    """
    arr = np.asarray(cube, dtype=np.float64)
    if arr.ndim != 3:
        raise ValueError(f"Expected HxWxB cube, got shape {arr.shape}")
    h, w, b = arr.shape
    mask = np.asarray(valid_mask, dtype=bool)
    if mask.shape != (h, w):
        raise ValueError(f"valid_mask shape {mask.shape} != cube spatial {(h, w)}")

    c = int(max(1, min(n_components, b)))

    if not np.any(mask):
        t = np.zeros((b, c), dtype=np.float64)
        t[:c, :c] = np.eye(c)
        out = np.zeros((h, w, c), dtype=np.float32)
        return cast(NDArray[np.float32], out), t

    rn = _noise_covariance_horizontal(arr, mask)
    rn_inv_sqrt = _matrix_inv_sqrt(rn)

    pixels = arr[mask].reshape(-1, b)
    n = pixels.shape[0]
    if n > 10000:
        rng = np.random.default_rng(0)
        idx = rng.choice(n, size=10000, replace=False)
        sample = pixels[idx]
    else:
        sample = pixels

    whitened = sample @ rn_inv_sqrt
    mean_w = np.mean(whitened, axis=0)
    whitened_c = whitened - mean_w

    n_s = whitened_c.shape[0]
    if n_s < 2:
        evecs = np.eye(b, dtype=np.float64)
    else:
        try:
            _u, _s, vt = np.linalg.svd(whitened_c, full_matrices=False)
            evecs = vt.T
        except np.linalg.LinAlgError:
            cov_w = np.cov(whitened_c, rowvar=False)
            if cov_w.ndim == 0:
                cov_w = np.array([[float(cov_w)]], dtype=np.float64)
            evals, evecs = np.linalg.eigh(0.5 * (cov_w + cov_w.T))
            evecs = evecs[:, np.argsort(evals)[::-1]]

    evecs_c = evecs[:, :c]
    transform = rn_inv_sqrt @ evecs_c  # (B, C)

    # Center with full valid-pixel mean so apply_mnf(..., mnf_data_mean(...)) matches
    mu = np.mean(pixels, axis=0)
    flat = arr.reshape(-1, b)
    scores = (flat - mu) @ transform
    transformed = scores.reshape(h, w, c).astype(np.float32)

    return cast(NDArray[np.float32], transformed), transform.astype(np.float64)
