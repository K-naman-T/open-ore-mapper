#!/usr/bin/env python3
"""Build a miniature benchmark package for CI/demo Path A (not lab-measured spectra).

Creates dense VNIR–SWIR synthetic endmembers with diagnostic absorptions, a planted
scene cube, reference class map / ROIs, and options. Source is labeled fixture-only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import tifffile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmarks" / "demo_fixture"

# 400–2500 nm @ 10 nm → 211 bands (dense enough for absorption features)
WAVELENGTHS = np.arange(400.0, 2501.0, 10.0, dtype=np.float64)
NB = len(WAVELENGTHS)

# Fixture mineral definitions: (name, [(center_nm, depth, fwhm), ...], baseline)
MINERALS: list[tuple[str, list[tuple[float, float, float]], float]] = [
    ("hematite", [(530, 0.15, 60), (860, 0.28, 100)], 0.35),
    ("goethite", [(480, 0.12, 50), (930, 0.25, 120)], 0.38),
    ("kaolinite", [(1400, 0.18, 40), (2165, 0.35, 35), (2205, 0.40, 30)], 0.55),
    ("calcite", [(2335, 0.35, 50)], 0.60),
]


def _gauss(wl: np.ndarray, center: float, depth: float, fwhm: float) -> np.ndarray:
    sigma = fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))
    return 1.0 - depth * np.exp(-0.5 * ((wl - center) / sigma) ** 2)


def spectrum_for(features: list[tuple[float, float, float]], baseline: float) -> np.ndarray:
    r = np.full(NB, baseline, dtype=np.float64)
    for c, d, f in features:
        r *= _gauss(WAVELENGTHS, c, d, f)
    r += np.random.default_rng(0).normal(0, 0.001, NB)
    return np.clip(r, 0.02, 1.0)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    np.random.seed(42)

    spectra = {
        name: spectrum_for(feats, base) for name, feats, base in MINERALS
    }
    names = [m[0] for m in MINERALS]

    # library.csv
    lines = ["name,wavelength,reflectance"]
    for name in names:
        for wl, ref in zip(WAVELENGTHS, spectra[name], strict=True):
            lines.append(f"{name},{wl:.1f},{ref:.6f}")
    (OUT / "library.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Planted scene 32x32
    H, W = 32, 32
    cube = np.full((H, W, NB), 0.25, dtype=np.float32)
    ref = np.full((H, W), 255, dtype=np.uint8)
    patches = [
        (0, 16, 0, 16, 0),  # hematite
        (0, 16, 16, 32, 1),  # goethite
        (16, 32, 0, 16, 2),  # kaolinite
        (16, 32, 16, 32, 3),  # calcite
    ]
    rng = np.random.default_rng(1)
    for r0, r1, c0, c1, idx in patches:
        sp = spectra[names[idx]].astype(np.float32)
        noise = rng.normal(0, 0.005, (r1 - r0, c1 - c0, NB)).astype(np.float32)
        tile = np.broadcast_to(sp, (r1 - r0, c1 - c0, NB)).copy() + noise
        cube[r0:r1, c0:c1, :] = np.clip(tile, 0.02, 1.0)
        ref[r0:r1, c0:c1] = idx

    tifffile.imwrite(OUT / "scene.tif", cube, photometric="minisblack")
    tifffile.imwrite(OUT / "reference.tif", ref)

    (OUT / "wavelengths.json").write_text(
        json.dumps([float(w) for w in WAVELENGTHS], indent=2), encoding="utf-8"
    )
    legend = {
        "class_names": names,
        "ignore_index": 255,
        "note": "Indices match reference.tif class ids",
    }
    (OUT / "legend.json").write_text(json.dumps(legend, indent=2) + "\n", encoding="utf-8")

    options = {
        "minerals": names,
        "classifier": "sam",
        "min_confidence": 0.0,
        "sam_threshold_deg": 25.0,
        "tile_size": 16,
        "normalization": "l2",
        "sensor": "manual",
    }
    (OUT / "options.json").write_text(json.dumps(options, indent=2) + "\n", encoding="utf-8")

    rois = [
        {"mineral": "hematite", "row0": 2, "row1": 14, "col0": 2, "col1": 14},
        {"mineral": "goethite", "row0": 2, "row1": 14, "col0": 18, "col1": 30},
        {"mineral": "kaolinite", "row0": 18, "row1": 30, "col0": 2, "col1": 14},
        {"mineral": "calcite", "row0": 18, "row1": 30, "col0": 18, "col1": 30},
    ]
    (OUT / "rois.json").write_text(json.dumps(rois, indent=2) + "\n", encoding="utf-8")

    (OUT / "README.md").write_text(
        """# Demo fixture benchmark (CI / Path A smoke)

**Not laboratory spectra.** Dense analytic VNIR–SWIR curves with placed absorption
features, planted into `scene.tif`. Use for evaluate pipeline validation only.

| File | Role |
|------|------|
| `scene.tif` | H×W×bands planted cube |
| `library.csv` | Matching endmember spectra |
| `reference.tif` | Class map ground truth |
| `rois.json` | ROI boxes (subset of truth) |
| `legend.json` | Class names |
| `options.json` | Frozen MapperOptions |
| `wavelengths.json` | Band centers (nm) |

Run:

```bash
open-ore-mapper evaluate --benchmark benchmarks/demo_fixture --output-dir outputs/demo-fixture-eval
```
""",
        encoding="utf-8",
    )
    print(f"Wrote fixture to {OUT}")
    print(f"  scene {cube.shape}, bands {NB}, minerals {names}")


if __name__ == "__main__":
    main()
