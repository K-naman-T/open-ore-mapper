from __future__ import annotations

import numpy as np
import pytest

from open_ore_mapper.qc import analyze_raster_quality


def test_pass_case_all_bands_valid() -> None:
    cube = np.ones((10, 10, 4), dtype=np.float32)
    wavelengths = [400.0, 500.0, 600.0, 700.0]
    report = analyze_raster_quality(cube, wavelengths, min_band_valid_fraction=0.5)

    assert report.status == "pass"
    assert report.band_count == 4
    assert report.retained_band_indices == [0, 1, 2, 3]
    assert report.excluded_band_indices == []
    assert report.valid_pixel_fraction == 1.0
    assert report.warnings == []
    for band in report.bands:
        assert not band.excluded
        assert band.reasons == []


def test_low_finite_fraction_excludes_band() -> None:
    cube = np.ones((10, 10, 3), dtype=np.float32)
    cube.reshape(-1, 3)[:60, 2] = np.nan
    wavelengths = [400.0, 500.0, 600.0]
    report = analyze_raster_quality(cube, wavelengths, min_band_valid_fraction=0.5)

    assert report.status == "warn"
    assert report.bands[2].excluded
    assert "low_finite_fraction" in report.bands[2].reasons
    assert 2 in report.excluded_band_indices
    assert 2 not in report.retained_band_indices
    assert report.bands[2].finite_fraction == pytest.approx(0.4)
    assert report.bands[0].finite_fraction == 1.0


def test_user_excluded_band() -> None:
    cube = np.ones((10, 10, 3), dtype=np.float32)
    wavelengths = [400.0, 500.0, 600.0]
    report = analyze_raster_quality(cube, wavelengths, excluded_band_indices=[1])

    assert report.bands[1].excluded
    assert "user_excluded" in report.bands[1].reasons
    assert 1 in report.excluded_band_indices
    assert 1 not in report.retained_band_indices
    assert report.retained_band_indices == [0, 2]
    assert report.status == "warn"


def test_fail_fewer_than_two_usable_bands() -> None:
    cube = np.ones((10, 10, 3), dtype=np.float32)
    cube.reshape(-1, 3)[:, 0] = np.nan
    cube.reshape(-1, 3)[:, 1] = np.nan
    cube.reshape(-1, 3)[:, 2] = np.nan
    wavelengths = [400.0, 500.0, 600.0]
    report = analyze_raster_quality(cube, wavelengths, min_band_valid_fraction=0.5)

    assert report.status == "fail"
    assert len(report.retained_band_indices) < 2
    assert any("insufficient" in w.lower() or "usable" in w.lower() for w in report.warnings)


def test_validate_3d_cube() -> None:
    with pytest.raises(ValueError, match="3D"):
        analyze_raster_quality(
            np.ones((10, 10), dtype=np.float32),
            [400.0, 500.0],
        )


def test_band_with_both_user_excluded_and_low_finite_fraction() -> None:
    cube = np.ones((10, 10, 3), dtype=np.float32)
    cube.reshape(-1, 3)[:60, 1] = np.nan
    wavelengths = [400.0, 500.0, 600.0]
    report = analyze_raster_quality(
        cube, wavelengths, excluded_band_indices=[1], min_band_valid_fraction=0.5
    )

    assert report.bands[1].excluded
    assert "user_excluded" in report.bands[1].reasons
    assert "low_finite_fraction" in report.bands[1].reasons
    assert len(report.bands[1].reasons) == 2
    assert report.bands[1].finite_fraction == pytest.approx(0.4)
    assert 1 in report.excluded_band_indices


def test_wavelength_min_max_mean_std_populated() -> None:
    cube = np.ones((5, 5, 3), dtype=np.float32)
    cube[0, 0, 0] = 10.0
    cube[1, 1, 1] = 20.0
    wavelengths = [400.0, 500.0, 600.0]
    report = analyze_raster_quality(cube, wavelengths)

    assert report.wavelength_min == 400.0
    assert report.wavelength_max == 600.0
    assert report.bands[0].mean == pytest.approx(1.36, rel=1e-2)
    assert report.bands[0].std == pytest.approx(1.7636, rel=1e-2)
    assert report.bands[1].mean == pytest.approx(1.76, rel=1e-2)
    assert report.bands[1].std == pytest.approx(3.7232, rel=1e-2)
    assert report.bands[2].mean == pytest.approx(1.0)
    assert report.bands[2].std == pytest.approx(0.0)


def test_warn_when_valid_pixel_fraction_below_one_with_no_excluded_bands() -> None:
    cube = np.ones((10, 10, 3), dtype=np.float32)
    cube[0, 0, :] = np.nan
    wavelengths = [400.0, 500.0, 600.0]
    report = analyze_raster_quality(cube, wavelengths, min_band_valid_fraction=0.5)

    assert report.status == "warn"
    assert report.excluded_band_indices == []
    assert report.valid_pixel_fraction == pytest.approx(0.99)
    assert len(report.warnings) > 0
    assert any("invalid" in w.lower() for w in report.warnings)
    assert not any("excluded" in w.lower() for w in report.warnings)


def test_negative_excluded_band_index_raises_value_error() -> None:
    cube = np.ones((10, 10, 3), dtype=np.float32)
    wavelengths = [400.0, 500.0, 600.0]
    with pytest.raises(ValueError, match="out of range"):
        analyze_raster_quality(cube, wavelengths, excluded_band_indices=[-1])


def test_out_of_range_excluded_band_index_raises_value_error() -> None:
    cube = np.ones((10, 10, 3), dtype=np.float32)
    wavelengths = [400.0, 500.0, 600.0]
    with pytest.raises(ValueError, match="out of range"):
        analyze_raster_quality(cube, wavelengths, excluded_band_indices=[5])


def test_excluded_band_indices_none_behaves_like_empty_list() -> None:
    cube = np.ones((10, 10, 3), dtype=np.float32)
    wavelengths = [400.0, 500.0, 600.0]
    report_none = analyze_raster_quality(cube, wavelengths, excluded_band_indices=None)
    report_empty = analyze_raster_quality(cube, wavelengths, excluded_band_indices=[])

    assert report_none.status == report_empty.status
    assert report_none.excluded_band_indices == report_empty.excluded_band_indices
    assert report_none.retained_band_indices == report_empty.retained_band_indices
    assert report_none.valid_pixel_fraction == report_empty.valid_pixel_fraction
    assert [b.excluded for b in report_none.bands] == [b.excluded for b in report_empty.bands]
