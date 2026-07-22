import pytest

from open_ore_mapper.schemas import MapperOptions
from open_ore_mapper.wavelengths import parse_wavelengths_text, resolve_wavelengths, validate_wavelengths


def test_default_options_are_public_demo_defaults() -> None:
    options = MapperOptions()
    assert options.sensor == "cubert_ultris_s5"
    assert len(options.minerals) >= 6  # minimum viable, could be DEFAULT_REAL_MINERALS


def test_parse_manual_wavelengths_json() -> None:
    assert parse_wavelengths_text("[450, 500.5, 850]") == [450.0, 500.5, 850.0]


def test_reject_non_increasing_wavelengths() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        validate_wavelengths([500.0, 500.0, 450.0], expected_bands=3)


def test_cubert_preset_has_51_bands() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "cubert_ultris_s5", expected_bands=51)
    assert sensor == "cubert_ultris_s5"
    assert len(wavelengths) == 51
    assert wavelengths[0] == 450.0
    assert wavelengths[-1] == 850.0


def test_missing_manual_wavelengths_fail_actionably() -> None:
    with pytest.raises(ValueError, match="Provide wavelengths"):
        resolve_wavelengths(None, "manual", expected_bands=6)
