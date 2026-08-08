import pytest

from spectral_matching.schemas import MatchOptions
from spectral_matching.wavelengths import parse_wavelengths_text, resolve_wavelengths, validate_wavelengths


def test_default_options_are_domain_neutral() -> None:
    options = MatchOptions()
    assert options.sensor == "cubert_ultris_s5"
    assert options.classes == []


def test_parse_manual_wavelengths_json() -> None:
    assert parse_wavelengths_text("[450, 500.5, 850]") == [450.0, 500.5, 850.0]


def test_parse_empty_wavelengths_text() -> None:
    assert parse_wavelengths_text("[]") == []


def test_reject_non_increasing_wavelengths() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        validate_wavelengths([500.0, 500.0, 450.0], expected_bands=3)


def test_reject_band_count_mismatch() -> None:
    with pytest.raises(ValueError, match="Expected 4 wavelengths"):
        validate_wavelengths([400.0, 500.0, 600.0], expected_bands=4)


def test_cubert_preset_has_51_bands() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "cubert_ultris_s5", expected_bands=51)
    assert sensor == "cubert_ultris_s5"
    assert len(wavelengths) == 51
    assert wavelengths[0] == 450.0
    assert wavelengths[-1] == 850.0


def test_aviris_preset_has_204_bands() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "aviris", expected_bands=204)
    assert sensor == "aviris"
    assert len(wavelengths) == 204
    assert wavelengths[0] == 366.0
    assert wavelengths[-1] == 2510.0


def test_emit_preset_has_285_bands() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "emit", expected_bands=285)
    assert sensor == "emit"
    assert len(wavelengths) == 285
    assert wavelengths[0] == 381.0
    assert wavelengths[-1] == 2493.0


def test_unknown_sensor_auto_resolves_known_grids() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "unknown_sensor", expected_bands=51)
    assert sensor == "aviris"
    assert len(wavelengths) == 51
    assert wavelengths[0] == 450.0
    assert wavelengths[-1] == 850.0

    wavelengths, sensor = resolve_wavelengths(None, "unknown_sensor", expected_bands=285)
    assert sensor == "emit"
    assert len(wavelengths) == 285


def test_missing_manual_wavelengths_fail_actionably() -> None:
    with pytest.raises(ValueError, match="Provide wavelengths"):
        resolve_wavelengths(None, "manual", expected_bands=6)


def test_unknown_sensor_with_unmatched_bands_fails_actionably() -> None:
    with pytest.raises(ValueError, match="Provide wavelengths"):
        resolve_wavelengths(None, "unknown_sensor", expected_bands=6)


def test_sensor_preset_band_mismatch_falls_back_to_auto_grid() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "emit", expected_bands=51)
    assert sensor == "aviris"
    assert len(wavelengths) == 51
