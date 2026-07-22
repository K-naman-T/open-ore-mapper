#!/usr/bin/env python3
"""
Crawl & download real mineral spectra from the RELAB PDS server.

Strategy:
  1. List all .tab files across bdr2, bdr3, ftir1, ftir2 subdirectories
  2. For each, fetch the XML metadata (parallel batches) to get:
     - specimen_name / specimen_description (mineral name inference)
     - spectral_range_min / spectral_range_max (VNIR+SWIR filter)
  3. Download .tab for matching spectra (wavelength_min < 450, wavelength_max > 2400)
  4. Build index.json and validate all downloaded spectra
  5. Stop at MAX_SPECTRA
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import httpx
from lxml import etree, html

CACHE_DIR = Path.home() / ".cache/open-ore-mapper/relab"
SPECTRA_DIR = CACHE_DIR / "spectra"
INDEX_PATH = CACHE_DIR / "index.json"

RELAB_BASE = "https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/"
MAX_SPECTRA = 100
SCAN_BATCH = 30
DL_BATCH = 10

TARGET_KEYWORDS = [
    "hematite", "goethite", "jarosite", "magnetite", "kaolinite",
    "montmorillonite", "illite", "calcite", "dolomite", "muscovite",
    "chlorite", "epidote", "alunite", "gypsum", "pyrite", "quartz",
    "feldspar",
]

CLASS_KEYWORDS = {
    "oxide": ["hematite", "goethite", "magnetite", "ilmenite", "rutile", "corundum", "spinel", "chromite", "ferrihydrite", "limonite", "lepidocrocite", "maghemite", "wustite"],
    "clay": ["kaolinite", "montmorillonite", "illite", "smectite", "bentonite", "vermiculite", "chlorite", "serpentine", "talc", "pyrophyllite", "saponite", "nontronite", "dickite", "halloysite"],
    "carbonate": ["calcite", "dolomite", "magnesite", "siderite", "ankerite", "aragonite", "strontianite", "rhodochrosite", "smithsonite"],
    "sulfate": ["gypsum", "anhydrite", "jarosite", "alunite", "barite", "epsomite", "mirabilite", "thenardite", "kieserite", "polyhalite"],
    "silicate": ["quartz", "feldspar", "olivine", "pyroxene", "amphibole", "garnet", "mica", "muscovite", "biotite", "epidote", "zeolite", "plagioclase", "orthoclase", "albite", "anorthite", "diopside", "enstatite", "forsterite", "hornblende", "augite"],
    "phosphate": ["apatite", "monazite", "xenotime"],
    "sulfide": ["pyrite", "chalcopyrite", "galena", "sphalerite", "pyrrhotite"],
}


def infer_class(name: str) -> str:
    name_lower = name.lower()
    for mineral_class, keywords in CLASS_KEYWORDS.items():
        for kw in keywords:
            if kw in name_lower:
                return mineral_class
    return "unknown"


def _find_text(root: etree._Element, local_tag: str) -> str:
    for elem in root.iter():
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
        if tag == local_tag and elem.text and elem.text.strip():
            return elem.text.strip()
    return ""


def scan_xml(xml_text: str) -> dict:
    root = etree.fromstring(xml_text.encode())
    spec_name = _find_text(root, "specimen_name")
    spec_desc = _find_text(root, "specimen_description")
    range_min = _find_text(root, "spectral_range_min")
    range_max = _find_text(root, "spectral_range_max")
    material_type = _find_text(root, "material_type")
    file_name = _find_text(root, "file_name")
    return {
        "specimen_name": spec_name,
        "specimen_description": spec_desc,
        "range_min": range_min,
        "range_max": range_max,
        "material_type": material_type,
        "file_name": file_name,
    }


def extract_mineral(info: dict) -> str | None:
    combined = (info["specimen_name"] + " " + info["specimen_description"]).lower()
    for kw in TARGET_KEYWORDS:
        if kw in combined:
            return kw
    return None


def parse_tab_data(text: str) -> tuple[list[float], list[float]] | None:
    wavelengths: list[float] = []
    reflectances: list[float] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
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
        return None
    for i in range(1, len(wavelengths)):
        if wavelengths[i] <= wavelengths[i - 1]:
            return None
    return (wavelengths, reflectances)


async def list_tab_files(client: httpx.AsyncClient) -> list[tuple[str, str, str]]:
    result: list[tuple[str, str, str]] = []
    subdirs = ["bdr2", "bdr3", "ftir1", "ftir2"]
    for sd in subdirs:
        url = urljoin(RELAB_BASE, sd + "/")
        resp = await client.get(url)
        resp.raise_for_status()
        tree = html.fromstring(resp.text)
        for a in tree.iter("a"):
            href = a.get("href")
            if href and href.endswith(".tab"):
                fname = href.rsplit("/", 1)[-1]
                fid = fname.replace(".tab", "")
                result.append((sd, fid, fname))
    return result


async def run() -> int:
    SPECTRA_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # Step 1: list all .tab files
        print("Listing all .tab files across subdirectories...", file=sys.stderr)
        all_files = await list_tab_files(client)
        print(f"  Total .tab files: {len(all_files)}", file=sys.stderr)

        # Step 2: scan XML metadata in parallel, download matching spectra
        entries = []
        scanned = 0
        mineral_counts: dict[str, int] = {}
        skipped_no_match = 0
        skipped_range = 0
        skipped_parse = 0

        for start in range(0, len(all_files), SCAN_BATCH):
            if len(entries) >= MAX_SPECTRA:
                break

            batch = all_files[start : start + SCAN_BATCH]
            xml_urls = [urljoin(RELAB_BASE, f"{sd}/{fid}.xml") for sd, fid, _ in batch]

            xml_responses = await asyncio.gather(
                *[client.get(u) for u in xml_urls], return_exceptions=True
            )

            # Filter matching candidates
            candidates = []
            for (sd, fid, fname), xresp in zip(batch, xml_responses):
                if isinstance(xresp, Exception):
                    continue
                try:
                    info = scan_xml(xresp.text)
                except Exception:
                    continue

                mineral = extract_mineral(info)
                if mineral is None:
                    skipped_no_match += 1
                    continue

                try:
                    rmin = float(info["range_min"]) if info["range_min"] else 0
                    rmax = float(info["range_max"]) if info["range_max"] else 0
                except ValueError:
                    skipped_range += 1
                    continue

                if rmin >= 450 or rmax <= 2400:
                    skipped_range += 1
                    continue

                candidates.append((sd, fid, fname, mineral, rmin, rmax))
                scanned += 1

            if not candidates:
                continue

            # Download .tab files for candidates
            tab_urls = [
                (urljoin(RELAB_BASE, f"{sd}/{fname}"), sd, fid, fname, mineral, rmin, rmax)
                for sd, fid, fname, mineral, rmin, rmax in candidates
            ]

            for i in range(0, len(tab_urls), DL_BATCH):
                if len(entries) >= MAX_SPECTRA:
                    break

                dl_batch = tab_urls[i : i + DL_BATCH]
                dl_responses = await asyncio.gather(
                    *[client.get(url) for url, *_ in dl_batch], return_exceptions=True
                )

                for (url, sd, fid, fname, mineral, rmin, rmax), dlresp in zip(
                    dl_batch, dl_responses
                ):
                    if len(entries) >= MAX_SPECTRA:
                        break

                    if isinstance(dlresp, Exception):
                        print(f"    DL error {fname}: {dlresp}", file=sys.stderr)
                        continue

                    parsed = parse_tab_data(dlresp.text)
                    if parsed is None:
                        skipped_parse += 1
                        print(f"    Parse fail {fname}", file=sys.stderr)
                        continue

                    wavelengths, reflectances = parsed
                    wl_min = wavelengths[0]
                    wl_max = wavelengths[-1]

                    if wl_min >= 450 or wl_max <= 2400:
                        skipped_range += 1
                        continue

                    # Save
                    safe_name = f"{sd}_{fname}"
                    dest = SPECTRA_DIR / safe_name
                    dest.write_text(dlresp.text, encoding="utf-8")

                    cls = infer_class(mineral)
                    entries.append({
                        "name": mineral,
                        "mineral_class": cls,
                        "wavelength_min": wl_min,
                        "wavelength_max": wl_max,
                        "filename": safe_name,
                    })
                    mineral_counts[mineral] = mineral_counts.get(mineral, 0) + 1
                    n = len(entries)
                    print(
                        f"  [{n:3d}/{MAX_SPECTRA}] {sd}/{fname}: "
                        f"{mineral:15s} {wl_min:.0f}-{wl_max:.0f}nm {len(wavelengths):5d}pts",
                        file=sys.stderr,
                    )

            scanned += len(candidates)

        # Step 3: write index
        index_data = {"entries": entries}
        INDEX_PATH.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
        print(f"\nIndex written to {INDEX_PATH}", file=sys.stderr)

        # Step 4: validation
        print("\n=== Validation ===", file=sys.stderr)
        failures = 0
        ok = 0
        for entry in entries:
            filepath = SPECTRA_DIR / entry["filename"]
            text = filepath.read_text(encoding="utf-8")
            parsed = parse_tab_data(text)
            if parsed is None:
                print(f"  FAIL: {entry['filename']}", file=sys.stderr)
                failures += 1
                continue
            wl, _ = parsed
            spacings = [wl[i + 1] - wl[i] for i in range(len(wl) - 1)]
            med_spacing = sorted(spacings)[len(spacings) // 2]
            increasing = all(wl[i] < wl[i + 1] for i in range(len(wl) - 1))
            status = "OK" if increasing else "NON-INCR"
            print(
                f"  {status}: {entry['name']:20s} "
                f"{wl[0]:8.1f}-{wl[-1]:8.1f}nm "
                f"{len(wl):5d}pts spacing={med_spacing:.2f}nm",
                file=sys.stderr,
            )
            ok += 1

        # Summary to stdout
        classes: dict[str, int] = {}
        for e in entries:
            classes[e["mineral_class"]] = classes.get(e["mineral_class"], 0) + 1

        print(f"\nDownloaded {len(entries)}/{MAX_SPECTRA} spectra "
              f"(scan={scanned}, no_match={skipped_no_match}, "
              f"range_fail={skipped_range}, parse_fail={skipped_parse})")
        print(f"Minerals ({len(mineral_counts)}): "
              f"{', '.join(sorted(mineral_counts.keys()))}")
        print(f"Classes: {classes}")
        print("Wavelength ranges:")
        for e in sorted(entries, key=lambda x: x["name"]):
            print(f"  {e['name']:20s} {e['wavelength_min']:8.1f} - {e['wavelength_max']:8.1f} nm")
        print(f"Validation: {ok} passed, {failures} failed")

    return 0


if __name__ == "__main__":
    asyncio.run(run())
