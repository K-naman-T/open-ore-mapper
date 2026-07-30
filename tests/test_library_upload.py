from __future__ import annotations

import numpy as np
import pytest

from spectral_matching.library import SpectralLibrary, load_csv_bytes


def _csv_bytes(rows: list[str]) -> bytes:
    header = "name,wavelength,reflectance"
    return "\n".join([header] + rows).encode("utf-8")


def test_load_csv_bytes_valid() -> None:
    csv = _csv_bytes([
        "hematite,450,0.4",
        "hematite,550,0.3",
        "hematite,650,0.35",
        "goethite,450,0.38",
        "goethite,550,0.44",
        "goethite,650,0.35",
    ])
    lib = load_csv_bytes(csv)
    assert isinstance(lib, SpectralLibrary)
    assert lib.names == ["hematite", "goethite"]
    assert lib.wavelengths.shape == (3,)
    np.testing.assert_array_almost_equal(lib.wavelengths, [450.0, 550.0, 650.0])
    assert lib.spectra.shape == (2, 3)
    np.testing.assert_array_almost_equal(lib.spectra[0], [0.4, 0.3, 0.35])
    np.testing.assert_array_almost_equal(lib.spectra[1], [0.38, 0.44, 0.35])


def test_load_csv_bytes_missing_columns() -> None:
    bad_csv = "name,reflectance\nhematite,0.5\n".encode("utf-8")
    with pytest.raises(ValueError, match="Spectral library CSV requires columns"):
        load_csv_bytes(bad_csv)


def test_load_csv_bytes_empty() -> None:
    csv = _csv_bytes([])
    with pytest.raises(ValueError, match="Spectral library CSV is empty"):
        load_csv_bytes(csv)


def test_load_csv_bytes_class_filtering() -> None:
    csv = _csv_bytes([
        "hematite,450,0.4",
        "hematite,550,0.3",
        "goethite,450,0.38",
        "goethite,550,0.44",
        "jarosite,450,0.52",
        "jarosite,550,0.48",
    ])
    lib = load_csv_bytes(csv, target_classes=["goethite", "jarosite"])
    assert lib.names == ["goethite", "jarosite"]
    assert lib.spectra.shape == (2, 2)


def test_load_csv_bytes_non_increasing_wavelengths() -> None:
    csv = _csv_bytes([
        "hematite,550,0.3",
        "hematite,450,0.4",
    ])
    with pytest.raises(ValueError, match="must be strictly increasing"):
        load_csv_bytes(csv)
