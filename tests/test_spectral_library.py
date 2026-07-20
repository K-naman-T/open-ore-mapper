from pathlib import Path

import numpy as np
import pytest

from open_ore_mapper.spectral_library import load_csv_library, load_demo_library, resample_library


def test_load_csv_library_returns_arrays() -> None:
    library = load_csv_library(Path("examples/demo_library.csv"), ["hematite_demo", "goethite_demo"])
    assert library.names == ["hematite_demo", "goethite_demo"]
    assert library.wavelengths.tolist() == [450.0, 550.0, 650.0, 750.0, 850.0]
    assert library.spectra.shape == (2, 5)
    assert np.all(np.isfinite(library.spectra))


def test_unknown_mineral_has_clear_error() -> None:
    with pytest.raises(ValueError, match="Unknown minerals"):
        load_demo_library(["unobtainium_demo"])


def test_resample_preserves_requested_band_count() -> None:
    library = load_demo_library(["hematite_demo", "goethite_demo"])
    target_wavelengths = [450.0, 550.0, 650.0, 850.0]
    resampled = resample_library(library, target_wavelengths)
    assert resampled.spectra.shape == (2, 4)
    assert resampled.wavelengths.tolist() == target_wavelengths
    assert np.all(np.isfinite(resampled.spectra))


def test_demo_library_does_not_claim_authoritative_spectra() -> None:
    library = load_demo_library(["hematite_demo"])
    assert not library.is_authoritative
    assert "synthetic" in library.source.lower()


def test_rejects_non_increasing_csv_wavelengths(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text(
        "name,wavelength,reflectance\n"
        "hematite_demo,550,0.30\n"
        "hematite_demo,450,0.42\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="strictly increasing"):
        load_csv_library(path, ["hematite_demo"])
