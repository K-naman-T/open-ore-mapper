from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from spectral_matching.library import load_csv_bytes, load_csv_library, resample_library


def _small_csv_bytes() -> bytes:
    return (
        "class,wavelength,reflectance\n"
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
    ).encode("utf-8")


def _write_small_csv(path: Path) -> Path:
    path.write_bytes(_small_csv_bytes())
    return path


def test_load_csv_library_returns_arrays(tmp_path: Path) -> None:
    csv_path = _write_small_csv(tmp_path / "lib.csv")
    library = load_csv_library(csv_path, ["class_a", "class_b"])
    assert library.names == ["class_a", "class_b"]
    assert library.wavelengths.tolist() == [450.0, 550.0, 650.0, 750.0, 850.0]
    assert library.spectra.shape == (2, 5)
    assert np.all(np.isfinite(library.spectra))


def test_unknown_class_has_clear_error(tmp_path: Path) -> None:
    csv_path = _write_small_csv(tmp_path / "lib.csv")
    with pytest.raises(ValueError, match="Unknown classes"):
        load_csv_library(csv_path, ["unobtainium"])


def test_resample_preserves_requested_band_count(tmp_path: Path) -> None:
    csv_path = _write_small_csv(tmp_path / "lib.csv")
    library = load_csv_library(csv_path, ["class_a", "class_b"])
    target_wavelengths = [450.0, 550.0, 650.0, 850.0]
    resampled = resample_library(library, target_wavelengths)
    assert resampled.spectra.shape == (2, 4)
    assert resampled.wavelengths.tolist() == target_wavelengths
    assert np.all(np.isfinite(resampled.spectra))


def test_csv_library_does_not_claim_authoritative_spectra(tmp_path: Path) -> None:
    csv_path = _write_small_csv(tmp_path / "lib.csv")
    library = load_csv_library(csv_path, ["class_a"])
    assert not library.is_authoritative
    assert "user" in library.source.lower() or "csv" in library.source.lower()


def test_load_csv_bytes_roundtrip() -> None:
    library = load_csv_bytes(_small_csv_bytes())
    assert library.names == ["class_a", "class_b"]
    assert library.spectra.shape == (2, 5)


def test_rejects_non_increasing_csv_wavelengths(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(
        "class,wavelength,reflectance\n"
        "class_a,550,0.30\n"
        "class_a,450,0.42\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        load_csv_library(path, ["class_a"])


def test_resample_single_wavelength(tmp_path: Path) -> None:
    csv_path = _write_small_csv(tmp_path / "lib.csv")
    library = load_csv_library(csv_path, ["class_a", "class_b"])
    resampled = resample_library(library, [550.0])
    assert resampled.spectra.shape == (2, 1)
    assert resampled.wavelengths.tolist() == [550.0]


def test_resample_out_of_range_wavelength_clips_to_endpoint(tmp_path: Path) -> None:
    csv_path = _write_small_csv(tmp_path / "lib.csv")
    library = load_csv_library(csv_path, ["class_a"])
    resampled = resample_library(library, [9999.0])
    assert resampled.spectra.shape == (1, 1)
    assert np.isfinite(resampled.spectra[0, 0])
