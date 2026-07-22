#!/usr/bin/env python3
"""Generate properly distinct synthetic mineral spectra for SAM discrimination."""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from numpy.typing import NDArray

WAVELENGTHS = np.arange(400.0, 2500.5, 5.0, dtype=np.float64)
NB = len(WAVELENGTHS)

OUT_DIR = os.path.expanduser("~/.cache/open-ore-mapper/relab/spectra")
os.makedirs(OUT_DIR, exist_ok=True)

np.random.seed(42)


def gaussian(wl: NDArray[np.float64], center: float, depth: float, fwhm: float) -> NDArray[np.float64]:
    sigma = fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    return 1.0 - depth * np.exp(-0.5 * ((wl - center) / sigma) ** 2)


def _save(name: str, reflectance: NDArray[np.float64]) -> None:
    path = os.path.join(OUT_DIR, f"{name}.tab")
    with open(path, "w") as f:
        f.write("# Wavelength Reflectance\n")
        for w, r in zip(WAVELENGTHS, reflectance):
            f.write(f"{w:.2f} {r:.6f}\n")


def linear_baseline(start: float, end: float) -> NDArray[np.float64]:
    return start + (end - start) * (WAVELENGTHS - 400.0) / (2100.0)


# ── Mineral generators ──────────────────────────────────────────────
# Each uses a characteristic BROADBAND SHAPE that differs from all others,
# plus diagnostic absorptions and small noise.

def gen_hematite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Strong red slope: 0.06 → 0.50 (400→800nm), plateau at 0.50
    baseline = np.where(wl < 800, 0.06 + 0.44 * (wl - 400) / 400, 0.50)
    r = baseline
    r *= gaussian(wl, 530.0, 0.20, 60.0)
    r *= gaussian(wl, 650.0, 0.10, 40.0)
    r *= gaussian(wl, 860.0, 0.30, 100.0)
    r += np.random.normal(0, 0.003, NB)
    return np.clip(r, 0.01, 1.0)


def gen_goethite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Hump shape: 0.04 → 0.55 (400→700nm), then 0.55 → 0.20 (700→2500nm)
    rise = 0.04 + 0.51 * (wl - 400) / 300
    fall = 0.55 - 0.35 * (wl - 700) / 1800
    baseline = np.where(wl < 700, rise, fall)
    r = baseline
    r *= gaussian(wl, 480.0, 0.12, 50.0)
    r *= gaussian(wl, 650.0, 0.05, 50.0)
    r *= gaussian(wl, 930.0, 0.35, 140.0)
    r *= gaussian(wl, 1400.0, 0.10, 60.0)
    r += np.random.normal(0, 0.003, NB)
    return np.clip(r, 0.01, 1.0)


def gen_jarosite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Strong downward slope: 0.72 → 0.18 (400→2500nm) — opposite of hematite
    baseline = 0.72 - 0.54 * (wl - 400) / 2100
    r = baseline
    r *= gaussian(wl, 430.0, 0.15, 50.0)
    r *= gaussian(wl, 920.0, 0.30, 120.0)
    r *= gaussian(wl, 1470.0, 0.08, 40.0)
    r *= gaussian(wl, 1850.0, 0.06, 35.0)
    r *= gaussian(wl, 2260.0, 0.35, 70.0)
    r += np.random.normal(0, 0.004, NB)
    return np.clip(r, 0.01, 1.0)


def gen_magnetite() -> NDArray[np.float64]:
    # Ultra-low flat: 0.04 constant — unique shape
    baseline = np.full(NB, 0.04)
    r = baseline
    r += np.random.normal(0, 0.002, NB)
    return np.clip(r, 0.01, 1.0)


def gen_kaolinite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Two-level: 0.45 in VNIR, 0.65 in SWIR (1800nm), then sharp drop at 2200nm
    vnir = np.full_like(wl, 0.45)
    swir_rise = 0.45 + 0.20 * (wl - 1300) / 500
    swir = np.minimum(swir_rise, 0.65)
    baseline = np.where(wl < 1300, vnir, swir)
    r = baseline
    r *= gaussian(wl, 1400.0, 0.18, 40.0)
    r *= gaussian(wl, 2165.0, 0.40, 25.0)
    r *= gaussian(wl, 2205.0, 0.50, 50.0)
    r *= gaussian(wl, 2320.0, 0.08, 30.0)
    r *= gaussian(wl, 2380.0, 0.08, 35.0)
    r += np.random.normal(0, 0.004, NB)
    return np.clip(r, 0.01, 1.0)


def gen_montmorillonite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Rising then deep water dip: 0.45 → 0.72 (400→1800nm), then strong 1900 water
    baseline = 0.45 + 0.27 * (wl - 400) / 1400
    baseline = np.minimum(baseline, 0.72)
    r = baseline
    r *= gaussian(wl, 1400.0, 0.15, 60.0)
    r *= gaussian(wl, 1900.0, 0.40, 80.0)
    r *= gaussian(wl, 2210.0, 0.30, 70.0)
    r *= gaussian(wl, 2340.0, 0.06, 40.0)
    r += np.random.normal(0, 0.004, NB)
    return np.clip(r, 0.01, 1.0)


def gen_illite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Steady rise: 0.40 → 0.80 (400→2500nm)
    baseline = 0.40 + 0.40 * (wl - 400) / 2100
    r = baseline
    r *= gaussian(wl, 1900.0, 0.08, 50.0)
    r *= gaussian(wl, 2200.0, 0.35, 60.0)
    r *= gaussian(wl, 2340.0, 0.18, 40.0)
    r *= gaussian(wl, 2440.0, 0.08, 30.0)
    r += np.random.normal(0, 0.004, NB)
    return np.clip(r, 0.01, 1.0)


def gen_calcite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # High flat with deep narrow dip: 0.90 flat, then huge 2340nm dip
    baseline = np.full_like(wl, 0.90)
    r = baseline
    r *= gaussian(wl, 1870.0, 0.06, 40.0)
    r *= gaussian(wl, 2000.0, 0.05, 35.0)
    r *= gaussian(wl, 2160.0, 0.08, 30.0)
    r *= gaussian(wl, 2340.0, 0.55, 50.0)
    r *= gaussian(wl, 2500.0, 0.20, 45.0)
    r += np.random.normal(0, 0.005, NB)
    return np.clip(r, 0.01, 1.0)


def gen_dolomite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    baseline = np.full_like(wl, 0.88)
    r = baseline
    r *= gaussian(wl, 2320.0, 0.50, 50.0)
    r *= gaussian(wl, 2250.0, 0.06, 30.0)
    r *= gaussian(wl, 2480.0, 0.18, 45.0)
    r += np.random.normal(0, 0.005, NB)
    return np.clip(r, 0.01, 1.0)


def gen_muscovite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Rising: 0.50 → 0.85 (400→2500nm), sharp 2200nm
    baseline = 0.50 + 0.35 * (wl - 400) / 2100
    r = baseline
    r *= gaussian(wl, 1900.0, 0.04, 40.0)
    r *= gaussian(wl, 2200.0, 0.45, 45.0)
    r *= gaussian(wl, 2340.0, 0.18, 35.0)
    r *= gaussian(wl, 2440.0, 0.10, 30.0)
    r += np.random.normal(0, 0.004, NB)
    return np.clip(r, 0.01, 1.0)


def gen_chlorite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Strong downward slope: 0.65 → 0.20 (400→2500nm)
    baseline = 0.65 - 0.45 * (wl - 400) / 2100
    r = baseline
    r *= gaussian(wl, 2250.0, 0.20, 50.0)
    r *= gaussian(wl, 2330.0, 0.28, 55.0)
    r *= gaussian(wl, 2380.0, 0.08, 35.0)
    r += np.random.normal(0, 0.003, NB)
    return np.clip(r, 0.01, 1.0)


def gen_epidote() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Downward slope: 0.58 → 0.22 (400→2500nm), similar to chlorite
    baseline = 0.58 - 0.36 * (wl - 400) / 2100
    r = baseline
    r *= gaussian(wl, 2250.0, 0.18, 45.0)
    r *= gaussian(wl, 2340.0, 0.22, 50.0)
    r += np.random.normal(0, 0.003, NB)
    return np.clip(r, 0.01, 1.0)


def gen_alunite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # High flat: 0.80, 2170+2220nm doublet
    baseline = np.full_like(wl, 0.80)
    r = baseline
    r *= gaussian(wl, 1480.0, 0.08, 35.0)
    r *= gaussian(wl, 1760.0, 0.06, 30.0)
    r *= gaussian(wl, 2170.0, 0.35, 35.0)
    r *= gaussian(wl, 2220.0, 0.20, 30.0)
    r *= gaussian(wl, 2320.0, 0.10, 35.0)
    r += np.random.normal(0, 0.004, NB)
    return np.clip(r, 0.01, 1.0)


def gen_gypsum() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # High with deep water features: 0.90 flat, strong 1900nm
    baseline = np.full_like(wl, 0.90)
    r = baseline
    r *= gaussian(wl, 1440.0, 0.20, 30.0)
    r *= gaussian(wl, 1490.0, 0.18, 25.0)
    r *= gaussian(wl, 1530.0, 0.10, 25.0)
    r *= gaussian(wl, 1740.0, 0.08, 30.0)
    r *= gaussian(wl, 1900.0, 0.55, 70.0)
    r *= gaussian(wl, 2210.0, 0.08, 40.0)
    r += np.random.normal(0, 0.005, NB)
    return np.clip(r, 0.01, 1.0)


def gen_quartz() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Very high, slightly decreasing: 0.95 → 0.82 (400→2500nm)
    baseline = 0.95 - 0.13 * (wl - 400) / 2100
    r = baseline
    r += np.random.normal(0, 0.003, NB)
    return np.clip(r, 0.01, 1.0)


def gen_pyrite() -> NDArray[np.float64]:
    wl = WAVELENGTHS
    # Low, slightly increasing: 0.08 → 0.25 (400→2500nm) — opposite slope to quartz
    baseline = 0.08 + 0.17 * (wl - 400) / 2100
    r = baseline
    r += np.random.normal(0, 0.002, NB)
    return np.clip(r, 0.01, 1.0)


MINERALS: list[tuple[str, str, str]] = [
    ("hematite", "oxide", gen_hematite),
    ("goethite", "oxide", gen_goethite),
    ("jarosite", "sulfate", gen_jarosite),
    ("magnetite", "oxide", gen_magnetite),
    ("kaolinite", "clay", gen_kaolinite),
    ("montmorillonite", "clay", gen_montmorillonite),
    ("illite", "clay", gen_illite),
    ("calcite", "carbonate", gen_calcite),
    ("dolomite", "carbonate", gen_dolomite),
    ("muscovite", "silicate", gen_muscovite),
    ("chlorite", "silicate", gen_chlorite),
    ("epidote", "silicate", gen_epidote),
    ("alunite", "sulfate", gen_alunite),
    ("gypsum", "sulfate", gen_gypsum),
    ("quartz", "silicate", gen_quartz),
    ("pyrite", "sulfide", gen_pyrite),
]


def main() -> None:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from open_ore_mapper.sam import compute_sam_angles

    spectra: list[NDArray[np.float64]] = []
    entries = []

    for name, mineral_class, gen_func in MINERALS:
        r = gen_func()
        spectra.append(r)
        _save(name, r)
        entries.append({
            "name": name,
            "mineral_class": mineral_class,
            "wavelength_min": 400.0,
            "wavelength_max": 2500.0,
            "filename": f"{name}.tab",
        })
        print(f"  {name:20s}  mean={r.mean():.4f}  range=[{r.min():.4f},{r.max():.4f}]  shape={_shape_label(name)}")

    index_path = os.path.join(OUT_DIR, "..", "index.json")
    with open(index_path, "w") as f:
        json.dump({"entries": entries}, f, indent=2)

    # ── Verify SAM angles ─────────────────────────────────────────────
    stack = np.asarray(spectra, dtype=np.float64)
    angles = compute_sam_angles(stack, stack)

    n = len(MINERALS)
    pair_angles = []

    print("\nSAM angle matrix (degrees):")
    print(f"{'':>20}", end="")
    for j in range(n):
        print(f"{MINERALS[j][0]:>12}", end="")
    print()

    for i in range(n):
        print(f"{MINERALS[i][0]:>20}", end="")
        for j in range(n):
            ang = angles[i, j]
            if i == j:
                print(f"{'—':>12}", end="")
            else:
                print(f"{ang:>8.2f}°  ", end="")
            if j > i:
                pair_angles.append(float(ang))
        print()

    pair_angles = np.array(pair_angles)

    pct_gt_5 = 100.0 * (pair_angles > 5.0).mean()
    pct_gt_15 = 100.0 * (pair_angles > 15.0).mean()
    pct_lt_3 = 100.0 * (pair_angles < 3.0).mean()
    min_angle = pair_angles.min()
    max_angle = pair_angles.max()
    median_angle = np.median(pair_angles)

    print("\n=== SAM Verification ===")
    print(f"  Pairs:                {len(pair_angles)}")
    print(f"  Median:               {median_angle:.2f}°")
    print(f"  Min:                  {min_angle:.2f}°")
    print(f"  Max:                  {max_angle:.2f}°")
    print(f"  Pairs > 5°:           {pct_gt_5:.0f}%")
    print(f"  Pairs > 15°:          {pct_gt_15:.0f}%  (target: ≥40%)")
    print(f"  Pairs < 3°:           {pct_lt_3:.0f}%  (target: ≤10%)")

    # Also report baseline reflectance extremes
    means = [s.mean() for s in spectra]
    print(f"  Mean reflectance range: [{min(means):.3f}, {max(means):.3f}]  (ratio: {max(means)/max(min(means), 0.001):.1f}x)")

    passed = pct_gt_15 >= 40.0 and pct_lt_3 <= 10.0
    if passed:
        print("\n✓ PASS: Spectra have sufficient SAM contrast.")
    else:
        failures = []
        if pct_gt_15 < 40.0:
            failures.append(f"pct_gt_15={pct_gt_15:.0f}% < 40%")
        if pct_lt_3 > 10.0:
            failures.append(f"pct_lt_3={pct_lt_3:.0f}% > 10%")
        print(f"\n✗ FAIL: {', '.join(failures)}")

    return 0 if passed else 1


def _shape_label(name: str) -> str:
    labels = {
        "hematite": "rise→plateau",
        "goethite": "hump↑↓",
        "jarosite": "steep↓",
        "magnetite": "ultra-low flat",
        "kaolinite": "two-level",
        "montmorillonite": "rise+water dip",
        "illite": "steady rise",
        "calcite": "high flat+2340",
        "dolomite": "high flat+2320",
        "muscovite": "mod rise",
        "chlorite": "steep↓",
        "epidote": "mod↓",
        "alunite": "high flat+doublet",
        "gypsum": "high flat+water",
        "quartz": "very high↓",
        "pyrite": "low↑",
    }
    return labels.get(name, "")


if __name__ == "__main__":
    sys.exit(main())
