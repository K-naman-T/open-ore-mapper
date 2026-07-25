# Best science + OA numbers

**Last run:** 2026-07-26 · Product default: **unsupervised classical** `fuse_classical`  
**Binding claims:** [`research_scrapes/ADVERSARIAL_CONSENSUS.md`](research_scrapes/ADVERSARIAL_CONSENSUS.md)

---

## Product proof panel (Cuprite)

![True-color | overlay | Tetracorder | solid | diff](assets/cuprite-gt-vs-ours.png)

*Map-to-map agreement with Tetracorder 4.4 fd maps. True-color is AVIRIS RGB (~650/550/470 nm); class mask is alpha-blended on terrain. Not field XRD. Not ore proof.*

| Full-scene fuse_classical | Spatial multi-seed fuse (5 seeds) |
|---------------------------|-----------------------------------|
| **OA ≈ 0.718** · κ ≈ 0.658 · n = 84 669 | **OA 0.664 ± 0.092** · κ ≈ 0.569 |

```bash
.venv/bin/python scripts/run_cuprite_real_validation.py
# outputs/cuprite-real-eval/{true_color,class_overlay,comparison_panel}.png
# metrics.json, report.md
```

Gallery:

| True-color | Overlay | Ours | Reference | Diff |
|------------|---------|------|-----------|------|
| ![tc](assets/cuprite-true-color.png) | ![ov](assets/cuprite-class-overlay.png) | ![ours](assets/cuprite-ours-fuse.png) | ![ref](assets/cuprite-reference-tetracorder.png) | ![diff](assets/cuprite-diff.png) |

---

## Track B — Classical (unsupervised)

### Full-scene scoreboard (n ≈ 84 669 labeled Tetracorder pixels)

Endmembers from pure GT pixels over the **full scene** (semi-dependent). Diagnostic only.

| Rank | Method | OA | Kappa | Kaolinite R | Command |
|-----:|--------|-----|-------|-------------|---------|
| 1 | **fuse_classical** | **~0.717** | **~0.657** | ~0.66 | `python scripts/run_cuprite_real_validation.py` |
| 2 | MNF-SAM (always assign) | ~0.71 | ~0.65 | ~0.64 | grid-search |
| 3 | MTMF | ~0.67 | ~0.61 | ~0.69 | `OPEN_ORE_CLASSIFIER=mtmf …` |
| 4 | CR-SAM | ~0.58 | ~0.49 | ~0.57 | `continuum_removal` |
| 5 | Full SAM+NNLS | ~0.34 | ~0.23 | ~0.07 | `sam` |

### Spatial multi-seed (preferred external classical bar)

Train-block endmembers / stats only; score **test blocks**; seeds 42, 7, 99, 123, 2024.

| Method | Mean OA ± std | Mean κ | Artifacts |
|--------|---------------|--------|-----------|
| **fuse_classical** | **0.664 ± 0.092** | 0.569 | `outputs/research_spatial_fuse_multi/` |
| mnf_sam | 0.635 ± 0.106 | 0.535 | `outputs/research_spatial_multi/` |
| mtmf | 0.629 ± 0.074 | 0.536 | same |
| continuum_removal | 0.556 ± 0.093 | 0.447 | same |
| sam | 0.361 ± 0.010 | 0.222 | same |

---

## Track C — Supervised (research only)

Train pure Tetracorder labels in train blocks → predict test blocks.  
**Map imitation / systems fusion — not product accuracy, not field truth.**

| Rank | Method | Mean OA ± std | Mean κ | Artifacts |
|-----:|--------|---------------|--------|-----------|
| 1 | HistGB · refl+MNF+MTMF | 0.816 ± 0.025 | 0.762 | `outputs/research_ml_boost/` |
| 2 | 1D-CNN · MNF-30 | 0.793 ± 0.046 | 0.735 | `outputs/research_ml_cnn1d/` |
| 3 | LightGBM · MNF | 0.791 ± 0.058 | 0.730 | `outputs/research_ml_boost_lgbm/` |
| 4 | RF · MNF | 0.788 ± 0.042 | 0.725 | `outputs/research_ml_rf/` |
| 5 | HistGB · MNF | 0.780 ± 0.059 | 0.717 | `outputs/research_ml_boost/` |
| 6 | RF · refl+MNF+MTMF | 0.779 ± 0.035 | 0.713 | `outputs/research_ml_rf/` |

**Matched MNF only:** CNN ≈ RF ≈ HistGB (~0.78–0.79) — **tie within seed noise**.  
Rich HistGB 0.816 uses classical **MTMF score features** (fusion, not a free spectral-net win).  
Retired: “+0.028 gate pass vs RF-MNF” as a science claim.

---

## Track A — Independent library (deferred)

Multi-seed OA with a **non-scene** USGS/lab library (no pure-GT endmembers).  
**Not yet scored** under our protocol. Required before stronger “discovery” claims.

---

## Consensus how-to-read

| Track | Headline | Product? |
|-------|----------|----------|
| **B multi-seed ~0.66** | Preferred **classical external** bar | Engineering bar for unlabeled maps |
| **B full-scene ~0.72** | Diagnostic with full pure-GT endmembers | Demo panel only |
| **C ~0.79–0.82** | Supervised Tetracorder agreement | **No** — research when labels exist |
| **A** | Independent library | **Future** |

**Product default for unlabeled scenes:** `fuse_classical` (and library matching generally).  
**Never claim:** HistGB/RF multi-seed OA as product accuracy or mineral truth.

---

## Reproduce research tables

```bash
# Classical multi-seed (example one method)
.venv/bin/python scripts/spatial_split_eval.py --methods fuse_classical --seed 42

# Supervised research (optional deps: pip install '.[ml]')
.venv/bin/python scripts/ml_spatial_rf_baseline.py --out outputs/research_ml_rf
.venv/bin/python scripts/ml_spatial_boost_baseline.py --backend hist --out outputs/research_ml_boost
.venv/bin/python scripts/ml_spatial_cnn1d_baseline.py --out outputs/research_ml_cnn1d
```

All numbers: real AVIRIS 1995 Cuprite + Tetracorder hard labels.  
None are planted-fixture OA=1.0. **None are independent field truth.**
