from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from open_ore_mapper.relab_fetcher import (
    RelabEntry,
    RelabIndex,
    build_spectral_library,
    download_spectrum,
    ensure_cache_dir,
    fetch_relab_entries,
    gaussian_srf_resample,
    infer_class,
    parse_relab_tab,
)


def _make_sample_entries() -> list[RelabEntry]:
    return [
        RelabEntry(name="hematite_foo", mineral_class="oxide", wavelength_min=400.0, wavelength_max=2500.0, filename="hematite_foo.tab"),
        RelabEntry(name="goethite_bar", mineral_class="oxide", wavelength_min=400.0, wavelength_max=2500.0, filename="goethite_bar.tab"),
        RelabEntry(name="calcite_baz", mineral_class="carbonate", wavelength_min=400.0, wavelength_max=2500.0, filename="calcite_baz.tab"),
        RelabEntry(name="Hematite_QUX", mineral_class="oxide", wavelength_min=400.0, wavelength_max=2500.0, filename="hematite_qux.tab"),
    ]


# ── existing tests ──────────────────────────────────────────────


def test_parse_tab_returns_wavelengths_and_reflectance() -> None:
    text = "wavelength\trefl\n400.0\t0.10\n500.0\t0.20\n600.0\t0.30\n"
    wl, ref = parse_relab_tab(text)
    assert wl.dtype == np.float32
    assert ref.dtype == np.float32
    assert len(wl) == len(ref) == 3
    np.testing.assert_allclose(wl, [400.0, 500.0, 600.0])
    np.testing.assert_allclose(ref, [0.10, 0.20, 0.30])
    assert all(np.diff(wl) > 0)


def test_parse_tab_rejects_empty_string() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_relab_tab("")


def test_search_by_name_returns_matching_entries() -> None:
    index = RelabIndex(_make_sample_entries())
    results = index.search(q="hematite")
    assert len(results) == 2
    assert all("hematite" in r.name.lower() for r in results)


def test_search_by_class_filters_correctly() -> None:
    index = RelabIndex(_make_sample_entries())
    results = index.search(mineral_class="oxide")
    assert len(results) == 3
    assert all(r.mineral_class == "oxide" for r in results)
    results2 = index.search(mineral_class="carbonate")
    assert len(results2) == 1
    assert results2[0].mineral_class == "carbonate"


def test_resample_to_target_wavelengths() -> None:
    source_wl = np.arange(400.0, 2501.0, dtype=np.float32)
    spectrum = np.zeros_like(source_wl)
    center = 900.0
    width = 50.0
    spectrum[:] = np.exp(-0.5 * ((source_wl - center) / width) ** 2)
    target_wl = np.array([500.0, 700.0, 900.0, 1100.0, 1300.0], dtype=np.float32)
    result = gaussian_srf_resample(source_wl, spectrum, target_wl)
    assert result.dtype == np.float32
    assert len(result) == len(target_wl)
    peak_idx = int(np.argmax(result))
    assert abs(target_wl[peak_idx] - center) < 10.0


def test_resample_gaussian_vs_linear() -> None:
    source_wl = np.arange(400.0, 2501.0, dtype=np.float32)
    spectrum = np.zeros_like(source_wl)
    center = 1000.0
    width = 10.0
    spectrum[:] = np.exp(-0.5 * ((source_wl - center) / width) ** 2)
    target_wl = np.arange(450.0, 2401.0, 50.0, dtype=np.float32)
    result = gaussian_srf_resample(source_wl, spectrum, target_wl)
    assert len(result) == len(target_wl)
    assert np.all(np.isfinite(result))


def test_cache_directory_created() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "test-cache" / "relab"
        result = ensure_cache_dir(target)
        assert result == target
        assert result.is_dir()


def test_index_from_json_roundtrip() -> None:
    entries = _make_sample_entries()
    index = RelabIndex(entries)
    serialized = index.to_json()
    loaded = RelabIndex.from_json(serialized)
    assert loaded.search(q="hematite") == index.search(q="hematite")
    assert loaded.search(mineral_class="carbonate") == index.search(mineral_class="carbonate")
    raw = json.loads(serialized)
    assert len(raw["entries"]) == 4


# ── infer_class ─────────────────────────────────────────────────


def test_infer_mineral_class_from_name() -> None:
    assert infer_class("hematite") == "oxide"
    assert infer_class("kaolinite") == "clay"
    assert infer_class("calcite") == "carbonate"
    assert infer_class("quartz") == "silicate"
    assert infer_class("olivine") == "silicate"
    assert infer_class("jarosite") == "sulfate"
    assert infer_class("unknown_mineral_xyz") == "unknown"


# ── fetch_relab_entries ─────────────────────────────────────────


@pytest.fixture
def mock_relab_index_html() -> str:
    """Simulates an Apache-style directory listing at data_reflectance/"""
    return """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html><head><title>Index of /speclib/urn-nasa-pds-relab/data_reflectance</title></head>
<body><h1>Index of data_reflectance</h1>
<pre>
<img src="/icons/folder.gif" alt="[DIR]"> <a href="hematite/">hematite/</a> 2025-01-01
<img src="/icons/folder.gif" alt="[DIR]"> <a href="goethite/">goethite/</a> 2025-01-01
<img src="/icons/folder.gif" alt="[DIR]"> <a href="calcite/">calcite/</a> 2025-01-01
</pre></body></html>"""


@pytest.fixture
def mock_subdir_html() -> str:
    """Simulates a subdirectory page with .tab files."""
    return """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html><head><title>Index of /speclib/.../hematite</title></head>
<body><h1>Index of hematite</h1>
<pre>
<img src="/icons/text.gif" alt="[TXT]"> <a href="hematite_foo.tab">hematite_foo.tab</a> 2025-01-01 1K
<img src="/icons/text.gif" alt="[TXT]"> <a href="hematite_bar.tab">hematite_bar.tab</a> 2025-01-01 1K
</pre></body></html>"""


def test_fetch_index_from_mock_server(mock_relab_index_html, mock_subdir_html) -> None:
    responses = {
        "https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/": mock_relab_index_html,
        "https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/hematite/": mock_subdir_html,
        "https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/goethite/": """<html><body><pre><a href="goethite_bar.tab">goethite_bar.tab</a></pre></body></html>""",
        "https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/calcite/": """<html><body><pre><a href="calcite_baz.tab">calcite_baz.tab</a></pre></body></html>""",
    }

    def mock_get(url, *args, **kwargs):
        content = responses.get(url, "")
        mock_resp = MagicMock()
        mock_resp.text = content
        mock_resp.raise_for_status = lambda: None
        mock_resp.status_code = 200
        return mock_resp

    with patch("open_ore_mapper.relab_fetcher.httpx.get", side_effect=mock_get):
        entries = fetch_relab_entries()

    assert len(entries) == 4

    names = {e.name for e in entries}
    assert "hematite_foo" in names
    assert "hematite_bar" in names
    assert "goethite_bar" in names
    assert "calcite_baz" in names

    for e in entries:
        assert e.filename.endswith(".tab")
        assert isinstance(e.wavelength_min, float)
        assert isinstance(e.wavelength_max, float)

    classes = {e.name: e.mineral_class for e in entries}
    assert classes["hematite_foo"] == "oxide"
    assert classes["hematite_bar"] == "oxide"
    assert classes["goethite_bar"] == "oxide"
    assert classes["calcite_baz"] == "carbonate"


# ── download_spectrum ───────────────────────────────────────────


@pytest.fixture
def mock_tab_content() -> str:
    return "wavelength\treflectance\n350.0\t0.123\n500.0\t0.234\n750.0\t0.345\n1000.0\t0.456\n"


def test_download_and_parse_tab(mock_tab_content) -> None:
    entry = RelabEntry(name="hematite_foo", mineral_class="oxide", wavelength_min=350.0, wavelength_max=1000.0, filename="hematite_foo.tab")

    def mock_get(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.text = mock_tab_content
        mock_resp.raise_for_status = lambda: None
        mock_resp.status_code = 200
        return mock_resp

    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        with patch("open_ore_mapper.relab_fetcher.httpx.get", side_effect=mock_get):
            wl, ref = download_spectrum(entry, cache_dir=cache_dir)

        assert wl.dtype == np.float32
        assert ref.dtype == np.float32
        np.testing.assert_allclose(wl, [350.0, 500.0, 750.0, 1000.0])
        np.testing.assert_allclose(ref, [0.123, 0.234, 0.345, 0.456])
        assert all(np.diff(wl) > 0)

        cached_file = cache_dir / "spectra" / "hematite_foo.tab"
        assert cached_file.exists()
        assert cached_file.read_text() == mock_tab_content


def test_fetch_all_skips_already_downloaded() -> None:
    entry = RelabEntry(name="hematite_foo", mineral_class="oxide", wavelength_min=350.0, wavelength_max=1000.0, filename="hematite_foo.tab")
    tab_data = "350.0\t0.1\n500.0\t0.2\n"

    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        spectra_dir = cache_dir / "spectra"
        spectra_dir.mkdir(parents=True)
        (spectra_dir / "hematite_foo.tab").write_text(tab_data)

        mock_get = MagicMock()
        with patch("open_ore_mapper.relab_fetcher.httpx.get", mock_get):
            # Download twice — first call uses cached, no HTTP
            wl1, ref1 = download_spectrum(entry, cache_dir=cache_dir)
            wl2, ref2 = download_spectrum(entry, cache_dir=cache_dir)

        mock_get.assert_not_called()
        np.testing.assert_allclose(wl1, wl2)
        np.testing.assert_allclose(ref1, ref2)
        np.testing.assert_allclose(wl1, [350.0, 500.0])


# ── build_spectral_library ──────────────────────────────────────


def test_build_library_from_cache() -> None:
    tab_data_1 = "350.0\t0.1\n500.0\t0.2\n750.0\t0.3\n"
    tab_data_2 = "350.0\t0.4\n500.0\t0.5\n750.0\t0.6\n"

    index_entries = [
        RelabEntry(name="hematite_foo", mineral_class="oxide", wavelength_min=350.0, wavelength_max=750.0, filename="hematite_foo.tab"),
        RelabEntry(name="goethite_bar", mineral_class="oxide", wavelength_min=350.0, wavelength_max=750.0, filename="goethite_bar.tab"),
    ]
    index = RelabIndex(index_entries)

    target_wl = np.array([350.0, 500.0, 750.0], dtype=np.float32)

    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        spectra_dir = cache_dir / "spectra"
        spectra_dir.mkdir(parents=True)
        (spectra_dir / "hematite_foo.tab").write_text(tab_data_1)
        (spectra_dir / "goethite_bar.tab").write_text(tab_data_2)
        (cache_dir / "index.json").write_text(index.to_json())

        library = build_spectral_library(
            target_minerals=["hematite", "goethite"],
            target_wavelengths=target_wl,
            cache_dir=cache_dir,
        )

    assert library.names == ["hematite_foo", "goethite_bar"]
    assert library.spectra.shape == (2, 3)
    assert library.wavelengths.dtype == np.float32
    np.testing.assert_allclose(library.wavelengths, target_wl)
    np.testing.assert_allclose(library.spectra[0], [0.1, 0.2, 0.3])
    np.testing.assert_allclose(library.spectra[1], [0.4, 0.5, 0.6])
    assert all(np.diff(library.wavelengths) > 0)
    assert library.source == "RELAB PDS"
    assert library.is_authoritative


# ── CLI ─────────────────────────────────────────────────────────


def test_cli_fetch_library_command(tmp_path: Path) -> None:
    """Run the CLI fetch-library command and verify outputs.

    Pre-populates the cache so the subprocess doesn't need network access.
    """
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True)
    spectra_dir = cache_dir / "spectra"
    spectra_dir.mkdir()

    index = RelabIndex([
        RelabEntry(name="hematite_foo", mineral_class="oxide", wavelength_min=350.0, wavelength_max=750.0, filename="hematite_foo.tab"),
    ])
    (cache_dir / "index.json").write_text(index.to_json(), encoding="utf-8")

    tab_data = "350.0\t0.1\n500.0\t0.2\n750.0\t0.3\n"
    (spectra_dir / "hematite_foo.tab").write_text(tab_data, encoding="utf-8")

    output_dir = tmp_path / "relab_output"

    env = {**__import__("os").environ, "OPEN_ORE_MAPPER_CACHE": str(cache_dir)}

    cli = shutil.which("open-ore-mapper") or str(Path(sys.executable).with_name("open-ore-mapper"))

    result = subprocess.run(
        [cli, "fetch-library",
         "--minerals", "hematite",
         "--output", str(output_dir)],
        capture_output=True, text=True, timeout=30,
        env=env,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert output_dir.exists()
    assert (output_dir / "index.json").exists()
