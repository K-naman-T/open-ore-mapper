import pytest

from spectral_matching.schemas import MatchOptions
from spectral_matching.wavelengths import (
    SENSOR_PRESETS,
    parse_wavelengths_text,
    resolve_wavelengths,
    validate_wavelengths,
)


def test_default_options_are_domain_neutral() -> None:
    options = MatchOptions()
    assert options.sensor == "aviris"
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


def test_aviris_preset_has_224_bands() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "aviris", expected_bands=224)
    assert sensor == "aviris"
    assert len(wavelengths) == 224
    assert wavelengths[0] == 400.0
    assert wavelengths[-1] == 2500.0


def test_aviris_ng_preset_uniform_5nm() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "aviris_ng", expected_bands=425)
    assert sensor == "aviris_ng"
    assert len(wavelengths) == 425
    assert wavelengths[0] == pytest.approx(376.86)
    assert wavelengths[-1] == pytest.approx(2496.86)
    step = wavelengths[1] - wavelengths[0]
    assert step == pytest.approx(5.0)
    assert all(
        b - a == pytest.approx(step) for a, b in zip(wavelengths[:-1], wavelengths[1:])
    )


def test_hyspex_presets_uniform() -> None:
    vnir_wl, sensor = resolve_wavelengths(None, "hyspex_vnir", expected_bands=186)
    assert sensor == "hyspex_vnir"
    assert len(vnir_wl) == 186
    assert vnir_wl[0] == pytest.approx(405.7000607)
    assert vnir_wl[1] - vnir_wl[0] == pytest.approx(3.19344621)

    swir_wl, sensor = resolve_wavelengths(None, "hyspex_swir", expected_bands=288)
    assert sensor == "hyspex_swir"
    assert len(swir_wl) == 288
    assert swir_wl[0] == pytest.approx(952.8263378)
    assert swir_wl[1] - swir_wl[0] == pytest.approx(5.448840168)


def test_hico_preset_128_bands() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "hico", expected_bands=128)
    assert sensor == "hico"
    assert len(wavelengths) == 128
    assert wavelengths[0] == pytest.approx(352.528)
    assert wavelengths[-1] == pytest.approx(1079.984)
    assert wavelengths[1] - wavelengths[0] == pytest.approx(5.728)


def test_emit_preset_has_285_bands() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "emit", expected_bands=285)
    assert sensor == "emit"
    assert len(wavelengths) == 285
    assert wavelengths[0] == 381.0
    assert wavelengths[-1] == 2497.5


def test_satellite_presets_band_counts() -> None:
    for name, expected_bands in (
        ("enmap", 244),
        ("prisma", 239),
        ("hyperion", 220),
        ("desis", 235),
        ("casi_1500", 288),
    ):
        wavelengths, sensor = resolve_wavelengths(None, name, expected_bands=expected_bands)
        assert sensor == name
        assert len(wavelengths) == expected_bands


def test_unknown_sensor_auto_resolves_known_grids() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "unknown_sensor", expected_bands=224)
    assert sensor == "aviris"
    assert len(wavelengths) == 224
    assert wavelengths[0] == 400.0
    assert wavelengths[-1] == 2500.0

    wavelengths, sensor = resolve_wavelengths(None, "unknown_sensor", expected_bands=285)
    assert sensor == "emit"
    assert len(wavelengths) == 285


def test_missing_manual_wavelengths_falls_back_to_generic() -> None:
    # 'manual' with no explicit wavelengths and no matching preset falls back
    # to a generic grid so the cube still processes (browser uploads never
    # send sensor or wavelengths).
    wavelengths, sensor = resolve_wavelengths(None, "manual", expected_bands=6)
    assert sensor == "generic"
    assert len(wavelengths) == 6
    assert wavelengths[0] == 400.0
    assert wavelengths[-1] == 2500.0


def test_unknown_sensor_with_unmatched_bands_falls_back_to_generic() -> None:
    # An unknown sensor with an unmatched band count now falls back to a
    # generic grid rather than erroring, so unknown cubes still process.
    wavelengths, sensor = resolve_wavelengths(None, "unknown_sensor", expected_bands=6)
    assert sensor == "generic"
    assert len(wavelengths) == 6
    assert wavelengths[0] == 400.0
    assert wavelengths[-1] == 2500.0


def test_sensor_preset_band_mismatch_falls_back_to_auto_grid() -> None:
    wavelengths, sensor = resolve_wavelengths(None, "emit", expected_bands=224)
    assert sensor == "aviris"
    assert len(wavelengths) == 224


def test_sensor_registry_duplicate_band_counts_are_documented() -> None:
    counts: dict[int, list[str]] = {}
    for preset in SENSOR_PRESETS.values():
        counts.setdefault(preset.bands, []).append(preset.name)
    # Known collisions: 288 = HySpex SWIR-384 and CASI-1500 (both documented).
    # Auto-detection picks the first; the collision is intentional and documented.
    for band_count, names in counts.items():
        if len(names) > 1:
            assert band_count == 288, f"unexpected collision at {band_count}: {names}"


def test_sensor_registry_exact_grids_are_monotonic() -> None:
    for preset in SENSOR_PRESETS.values():
        wl = preset.wavelengths()
        assert len(wl) == preset.bands
        assert all(b > a for a, b in zip(wl[:-1], wl[1:]))


def test_unknown_band_count_falls_back_to_generic_grid() -> None:
    # A cube with a band count matching no sensor preset (e.g. 48 or 51 after
    # the Cubert preset was removed) must resolve to a generic grid, not error.
    wl, sensor = resolve_wavelengths(None, "aviris", 48)
    assert sensor == "generic"
    assert len(wl) == 48
    assert wl[0] == 400.0
    assert wl[-1] == 2500.0

    wl, sensor = resolve_wavelengths(None, None, 51)
    assert sensor == "generic"
    assert len(wl) == 51
    assert wl[0] == 400.0
    assert wl[-1] == 2500.0

