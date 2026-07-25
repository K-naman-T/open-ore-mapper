# Product path research — Cuprite classical (first-time user)

**Date:** 2026-07-26  
**Scope:** Verify open-ore-mapper for an unsupervised classical product path.  
**Anti-trophy rule:** Do **not** treat Track C HistGB/RF OA (~0.82) as product accuracy.  
**Sources:** code + `docs/BEST_NUMBERS.md` + `docs/research_scrapes/ADVERSARIAL_CONSENSUS.md`.

---

## Dimensions checked

| # | Dimension | Status |
|---|-----------|--------|
| 1 | Cuprite real validation code path | Traced |
| 2 | Service / evaluate / default classifier | Traced; defaults **split** |
| 3 | Outputs (maps, metrics, panel) | Verified on disk |
| 4 | Eval honesty (product-safe vs Track C) | From BEST_NUMBERS + consensus |
| 5 |   gaps (docs, CLI, UI claims) | Ranked blockers |

---

## 1. Current code path (Cuprite classical map)

### Primary entry (what a first-time user should run)

From repo root (venv with package importable, cube already under `benchmarks/cuprite_real/raw/`):

```bash
python scripts/run_cuprite_real_validation.py
# equivalent explicit product preset:
OPEN_ORE_CLASSIFIER=fuse_classical python scripts/run_cuprite_real_validation.py
```

**Default classifier in this script (must stay unsupervised classical):**  
`DEFAULT_CLASSIFIER = "fuse_classical"` — `scripts/run_cuprite_real_validation.py:51`.

Env override: `OPEN_ORE_CLASSIFIER` or `CLASSIFIER` (`:390–394`). Allowed classical set includes `fuse_classical`, `mtmf`, `mnf_sam`, `mnf_mtmf`, `continuum_removal`, `sam`, `sff` (`:399–408`). Unknown → falls back to `fuse_classical`.

### Pipeline (what the script does)

1. Load AVIRIS ENVI cube `benchmarks/cuprite_real/raw/cuprite95` + hdr (`:313–327`).
2. Build Tetracorder fd-max hard reference from `benchmarks/cuprite_real/gt/*.fd.gz` (`:130–163`, threshold ≥20).
3. Build **scene endmember** library (median pure-GT pixels) → `benchmarks/cuprite_real/library.csv` (`:197–247`, `:362–381`). **Semi-dependent**, not USGS lab transfer.
4. Write package: `scene.tif`, `reference.tif`, `wavelengths.json`, `legend.json`, `options.json` (`:383–443`).
5. `OreMapper.predict_file` + `_classify_core` with `MapperOptions(classifier=…)` (`:445–474`).
6. Score with `evaluate_maps` / `write_evaluation_artifacts` (`:481–500`).
7. Extra panel: `comparison_panel.png` + copy to `docs/assets/cuprite-gt-vs-ours.png` (`:509–517`).

### Service engine (fuse_classical)

`src/open_ore_mapper/service.py`:

- Implemented set includes `fuse_classical` (`:29–41`, dispatch `:229–238`).
- Fusion: **0.7 MTMF + 0.2 CR-SAM + 0.1 MNF-SAM**, argmax, **always-assign on valid pixels** (`:594–665`). Weights are Cuprite-OA-tuned — state that when quoting OA.
- Product consensus default for **unlabeled** scenes: classical fuse (`docs/BEST_NUMBERS.md:78`, consensus C7).

### Evaluate path (after package exists)

```bash
open-ore-mapper evaluate \
  --benchmark benchmarks/cuprite_real \
  --output-dir outputs/cuprite-real-eval
```

`benchmark.py` reads `options.json` (`classifier: fuse_classical` currently) and runs predict+scorecard.  
**Note:** this reuses the **scene-endmember library** already written by the validation script — same semi-dependent Track B setup.

Direct CLI `predict --classifier fuse_classical` is **broken for users** (choices omit fuse; see blockers).

---

## 2. Artifact paths expected

| Path | Role |
|------|------|
| `outputs/cuprite-real-eval/metrics.json` | OA, kappa, per-class, provenance |
| `outputs/cuprite-real-eval/report.md` | Human scorecard |
| `outputs/cuprite-real-eval/confusion.csv` | Confusion matrix |
| `outputs/cuprite-real-eval/our_class.png` | Predicted class RGB |
| `outputs/cuprite-real-eval/reference.png` | Tetracorder hard labels RGB |
| `outputs/cuprite-real-eval/diff.png` | Agree/disagree |
| `outputs/cuprite-real-eval/comparison_panel.png` | GT \| Ours \| Diff + footer OA |
| `docs/assets/cuprite-gt-vs-ours.png` | Docs copy of panel |
| `benchmarks/cuprite_real/{scene.tif,library.csv,reference.tif,options.json,…}` | Package for re-evaluate |

Observed full-scene run (`outputs/cuprite-real-eval/metrics.json`): **OA ≈ 0.713**, **κ ≈ 0.653**, **n_labeled = 84669** — Track B diagnostic with all pure-GT endmembers, not product SLA.

---

## 3. Eval honesty — product-safe vs trophies

From `docs/BEST_NUMBERS.md` + `docs/research_scrapes/ADVERSARIAL_CONSENSUS.md`:

| Track | Headline | Product-safe? | Use |
|-------|----------|---------------|-----|
| **B full-scene** fuse | OA **0.713** | Internal / diagnostic only | Engine ablation with pure-GT endmembers |
| **B multi-seed** fuse | **0.664 ± 0.092** | Prefer for external classical claim | Spatial hold-out, still GT-endmember |
| **C HistGB rich** | **0.816 ± 0.025** (~“0.82”) | **No** | Map-emulator / systems fusion with train labels |
| **C RF/CNN MNF** | ~0.79 | **No** as product default | Research only; not library transfer |
| **A independent library** | *missing* | Required for science integrity | Not scored multi-seed yet |

All OAs = **map-to-map agreement with Tetracorder 4.4 fd-max hard labels**, not field/XRD mineral truth.

**Product default (unlabeled):** `fuse_classical` — never HistGB/RF/CNN (`ADVERSARIAL_CONSENSUS` unanimous §C.4, F2).

---

## 4. Forbidden claims list

Do **not** put in UI, README hero, sales, or   docs:

1. “**82% accurate** minerals / product accuracy” (Track C closed-set emulator).
2. “HistGB **wins science** / supervised spatial **leader** for mineral mapping.”
3. “**Gate pass +0.028** vs RF” (unfair features; retired).
4. Bare “**71% accuracy**” without “semi-dependent pure-GT endmembers + Tetracorder agreement.”
5. “**ML beats classical** for exploration mapping” (different tasks; teacher circularity).
6. “Detects **ore** / finds **deposits** / replaces field validation.”
7. Any OA on **EMIT/upload without GT**.
8. Fixture **OA=1.0** as science proof.
9. “1D-CNN fails / nets don’t help” (under-trained baseline).
10. Single ladder ranking HistGB above fuse for **unlabeled** product maps.

**Allowed product language patterns:**  
“Default unlabeled mapping is classical fusion (`fuse_classical`). Full-scene Cuprite panel is Tetracorder agreement with scene endmembers (semi-dependent). Prefer multi-seed ~0.66 for external classical reference. Candidates only — not ore proof.”

---

## 5. Blockers ranked

### Blocking (  product path fails or misleads)

| Rank | Blocker | Evidence |
|-----:|---------|----------|
| 1 | **Product defaults are not `fuse_classical`.** Schema / CLI / API default remains **`sam`**. | `schemas.py:70`; `cli.py:49`; `api.py` default `"sam"` |
| 2 | **CLI cannot select product classifier.** `predict --classifier` choices omit `fuse_classical` (and fuse). | `cli.py:48–62` |
| 3 | **Frontend forces SAM.** UI default `"SAM"`; map path maps non-SFF → `"sam"` only. | `Home.tsx:23`, `:99–103`; `SettingsPanel.tsx:16` `CLASSIFIERS = ["SAM","SFF"]` |
| 4 | **README is stale and wrong for current engine.** Claims “SAM + NNLS is the only pipeline that affects final output” and “MTMF not wired.” Contradicts implemented fuse/MTMF paths. | `README.md:15–36` vs `service.py:206–238` |
| 5 | **Semi-dependent library only.** Scene pure-GT endmembers; Track A independent USGS/lab transfer **missing** — user may think 0.71 is discovery accuracy. | Script docstring `:197–209`; consensus §C.9 |
| 6 | **Panel footer mislabels engine.** Still “Ours (SAM+NNLS)” / “CR+region SAM” when fuse runs. | `run_cuprite_real_validation.py:289–303` |
| 7 | **Always-assign OA mode for fuse** (`min_confidence=0`, no unknown gate) inflates closed-set agreement; product maps need honest unknowns. | Script `:411–415`; `service.py:607–608` |

### Nice-to-have (not ship-stoppers for script-only Cuprite demo)

| Rank | Item | Evidence |
|-----:|------|----------|
| 8 | UI “Overall accuracy X%” without protocol (fixture/benchmark path). | `MapView.tsx:241–243`; `Home.tsx:67` |
| 9 | AdvancedOptions default `continuum_removal` ≠ fuse; only sam/CR in select. | `AdvancedOptions.tsx:10–54` |
| 10 | No single   one-pager (“run this, open that PNG”) outside research scrapes. | `benchmarks/cuprite_real/README.md` is minimal; README quickstart is demo SAM |
| 11 | `report.md` says “Overall accuracy” without Tetracorder-agreement framing. | `evaluate.py:261` |
| 12 | Track C research dirs (`outputs/research_ml_*`) easy to confuse with product. | Layout under `outputs/` |

---

## 6. Default classifier name (product)

| Surface | Current default | Required product default |
|---------|-----------------|---------------------------|
| Cuprite validation script | **`fuse_classical`** ✓ | Keep |
| `MapperOptions` / CLI / API | **`sam`** ✗ | **`fuse_classical`** (unsupervised classical) |
| Frontend Home | **SAM** ✗ | Classical fuse (or hide ML; never HistGB) |
| Benchmark options.json (post-script) | **`fuse_classical`** ✓ | Keep |

**Do not** set HistGB, RF, LightGBM, or CNN as product default.

---

## 7. Minimal   recipe (classical Cuprite map only)

```bash
# Prerequisites: package installable; cube present at
#   benchmarks/cuprite_real/raw/cuprite95 (+ .hdr); GT under gt/
cd /path/to/open-ore-mapper
python scripts/run_cuprite_real_validation.py
# Open:
#   outputs/cuprite-real-eval/comparison_panel.png
#   outputs/cuprite-real-eval/metrics.json
#   outputs/cuprite-real-eval/report.md
```

Read OA as **Tetracorder agreement (semi-dependent library)**, not product mineral truth. Prefer quoting multi-seed fuse **0.664±0.092** for external classical claims when available (`outputs/research_spatial_fuse_multi/`).

---

## 8. Bottom line

The **only honest -first classical product demo today** is the scripted Cuprite path defaulting to **`fuse_classical`**, writing maps + metrics under `outputs/cuprite-real-eval/`. Schema/CLI/UI still ship **SAM**, README denies the wired classical stack, and **~0.82 HistGB** is a Track C trophy — not the product number. Ship language and defaults must follow consensus F1/F2 before any accuracy theater in the UI.

*End of product-path research scrape.*
