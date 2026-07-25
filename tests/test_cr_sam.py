"""Unit tests for continuum-removed / region-weighted SAM (classical CPU path)."""

from __future__ import annotations

import numpy as np

from open_ore_mapper.cr_sam import (
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
    spectra[0, 20] = 0.2  # dip
    cr = linear_continuum_remove(spectra)
    assert cr[0, 20] < 0.9
    assert cr[0, 0] > 0.95 and cr[0, -1] > 0.95


def test_classify_cr_sam_exact_library_pixel() -> None:
    """Pixel identical to library mineral 1 (SWIR clay-like) classifies as that mineral."""
    n_bands = 50
    wl = np.linspace(400, 2500, n_bands).astype(np.float32)
    # simple library: two distinct shapes
    refs = np.ones((2, n_bands), dtype=np.float32) * 0.5
    # mineral 0: VNIR dip (Fe-like)
    refs[0, 5:12] = 0.2
    # mineral 1: SWIR dip (clay-like ~2200nm region)
    swir_i = int(np.argmin(np.abs(wl - 2200)))
    refs[1, swir_i - 2 : swir_i + 3] = 0.15
    names = ["hematite", "kaolinite"]
    pixel = refs[1:2].copy()
    cls, conf = classify_cr_sam(
        pixel, refs, wl, names, sam_threshold_deg=90.0, min_strength=0.0
    )
    assert cls.shape == (1,)
    assert int(cls[0]) == 1
    assert float(conf[0]) > 0.5


def test_classify_cr_sam_fe_vs_swir_separation() -> None:
    n_bands = 60
    wl = np.linspace(400, 2500, n_bands).astype(np.float32)
    refs = np.ones((2, n_bands), dtype=np.float32) * 0.55
    vnir_i = int(np.argmin(np.abs(wl - 900)))
    swir_i = int(np.argmin(np.abs(wl - 2205)))
    refs[0, vnir_i - 3 : vnir_i + 3] = 0.15  # hematite-like
    refs[1, swir_i - 3 : swir_i + 3] = 0.12  # kaolinite-like
    names = ["hematite", "kaolinite"]
    # pure Fe pixel
    cls_fe, _ = classify_cr_sam(
        refs[0:1], refs, wl, names, sam_threshold_deg=90.0, min_strength=0.0
    )
    # pure clay pixel
    cls_sw, _ = classify_cr_sam(
        refs[1:2], refs, wl, names, sam_threshold_deg=90.0, min_strength=0.0
    )
    assert int(cls_fe[0]) == 0
    assert int(cls_sw[0]) == 1
