from pathlib import Path
from unittest.mock import patch

import h5py
import numpy as np
import pytest
import scipy.io  # type: ignore[import-untyped]
import tifffile

from open_ore_mapper.qc import RasterQualityReport
from open_ore_mapper.schemas import MapperOptions
from open_ore_mapper.service import OreMapper
from open_ore_mapper.spectral_library import SpectralLibrary


def test_predict_file_on_synthetic_cubert_like_tiff(tmp_path: Path) -> None:
    cube = np.ones((8, 8, 51), dtype=np.float32) * 0.5
    cube[:4, :4, 10:20] *= 0.5
    path = tmp_path / "synthetic.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    result = OreMapper().predict_file(
        path,
        MapperOptions(
            sensor="cubert_ultris_s5",
            minerals=["hematite_demo", "goethite_demo"],
            tile_size=4,
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )

    assert result.status == "success"
    assert result.model_used == "library_sam_nnls_v1"
    assert result.minerals == ["hematite_demo", "goethite_demo"]
    assert result.output_image.startswith("data:image/png;base64,")
    assert "hematite_demo" in result.statistics


def test_default_options_use_cubert_wavelength_preset(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 51), dtype=np.float32) * 0.5
    path = tmp_path / "synthetic.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    result = OreMapper().predict_file(
        path,
        MapperOptions(min_confidence=0.0, sam_threshold_deg=180.0),
    )

    assert result.sensor == "cubert_ultris_s5"
    assert len(result.wavelengths) == 51


def test_nnls_abundance_uses_raw_spectra_not_l2_normalized_spectra(tmp_path: Path) -> None:
    library = SpectralLibrary(
        names=["Bright", "Dim"],
        wavelengths=np.array([500.0, 600.0], dtype=np.float32),
        spectra=np.array([[2.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        source="synthetic test",
    )
    cube = np.zeros((3, 3, 2), dtype=np.float32)
    cube[:, :, :] = np.array([1.0, 0.5], dtype=np.float32)
    path = tmp_path / "synthetic.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    with (
        patch("open_ore_mapper.service.load_demo_library", return_value=library),
        patch("open_ore_mapper.service.resample_library", return_value=library),
    ):
        result = OreMapper().predict_file(
            path,
            MapperOptions(
                wavelengths=[500.0, 600.0],
                sensor="manual",
                minerals=["Bright", "Dim"],
                sam_threshold_deg=180.0,
                min_confidence=0.0,
                normalization="l2",
            ),
        )

    assert result.statistics["Bright"].mean_abundance == pytest.approx(0.5)


def test_vnir_only_warning_is_emitted(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 51), dtype=np.float32) * 0.5
    path = tmp_path / "synthetic.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    result = OreMapper().predict_file(
        path,
        MapperOptions(min_confidence=0.0, sam_threshold_deg=180.0),
    )

    assert any("SWIR" in warning for warning in result.warnings)


def test_hdf5_without_wavelengths_falls_back_to_sensor_preset(tmp_path: Path) -> None:
    cube = np.zeros((4, 4, 51), dtype=np.float32)
    path = tmp_path / "no_wl.h5"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("hdr", data=cube)

    result = OreMapper().predict_file(
        path,
        MapperOptions(
            sensor="cubert_ultris_s5",
            minerals=["hematite_demo", "goethite_demo"],
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )
    assert result.sensor == "cubert_ultris_s5"
    assert len(result.wavelengths) == 51


def test_hdf5_without_wavelengths_falls_back_to_manual_wavelengths(tmp_path: Path) -> None:
    cube = np.zeros((4, 4, 3), dtype=np.float32)
    path = tmp_path / "no_wl_manual.h5"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("hdr", data=cube)

    result = OreMapper().predict_file(
        path,
        MapperOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
            minerals=["hematite_demo", "goethite_demo"],
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )
    assert result.sensor == "manual"
    assert len(result.wavelengths) == 3


def test_hdf5_embedded_wavelengths(tmp_path: Path) -> None:
    cube = np.zeros((3, 4, 5), dtype=np.float32)
    cube[0, :, :] = 0.3
    cube[1, :, :] = 0.4
    cube[2, :, :] = 0.5
    wavelengths = [500.0, 600.0, 700.0]

    path = tmp_path / "test.h5"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("hdr", data=cube)
        h5.create_dataset("wavelengths", data=wavelengths)

    result = OreMapper().predict_file(
        path,
        MapperOptions(
            min_confidence=0.0,
            sam_threshold_deg=180.0,
            minerals=["hematite_demo", "goethite_demo"],
        ),
    )

    assert result.sensor == "embedded_hdf5"
    assert len(result.wavelengths) == 3


def test_predict_bytes_rejects_unsupported_extension() -> None:
    with pytest.raises(ValueError, match="Supported inputs"):
        OreMapper().predict_bytes(b"not a cube", "scene.txt", MapperOptions())


def test_prediction_excludes_user_band_and_returns_retained_wavelengths(tmp_path: Path) -> None:
    library_3band = SpectralLibrary(
        names=["Hema", "Goet"],
        wavelengths=np.array([400.0, 500.0, 600.0], dtype=np.float32),
        spectra=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32),
        source="synthetic",
    )
    cube = np.ones((4, 4, 3), dtype=np.float32) * 0.5
    path = tmp_path / "exclude_band.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    with (
        patch("open_ore_mapper.service.load_demo_library", return_value=library_3band),
        patch("open_ore_mapper.service.resample_library") as mock_resample,
    ):
        mock_resample.return_value = SpectralLibrary(
            names=["Hema", "Goet"],
            wavelengths=np.array([400.0, 600.0], dtype=np.float32),
            spectra=np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
            source="synthetic",
        )

        result = OreMapper().predict_file(
            path,
            MapperOptions(
                wavelengths=[400.0, 500.0, 600.0],
                sensor="manual",
                minerals=["Hema", "Goet"],
                excluded_band_indices=[1],
                sam_threshold_deg=180.0,
                min_confidence=0.0,
            ),
        )

    assert result.status == "success"
    assert result.wavelengths == [400.0, 600.0]
    assert 500.0 not in result.wavelengths


def test_quality_report_attached_to_result(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 51), dtype=np.float32) * 0.5
    path = tmp_path / "qc_report.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    result = OreMapper().predict_file(
        path,
        MapperOptions(min_confidence=0.0, sam_threshold_deg=180.0),
    )

    assert isinstance(result.quality_report, RasterQualityReport)
    assert result.quality_report.status == "pass"
    assert result.quality_report.band_count == 51
    assert result.quality_report.retained_band_indices == list(range(51))
    assert result.quality_report.valid_pixel_fraction == 1.0


def test_qc_warnings_merged_into_result_warnings(tmp_path: Path) -> None:
    library_3band = SpectralLibrary(
        names=["Hema", "Goet"],
        wavelengths=np.array([400.0, 500.0, 600.0], dtype=np.float32),
        spectra=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32),
        source="synthetic",
    )
    cube = np.ones((4, 4, 3), dtype=np.float32) * 0.5
    path = tmp_path / "merged_warnings.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    with (
        patch("open_ore_mapper.service.load_demo_library", return_value=library_3band),
        patch("open_ore_mapper.service.resample_library") as mock_resample,
    ):
        mock_resample.return_value = SpectralLibrary(
            names=["Hema", "Goet"],
            wavelengths=np.array([400.0, 600.0], dtype=np.float32),
            spectra=np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
            source="synthetic",
        )

        result = OreMapper().predict_file(
            path,
            MapperOptions(
                wavelengths=[400.0, 500.0, 600.0],
                sensor="manual",
                minerals=["Hema", "Goet"],
                excluded_band_indices=[1],
                sam_threshold_deg=180.0,
                min_confidence=0.0,
            ),
        )

    assert any("excluded" in w.lower() for w in result.warnings)
    qc_warning_found = any("band(s) were excluded" in w for w in result.warnings)
    assert qc_warning_found


def test_emit_like_hdf5_loads_reflectance_dataset(tmp_path: Path) -> None:
    cube = np.zeros((3, 4, 5), dtype=np.float32)
    wavelengths = [500.0, 600.0, 700.0, 800.0, 900.0]

    path = tmp_path / "emit_test.nc"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("reflectance", data=cube)
        sgrp = h5.create_group("sensor_band_parameters")
        sgrp.create_dataset("wavelengths", data=wavelengths)

    result = OreMapper().predict_file(
        path,
        MapperOptions(
            min_confidence=0.0,
            sam_threshold_deg=180.0,
            minerals=["hematite_demo", "goethite_demo"],
        ),
    )

    assert result.sensor == "embedded_hdf5"
    assert result.wavelengths == wavelengths
    assert len(result.wavelengths) == 5


def test_emit_like_hdf5_cube_shape_hwc(tmp_path: Path) -> None:
    cube = np.zeros((3, 4, 5), dtype=np.float32)
    wavelengths = list(range(5))

    path = tmp_path / "emit_shape.nc"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("reflectance", data=cube)
        sgrp = h5.create_group("sensor_band_parameters")
        sgrp.create_dataset("wavelengths", data=wavelengths)

    mapper = OreMapper()
    report = mapper.quality_file(
        path,
        MapperOptions(wavelengths=wavelengths, sensor="manual"),
    )

    assert report.shape == (3, 4, 5)


def test_emit_hdf5_good_wavelengths_auto_excludes_bad_bands(tmp_path: Path) -> None:
    cube = np.ones((2, 2, 5), dtype=np.float32)
    wavelengths = [500.0, 600.0, 700.0, 800.0, 900.0]
    good_wavelengths = [1, 1, 0, 1, 0]

    path = tmp_path / "emit_good_wl.h5"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("reflectance", data=cube)
        sgrp = h5.create_group("sensor_band_parameters")
        sgrp.create_dataset("wavelengths", data=wavelengths)
        sgrp.create_dataset("good_wavelengths", data=good_wavelengths)

    result = OreMapper().predict_file(
        path,
        MapperOptions(
            min_confidence=0.0,
            sam_threshold_deg=180.0,
            minerals=["hematite_demo", "goethite_demo"],
        ),
    )

    assert result.quality_report is not None
    assert 2 in result.quality_report.excluded_band_indices
    assert 4 in result.quality_report.excluded_band_indices
    assert result.quality_report.retained_band_indices == [0, 1, 3]
    assert result.wavelengths == [500.0, 600.0, 800.0]


def test_emit_hdf5_good_wavelengths_ignored_when_user_sets_excluded_bands(tmp_path: Path) -> None:
    cube = np.ones((2, 2, 5), dtype=np.float32)
    wavelengths = [500.0, 600.0, 700.0, 800.0, 900.0]
    good_wavelengths = [1, 1, 0, 1, 1]

    path = tmp_path / "emit_user_exclude.h5"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("reflectance", data=cube)
        sgrp = h5.create_group("sensor_band_parameters")
        sgrp.create_dataset("wavelengths", data=wavelengths)
        sgrp.create_dataset("good_wavelengths", data=good_wavelengths)

    result = OreMapper().predict_file(
        path,
        MapperOptions(
            wavelengths=wavelengths,
            sensor="manual",
            min_confidence=0.0,
            sam_threshold_deg=180.0,
            minerals=["hematite_demo", "goethite_demo"],
            excluded_band_indices=[0],
        ),
    )

    assert result.quality_report is not None
    assert 0 in result.quality_report.excluded_band_indices
    assert 2 not in result.quality_report.excluded_band_indices
    assert result.quality_report.retained_band_indices == [1, 2, 3, 4]
    assert result.wavelengths == [600.0, 700.0, 800.0, 900.0]


def test_prediction_fails_when_fewer_than_two_usable_bands_remain(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 2), dtype=np.float32) * 0.5
    path = tmp_path / "two_band.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    with pytest.raises(ValueError, match="At least two usable spectral bands"):
        OreMapper().predict_file(
            path,
            MapperOptions(
                wavelengths=[400.0, 500.0],
                sensor="manual",
                minerals=["Hema", "Goet"],
                excluded_band_indices=[0],
                sam_threshold_deg=180.0,
                min_confidence=0.0,
            ),
        )


def test_mat_file_predict(tmp_path: Path) -> None:
    cube = np.ones((8, 8, 3), dtype=np.float32) * 0.5
    cube[:4, :4, 1] = 0.1
    mat_path = tmp_path / "scene.mat"
    scipy.io.savemat(mat_path, {"cube": cube})

    result = OreMapper().predict_file(
        mat_path,
        MapperOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
            minerals=["hematite_demo", "goethite_demo"],
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )
    assert result.status == "success"
    assert len(result.wavelengths) == 3
    assert "hematite_demo" in result.statistics


def test_mat_file_qc_raster(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 3), dtype=np.float32) * 0.5
    mat_path = tmp_path / "test_qc.mat"
    scipy.io.savemat(mat_path, {"data": cube})

    mapper = OreMapper()
    report = mapper.quality_file(
        mat_path,
        MapperOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
        ),
    )
    assert report.status == "pass"
    assert report.band_count == 3


def test_mat_file_chw_orientation_shape_5_3_4(tmp_path: Path) -> None:
    cube = np.ones((5, 3, 4), dtype=np.float32) * 0.5
    mat_path = tmp_path / "chw_5_3_4.mat"
    scipy.io.savemat(mat_path, {"cube": cube})
    mapper = OreMapper()
    report = mapper.quality_file(
        mat_path,
        MapperOptions(
            wavelengths=[400.0, 460.0, 520.0, 580.0, 640.0],
            sensor="manual",
        ),
    )
    assert report.band_count == 5
    assert report.shape == (3, 4, 5)


def test_mat_file_chw_orientation_salinas_like(tmp_path: Path) -> None:
    cube = np.ones((224, 86, 83), dtype=np.float32) * 0.5
    mat_path = tmp_path / "salinas_like.mat"
    scipy.io.savemat(mat_path, {"salinasA_corrected": cube})
    mapper = OreMapper()
    report = mapper.quality_file(
        mat_path,
        MapperOptions(
            wavelengths=[400.0 + i * 5.0 for i in range(224)],
            sensor="manual",
        ),
    )
    assert report.band_count == 224
    assert report.shape == (86, 83, 224)


def test_mat_file_chw_orientation_shape_30_100_20(tmp_path: Path) -> None:
    cube = np.ones((30, 100, 20), dtype=np.float32) * 0.5
    mat_path = tmp_path / "chw_30_100_20.mat"
    scipy.io.savemat(mat_path, {"cube": cube})
    mapper = OreMapper()
    report = mapper.quality_file(
        mat_path,
        MapperOptions(
            wavelengths=list(range(30)),
            sensor="manual",
        ),
    )
    assert report.band_count == 30
    assert report.shape == (100, 20, 30)


def test_mat_file_int16_qc(tmp_path: Path) -> None:
    rng = np.random.default_rng(42)
    cube = rng.integers(0, 10000, size=(4, 4, 3), dtype=np.int16)
    mat_path = tmp_path / "int16_qc.mat"
    scipy.io.savemat(mat_path, {"cube": cube})
    mapper = OreMapper()
    report = mapper.quality_file(
        mat_path,
        MapperOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
        ),
    )
    assert report.status == "pass"
    assert report.band_count == 3
