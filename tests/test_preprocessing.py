import numpy as np
import pytest

from open_ore_mapper.preprocessing import ensure_hwc, normalize_cube, valid_pixel_mask


def test_l2_normalization_makes_valid_spectra_unit_norm() -> None:
    cube = np.array([[[3.0, 4.0], [0.0, 0.0]]], dtype=np.float32)
    normalized = normalize_cube(cube, "l2")
    assert float(np.linalg.norm(normalized[0, 0])) == pytest.approx(1.0)
    assert float(np.linalg.norm(normalized[0, 1])) == 0.0


def test_valid_pixel_mask_sanitizes_inf_no_runtimewarning() -> None:
    cube = np.array([[[1.0, np.inf], [0.0, 0.0], [np.nan, 1.0]]], dtype=np.float32)
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        mask = valid_pixel_mask(cube)
        runtime_warnings = [x for x in w if issubclass(x.category, RuntimeWarning)]
        assert len(runtime_warnings) == 0
    # inf pixels fail isfinite so they're excluded regardless of norm
    assert mask.tolist() == [[False, False, False]]


def test_valid_pixel_mask_rejects_nan_and_zero_spectra() -> None:
    cube = np.array([[[1.0, 2.0], [0.0, 0.0], [np.nan, 1.0]]], dtype=np.float32)
    mask = valid_pixel_mask(cube)
    assert mask.tolist() == [[True, False, False]]


def test_percentile_normalization_is_finite() -> None:
    cube = np.arange(2 * 3 * 4, dtype=np.float32).reshape(2, 3, 4)
    normalized = normalize_cube(cube, "percentile")
    assert np.all(np.isfinite(normalized))
    assert float(normalized.min()) >= 0.0
    assert float(normalized.max()) <= 1.0


def test_ensure_hwc_does_not_transpose_hwc_cube_with_many_bands() -> None:
    cube = np.zeros((200, 300, 400), dtype=np.float32)
    normalized = ensure_hwc(cube)
    assert normalized.shape == (200, 300, 400)


def test_ensure_hwc_moves_band_axis_when_band_count_provided() -> None:
    cube = np.zeros((256, 111, 170), dtype=np.float32)
    result = ensure_hwc(cube, band_count=256)
    assert result.shape == (111, 170, 256)


def test_ensure_hwc_preserves_hwc_when_last_axis_matches_band_count() -> None:
    cube = np.zeros((111, 170, 256), dtype=np.float32)
    result = ensure_hwc(cube, band_count=256)
    assert result.shape == (111, 170, 256)


def test_ensure_hwc_raises_on_ambiguous_all_three_axes_match_band_count() -> None:
    cube = np.zeros((128, 128, 128), dtype=np.float32)
    with pytest.raises(ValueError, match="Ambiguous"):
        ensure_hwc(cube, band_count=128)


def test_ensure_hwc_raises_on_ambiguous_two_non_last_axes_match_band_count() -> None:
    cube = np.zeros((8, 8, 4), dtype=np.float32)
    with pytest.raises(ValueError, match="Ambiguous"):
        ensure_hwc(cube, band_count=8)
