from __future__ import annotations

import numpy as np

from spectral_matching.cr_sam import (
    classify_cr_sam,
    linear_continuum_remove,
)


def test_linear_continuum_remove_flat_is_ones() -> None:
    spectra = np.full((3, 10), 0.4, dtype=np.float32)
    cr = linear_continuum_remove(spectra)
    np.testing.assert_allclose(cr, 1.0, atol=1e-5)


def test_linear_continuum_remove_absorption_dip() -> None:
    wl_n = 40
    spectra = np.ones((1, wl_n), dtype=np.float32) * 0.5
    spectra[0, 20] = 0.2
    cr = linear_continuum_remove(spectra)
    assert float(cr[0, 20]) < 0.9
    assert float(cr[0, 0]) > 0.95
    assert float(cr[0, -1]) > 0.95


def test_cr_sam_classifies_generic() -> None:
    n_bands = 30
    wl = np.linspace(400, 2500, n_bands).astype(np.float32)
    refs = np.ones((2, n_bands), dtype=np.float32) * 0.5
    refs[0, 5:12] = 0.2
    refs[1, 18:22] = 0.15
    names = ["spectrum_a", "spectrum_b"]

    pixel = refs[1:2].copy()
    cls, conf = classify_cr_sam(
        pixel, refs, wl, names, sam_threshold_deg=90.0, min_strength=0.0
    )
    assert cls.shape == (1,)
    assert int(cls[0]) == 1
    assert float(conf[0]) > 0.5


def test_cr_sam_separates_generic_spectra() -> None:
    n_bands = 30
    wl = np.linspace(400, 2500, n_bands).astype(np.float32)
    refs = np.ones((2, n_bands), dtype=np.float32) * 0.5
    refs[0, 5:12] = 0.2
    refs[1, 18:22] = 0.15
    names = ["spectrum_a", "spectrum_b"]

    cls_a, _ = classify_cr_sam(
        refs[0:1], refs, wl, names, sam_threshold_deg=90.0, min_strength=0.0
    )
    cls_b, _ = classify_cr_sam(
        refs[1:2], refs, wl, names, sam_threshold_deg=90.0, min_strength=0.0
    )
    assert int(cls_a[0]) == 0
    assert int(cls_b[0]) == 1
