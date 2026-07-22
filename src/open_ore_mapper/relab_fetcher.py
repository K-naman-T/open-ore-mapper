from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
import lxml.html
import numpy as np
from numpy.typing import NDArray

from .spectral_library import SpectralLibrary

CACHE_DIR = Path("~/.cache/open-ore-mapper/relab").expanduser()

_RELAB_BASE_URL = "https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/"

_FWHM_FACTOR = 2.0 * np.sqrt(2.0 * np.log(2.0))

CLASS_KEYWORDS: dict[str, list[str]] = {
    "oxide": ["hematite", "goethite", "magnetite", "ilmenite", "rutile", "corundum", "spinel", "chromite", "ferrihydrite", "limonite", "lepidocrocite", "maghemite", "wustite"],
    "clay": ["kaolinite", "montmorillonite", "illite", "smectite", "bentonite", "vermiculite", "chlorite", "serpentine", "talc", "pyrophyllite", "saponite", "nontronite", "dickite", "halloysite"],
    "carbonate": ["calcite", "dolomite", "magnesite", "siderite", "ankerite", "aragonite", "strontianite", "rhodochrosite", "smithsonite"],
    "sulfate": ["gypsum", "anhydrite", "jarosite", "alunite", "barite", "epsomite", "mirabilite", "thenardite", "kieserite", "polyhalite"],
    "silicate": ["quartz", "feldspar", "olivine", "pyroxene", "amphibole", "garnet", "mica", "muscovite", "biotite", "epidote", "zeolite", "plagioclase", "orthoclase", "albite", "anorthite", "diopside", "enstatite", "forsterite", "hornblende", "augite"],
    "phosphate": ["apatite", "monazite", "xenotime"],
    "sulfide": ["pyrite", "chalcopyrite", "galena", "sphalerite", "pyrrhotite"],
}


@dataclass(frozen=True)
class RelabEntry:
    name: str
    mineral_class: str
    wavelength_min: float
    wavelength_max: float
    filename: str


class RelabIndex:
    def __init__(self, entries: list[RelabEntry]) -> None:
        self._entries = list(entries)

    def search(
        self,
        q: str | None = None,
        mineral_class: str | None = None,
    ) -> list[RelabEntry]:
        results = self._entries
        if q is not None:
            lowered = q.lower()
            results = [e for e in results if lowered in e.name.lower()]
        if mineral_class is not None:
            results = [e for e in results if e.mineral_class == mineral_class]
        return list(results)

    def to_json(self) -> str:
        data = {
            "entries": [
                {
                    "name": e.name,
                    "mineral_class": e.mineral_class,
                    "wavelength_min": e.wavelength_min,
                    "wavelength_max": e.wavelength_max,
                    "filename": e.filename,
                }
                for e in self._entries
            ]
        }
        return json.dumps(data)

    @classmethod
    def from_json(cls, data: str) -> RelabIndex:
        parsed = json.loads(data)
        entries = [RelabEntry(**e) for e in parsed["entries"]]
        return cls(entries)


def parse_relab_tab(text: str) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    if not text.strip():
        raise ValueError("empty input")
    lines = text.strip().splitlines()
    wavelengths: list[float] = []
    reflectances: list[float] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if len(parts) < 2:
            continue
        try:
            wl = float(parts[0])
            ref = float(parts[1])
        except ValueError:
            continue
        wavelengths.append(wl)
        reflectances.append(ref)
    if len(wavelengths) < 2:
        raise ValueError("not enough data points")
    wl_arr = np.asarray(wavelengths, dtype=np.float32)
    ref_arr = np.asarray(reflectances, dtype=np.float32)
    if np.any(np.diff(wl_arr) <= 0):
        raise ValueError("wavelengths must be strictly increasing")
    return wl_arr, ref_arr


def gaussian_srf_resample(
    source_wl: NDArray[np.float32],
    source_spectrum: NDArray[np.float32],
    target_wl: NDArray[np.float32],
    fwhm: float | None = None,
) -> NDArray[np.float32]:
    if fwhm is None:
        if len(target_wl) > 1:
            fwhm = float(np.median(np.diff(target_wl)))
        else:
            fwhm = 10.0
    sigma = fwhm / _FWHM_FACTOR
    result: NDArray[np.float32] = np.empty(len(target_wl), dtype=np.float32)
    for i, t in enumerate(target_wl):
        weights = np.exp(-0.5 * ((source_wl - t) / sigma) ** 2)
        wsum: float = float(np.sum(weights))
        if wsum > 0:
            result[i] = np.average(source_spectrum, weights=weights)
        else:
            result[i] = 0.0
    return result


def ensure_cache_dir(cache_path: Path | None = None) -> Path:
    path = cache_path if cache_path is not None else CACHE_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


# ── new code ────────────────────────────────────────────────────


def _resolve_cache_dir(cache_dir: Path | None) -> Path:
    if cache_dir is not None:
        return cache_dir
    env = os.environ.get("OPEN_ORE_MAPPER_CACHE")
    if env:
        return Path(env)
    return CACHE_DIR


def infer_class(name: str) -> str:
    name_lower = name.lower()
    for mineral_class, keywords in CLASS_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return mineral_class
    return "unknown"


def _parse_href_links(html_text: str) -> list[str]:
    tree = lxml.html.fromstring(html_text)
    links: list[str] = []
    for anchor in tree.iter("a"):
        href = anchor.get("href")
        if href and not href.startswith("?") and href != "/":
            links.append(href)
    return links


def _infer_name_from_filename(filename: str) -> str:
    return filename.rsplit(".", 1)[0]


def fetch_relab_entries(base_url: str | None = None) -> list[RelabEntry]:
    url = base_url.rstrip("/") + "/" if base_url else _RELAB_BASE_URL

    resp = httpx.get(url, timeout=30.0)
    resp.raise_for_status()

    subdirs = _parse_href_links(resp.text)
    subdirs = [s.rstrip("/") for s in subdirs if s.endswith("/")]

    entries: list[RelabEntry] = []
    for subdir in subdirs:
        sub_url = urljoin(url, subdir + "/")
        sub_resp = httpx.get(sub_url, timeout=30.0)
        sub_resp.raise_for_status()

        filenames = _parse_href_links(sub_resp.text)
        tab_files = [f for f in filenames if f.endswith(".tab")]

        mineral_name = subdir.lower()
        mineral_class = infer_class(mineral_name)

        for tab_file in tab_files:
            entry_name = _infer_name_from_filename(tab_file)
            entries.append(RelabEntry(
                name=entry_name,
                mineral_class=mineral_class,
                wavelength_min=350.0,
                wavelength_max=2500.0,
                filename=tab_file,
            ))

    return entries


def download_spectrum(
    entry: RelabEntry,
    cache_dir: Path | None = None,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    cache_dir = _resolve_cache_dir(cache_dir)
    spectra_dir = cache_dir / "spectra"
    spectra_dir.mkdir(parents=True, exist_ok=True)

    cached_path = spectra_dir / entry.filename
    if cached_path.exists():
        text = cached_path.read_text(encoding="utf-8")
        return parse_relab_tab(text)

    base_url = _RELAB_BASE_URL
    resp = httpx.get(urljoin(base_url, entry.filename), timeout=30.0)
    resp.raise_for_status()
    text = resp.text

    cached_path.write_text(text, encoding="utf-8")
    return parse_relab_tab(text)


def build_spectral_library(
    target_minerals: list[str],
    target_wavelengths: NDArray[np.float32] | None = None,
    cache_dir: Path | None = None,
) -> SpectralLibrary:
    cache_dir = _resolve_cache_dir(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    spectra_dir = cache_dir / "spectra"
    spectra_dir.mkdir(parents=True, exist_ok=True)

    index_path = cache_dir / "index.json"
    if index_path.exists():
        index = RelabIndex.from_json(index_path.read_text(encoding="utf-8"))
    else:
        index = RelabIndex(fetch_relab_entries())
        index_path.write_text(index.to_json(), encoding="utf-8")

    matched = index.search(q="|".join(target_minerals))
    if not matched:
        matched = []
        for mineral in target_minerals:
            matched.extend(index.search(q=mineral))

    matched = list({e.filename: e for e in matched}.values())

    parsed: list[tuple[RelabEntry, NDArray[np.float32], NDArray[np.float32]]] = []
    all_wl: list[NDArray[np.float32]] = []
    for entry in matched:
        try:
            wl, ref = download_spectrum(entry, cache_dir=cache_dir)
        except Exception:
            continue
        parsed.append((entry, wl, ref))
        all_wl.append(wl)

    if not parsed:
        return SpectralLibrary(
            names=[],
            wavelengths=np.array([], dtype=np.float32),
            spectra=np.zeros((0, 0), dtype=np.float32),
            source="RELAB PDS",
            is_authoritative=True,
        )

    if target_wavelengths is not None:
        common_wl = np.asarray(target_wavelengths, dtype=np.float32)
    else:
        wl_min = max(float(np.min(w)) for _, w, _ in parsed)
        wl_max = min(float(np.max(w)) for _, w, _ in parsed)
        common_wl = np.arange(wl_min, wl_max + 1, 1.0, dtype=np.float32)

    names: list[str] = []
    spectra_rows: list[NDArray[np.float32]] = []
    for entry, wl, ref in parsed:
        names.append(entry.name)
        if len(wl) == len(common_wl) and np.allclose(wl, common_wl, atol=1e-5):
            spectra_rows.append(ref.astype(np.float32))
        else:
            resampled = gaussian_srf_resample(wl, ref, common_wl)
            spectra_rows.append(resampled)

    spectra_arr = np.stack(spectra_rows, axis=0)

    return SpectralLibrary(
        names=names,
        wavelengths=common_wl,
        spectra=spectra_arr,
        source="RELAB PDS",
        is_authoritative=True,
    )
