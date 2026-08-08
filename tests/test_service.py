from pathlib import Path

import h5py
import numpy as np
import pytest
import scipy.io  # type: ignore[import-untyped]
import tifffile

from spectral_matching.schemas import MatchOptions
from spectral_matching.engine import SpectralMatcher


def _write_library(tmp_path: Path, name: str = "lib.csv") -> Path:
    """Write a small generic 5-band spectral library CSV and return its path."""
    csv_path = tmp_path / name
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,450,0.42\n"
        "class_a,550,0.30\n"
        "class_a,650,0.34\n"
        "class_a,750,0.46\n"
        "class_a,850,0.52\n"
        "class_b,450,0.38\n"
        "class_b,550,0.44\n"
        "class_b,650,0.35\n"
        "class_b,750,0.48\n"
        "class_b,850,0.55\n"
    )
    return csv_path


def _two_class_library(tmp_path: Path) -> Path:
    """2-band two-class library for small cubes."""
    csv_path = tmp_path / "two_class.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,400,1.0\n"
        "class_a,500,0.0\n"
        "class_b,400,0.0\n"
        "class_b,500,1.0\n"
    )
    return csv_path


def test_predict_file_on_synthetic_cubert_like_tiff(tmp_path: Path) -> None:
    cube = np.ones((8, 8, 51), dtype=np.float32) * 0.5
    cube[:4, :4, 10:20] *= 0.5
    path = tmp_path / "synthetic.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")
    lib = _write_library(tmp_path)

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            sensor="cubert_ultris_s5",
            classes=["class_a", "class_b"],
            spectral_library=str(lib),
            tile_size=4,
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )

    assert result.status == "success"
    assert "nnls" in result.model_used
    assert result.classes == ["class_a", "class_b"]
    assert result.output_image.startswith("data:image/png;base64,")
    assert "class_a" in result.statistics


def test_default_options_use_cubert_wavelength_preset(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 51), dtype=np.float32) * 0.5
    path = tmp_path / "synthetic.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")
    lib = _write_library(tmp_path)

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            classes=["class_a"],
            spectral_library=str(lib),
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )

    assert result.sensor == "cubert_ultris_s5"
    assert len(result.wavelengths) == 51


def test_nnls_abundance_uses_raw_spectra_not_l2_normalized_spectra(tmp_path: Path) -> None:
    cube = np.zeros((3, 3, 2), dtype=np.float32)
    cube[:, :, :] = np.array([1.0, 0.5], dtype=np.float32)
    path = tmp_path / "synthetic.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    csv_path = tmp_path / "lib.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "Bright,500,2.0\n"
        "Bright,600,0.0\n"
        "Dim,500,0.0\n"
        "Dim,600,1.0\n"
    )

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            wavelengths=[500.0, 600.0],
            sensor="manual",
            classes=["Bright", "Dim"],
            spectral_library=str(csv_path),
            sam_threshold_deg=180.0,
            min_confidence=0.0,
            normalization="l2",
        ),
    )

    assert result.statistics["Bright"].mean_abundance == pytest.approx(0.5)


def test_hdf5_without_wavelengths_falls_back_to_sensor_preset(tmp_path: Path) -> None:
    cube = np.zeros((4, 4, 51), dtype=np.float32)
    path = tmp_path / "no_wl.h5"
    with h5py.File(path, "w") as h5:
        h5.create_dataset("hdr", data=cube)
    lib = _write_library(tmp_path)

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            sensor="cubert_ultris_s5",
            classes=["class_a", "class_b"],
            spectral_library=str(lib),
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
    csv_path = tmp_path / "lib3.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,400,0.5\n"
        "class_a,500,0.4\n"
        "class_a,600,0.3\n"
        "class_b,400,0.3\n"
        "class_b,500,0.4\n"
        "class_b,600,0.5\n"
    )

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
            classes=["class_a", "class_b"],
            spectral_library=str(csv_path),
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
    csv_path = tmp_path / "lib3.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,500,0.5\n"
        "class_a,600,0.4\n"
        "class_a,700,0.3\n"
        "class_b,500,0.3\n"
        "class_b,600,0.4\n"
        "class_b,700,0.5\n"
    )

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            min_confidence=0.0,
            sam_threshold_deg=180.0,
            classes=["class_a", "class_b"],
            spectral_library=str(csv_path),
        ),
    )

    assert result.sensor == "embedded_hdf5"
    assert len(result.wavelengths) == 3


def test_predict_bytes_rejects_unsupported_extension(tmp_path: Path) -> None:
    lib = _two_class_library(tmp_path)
    with pytest.raises(ValueError, match="Supported inputs"):
        SpectralMatcher().predict_bytes(
            b"not a cube",
            "scene.txt",
            MatchOptions(classes=["class_a", "class_b"], spectral_library=str(lib)),
        )


def test_prediction_excludes_user_band_and_returns_retained_wavelengths(tmp_path: Path) -> None:
    csv_path = tmp_path / "lib3.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,400,1.0\n"
        "class_a,500,0.0\n"
        "class_a,600,0.0\n"
        "class_b,400,0.0\n"
        "class_b,500,1.0\n"
        "class_b,600,0.0\n"
    )
    cube = np.ones((4, 4, 3), dtype=np.float32) * 0.5
    path = tmp_path / "exclude_band.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
            classes=["class_a", "class_b"],
            spectral_library=str(csv_path),
            excluded_band_indices=[1],
            sam_threshold_deg=180.0,
            min_confidence=0.0,
        ),
    )

    assert result.status == "success"
    assert result.wavelengths == [400.0, 600.0]
    assert 500.0 not in result.wavelengths


def test_qc_warnings_merged_into_result_warnings(tmp_path: Path) -> None:
    csv_path = tmp_path / "lib3.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,400,1.0\n"
        "class_a,500,0.0\n"
        "class_a,600,0.0\n"
        "class_b,400,0.0\n"
        "class_b,500,1.0\n"
        "class_b,600,0.0\n"
    )
    cube = np.ones((4, 4, 3), dtype=np.float32) * 0.5
    path = tmp_path / "merged_warnings.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
            classes=["class_a", "class_b"],
            spectral_library=str(csv_path),
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
    csv_path = tmp_path / "lib5.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        + "".join(f"class_a,{w},0.5\nclass_b,{w},0.3\n" for w in wavelengths)
    )

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            min_confidence=0.0,
            sam_threshold_deg=180.0,
            classes=["class_a", "class_b"],
            spectral_library=str(csv_path),
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

    mapper = SpectralMatcher()
    report = mapper.quality_file(
        path,
        MatchOptions(wavelengths=wavelengths, sensor="manual"),
    )

    assert report.shape == (3, 4, 5)


def test_prediction_fails_when_fewer_than_two_usable_bands_remain(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 2), dtype=np.float32) * 0.5
    path = tmp_path / "two_band.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    with pytest.raises(ValueError, match="At least two usable spectral bands"):
        SpectralMatcher().predict_file(
            path,
            MatchOptions(
                wavelengths=[400.0, 500.0],
                sensor="manual",
                classes=["Hema", "Goet"],
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
    csv_path = tmp_path / "lib3.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,400,0.5\n"
        "class_a,500,0.4\n"
        "class_a,600,0.3\n"
        "class_b,400,0.3\n"
        "class_b,500,0.4\n"
        "class_b,600,0.5\n"
    )

    result = SpectralMatcher().predict_file(
        mat_path,
        MatchOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
            classes=["class_a", "class_b"],
            spectral_library=str(csv_path),
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )
    assert result.status == "success"
    assert len(result.wavelengths) == 3
    assert "class_a" in result.statistics


def test_mat_file_qc_raster(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 3), dtype=np.float32) * 0.5
    mat_path = tmp_path / "test_qc.mat"
    scipy.io.savemat(mat_path, {"data": cube})

    mapper = SpectralMatcher()
    report = mapper.quality_file(
        mat_path,
        MatchOptions(
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
    mapper = SpectralMatcher()
    report = mapper.quality_file(
        mat_path,
        MatchOptions(
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
    mapper = SpectralMatcher()
    report = mapper.quality_file(
        mat_path,
        MatchOptions(
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
    mapper = SpectralMatcher()
    report = mapper.quality_file(
        mat_path,
        MatchOptions(
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
    mapper = SpectralMatcher()
    report = mapper.quality_file(
        mat_path,
        MatchOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
        ),
    )
    assert report.status == "pass"
    assert report.band_count == 3


def test_user_csv_library_with_real_names(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 2), dtype=np.float32) * 0.5
    path = tmp_path / "csv_library.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")

    csv_path = tmp_path / "test_library.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "hematite,400,0.5\n"
        "hematite,500,0.6\n"
        "goethite,400,0.4\n"
        "goethite,500,0.3\n"
    )

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            wavelengths=[400.0, 500.0],
            sensor="manual",
            classes=["hematite", "goethite"],
            spectral_library=str(csv_path),
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )

    assert result.status == "success"
    assert result.classes == ["hematite", "goethite"]


def test_mtmf_default_is_false() -> None:
    opts = MatchOptions()
    assert opts.use_mtmf is False


def test_use_mtmf_true_runs_mtmf_path(tmp_path: Path) -> None:
    cube = np.ones((4, 4, 3), dtype=np.float32) * 0.5
    path = tmp_path / "mtmf_flag.tif"
    tifffile.imwrite(path, cube, photometric="minisblack")
    csv_path = tmp_path / "lib3.csv"
    csv_path.write_text(
        "name,wavelength,reflectance\n"
        "class_a,400,0.5\n"
        "class_a,500,0.4\n"
        "class_a,600,0.3\n"
        "class_b,400,0.3\n"
        "class_b,500,0.4\n"
        "class_b,600,0.5\n"
    )

    result = SpectralMatcher().predict_file(
        path,
        MatchOptions(
            wavelengths=[400.0, 500.0, 600.0],
            sensor="manual",
            classes=["class_a", "class_b"],
            spectral_library=str(csv_path),
            use_mtmf=True,
            mf_threshold=0.0,
            infeas_threshold=1e6,
            min_confidence=0.0,
            sam_threshold_deg=180.0,
        ),
    )
    assert result.status == "success"
    assert "mtmf" in result.model_used
