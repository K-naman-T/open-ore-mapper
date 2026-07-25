# Iterative build — next increments (after Cuprite fuse_classical)

**Date:** 2026-07-26  
**Scope:** Product path only — unlabeled classical.  
**Anti-scope:** HybridSN, HistGB/RF/CNN product work, more Track C horse races.  
**Sources:** `README.md`, `ROADMAP.md`, `docs/BEST_NUMBERS.md`, `ADVERSARIAL_CONSENSUS.md`, `SUPERVISOR_GO_NOGO.md`, `PRODUCT_PATH_RESEARCH_2026.md`, `PRODUCT_UX_OPS_RESEARCH_2026.md`, code defaults.

---

## 1. Current baseline (done — cite files)

| Deliverable | Evidence |
|-------------|----------|
| Cuprite package + Tetracorder ref | `benchmarks/cuprite_real/` (`gt/`, `legend.json`, `library.csv` scene endmembers, `options.json` → `classifier: fuse_classical`) |
|   validation path | `scripts/run_cuprite_real_validation.py` — `DEFAULT_CLASSIFIER = "fuse_classical"` |
| Engine: fuse + classical stack | `src/open_ore_mapper/service.py` — `fuse_classical` = 0.7 MTMF + 0.2 CR-SAM + 0.1 MNF-SAM; also SAM/CR/MTMF/MNF |
| Scoreboard artifacts | `outputs/cuprite-real-eval/{comparison_panel,metrics,report,diff}.png/json/md` |
| Docs panel | `docs/assets/cuprite-gt-vs-ours.png` (+ ours/ref/diff) |
| Full-scene Track B diagnostic | OA **~0.72**, κ **~0.66** (`docs/BEST_NUMBERS.md`, metrics.json) |
| Multi-seed Track B external bar | fuse **0.664 ± 0.092** (`outputs/research_spatial_fuse_multi/`) |
| Evaluate CLI + package re-run | `open-ore-mapper evaluate --benchmark benchmarks/cuprite_real` |
| Honest claim framing | `docs/BEST_NUMBERS.md` Tracks A/B/C; `ADVERSARIAL_CONSENSUS.md` F1–F4 |
| Supervisor GO on script Path A | `docs/research_scrapes/SUPERVISOR_GO_NOGO.md` |
| Fail-closed CSV library load | `src/open_ore_mapper/spectral_library.py` |
| Dispatch tests for fuse | `tests/test_classify_dispatch.py`, `tests/test_cuprite_demo_path.py` |

**Not done (product surfaces still lag engine):**

| Gap | Where |
|-----|--------|
| Default classifier still **`sam`** | `schemas.py:70` `MapperOptions.classifier`; `cli.py:49`; `api.py` ~462 |
| CLI **cannot** select product classifier | `cli.py` choices omit `fuse_classical` / `fuse` |
| UI forces SAM/SFF only | `frontend/.../SettingsPanel.tsx` `CLASSIFIERS = ["SAM","SFF"]`; `Home.tsx` maps non-SFF → `sam` |
| AdvancedOptions default CR | `AdvancedOptions.tsx` `continuum_removal` |
| Track A independent USGS library | **Not scored** (`BEST_NUMBERS` Track A empty) |
| Open-set / unknown rate on scoreboard | fuse often `min_confidence=0` always-assign |
| Bundled authoritative USGS pack | No shippable `data/` mineral CSV in git; only demos + scene endmembers |
| Large scene data | **local-only** (see §7) |

---

## 2. Ordered next increments

### I1 — Align product classifier surfaces (defaults + CLI)

| | |
|--|--|
| **Goal** | One product classifier everywhere unlabeled: `fuse_classical`. |
| **User-visible** | `open-ore-mapper predict --classifier fuse_classical` works; bare `predict` / API default matches Cuprite script. |
| **Files** | `src/open_ore_mapper/{cli,schemas,api,benchmark}.py`; `tests/test_cli.py`, `test_api.py`, `test_benchmark_package.py`, `test_cuprite_demo_path.py` (assert default); README one-liner. |
| **Effort** | **S** |
| **Risks** | SAM-dependent unit tests / fixture OA=1.0 may need explicit `classifier="sam"`; default change is intentional product break. |
| **Acceptance** | (1) CLI help lists `fuse_classical`; (2) `MapperOptions().classifier == "fuse_classical"`; (3) API omit classifier → fuse; (4) `pytest` green; (5) Cuprite script still default fuse, metrics stable if re-run. |

### I2 — UI honesty strip (dead toggles + classical preset)

| | |
|--|--|
| **Goal** | UI only offers wired classical path; no ACE/veg theater; Path A CTA. |
| **User-visible** | Settings: fuse (or “Classical fuse”) + SAM/SFF as advanced; no live ACE/veg; CTAs “Try Cuprite benchmark” / “Run spectral match”; confidence = match score not probability. |
| **Files** | `frontend/src/{pages/Home,components/map/SettingsPanel,components/input/AdvancedOptions,components/sidebar/StatisticsTab,pages/MapView}.tsx` |
| **Effort** | **S–M** |
| **Risks** | E2E playwright may pin SAM; copy churn. |
| **Acceptance** | Playwright happy path uses fuse or documents SAM-only; no ACE/veg enabled; scorecard says map-to-map agreement when GT present. |

### I3 — Product preset JSON (“Cuprite classical”)

| | |
|--|--|
| **Goal** | Named frozen options for fair unlabeled runs (not ad-hoc flags). |
| **User-visible** | `--preset cuprite_classical` or documented `benchmarks/cuprite_real/options.json` reuse on predict. |
| **Files** | `src/open_ore_mapper/{cli,schemas,service}.py`; optional `presets/cuprite_classical.json`; tests. |
| **Effort** | **S** |
| **Risks** | Always-assign thresholds in package options (`min_confidence=0`) are **eval** settings — product preset should restore unknown gates for non-benchmark maps. |
| **Acceptance** | One command applies fuse + sensible thresholds; provenance records preset name. |

### I4 — Open-set / paint-coverage on scoreboard

| | |
|--|--|
| **Goal** | Stop closed-set-only OA as sole product metric. |
| **User-visible** | metrics/report: **% unknown**, precision-on-calls, paint coverage; ops fuse uses non-zero min_confidence/mf gates. |
| **Files** | `evaluate.py`, `service.py` fuse path, `run_cuprite_real_validation.py`, `BEST_NUMBERS.md` |
| **Effort** | **M** |
| **Risks** | OA drops when unknowns restored — document dual operating points (research always-assign vs product gated). |
| **Acceptance** | Scoreboard row for fuse@gated + unknown rate; product docs prefer gated for “real maps.” |

### I5 — USGS library Track A (smallest path) — **not I1**

| | |
|--|--|
| **Goal** | Independent lab library transfer score (science integrity). |
| **User-visible** | `metrics` with `library_source=usgs_…`, no pure-GT endmembers; Track A number (even if low). |
| **Files** | new `benchmarks/cuprite_real/library_usgs.csv` (or `data/libraries/usgs_cuprite_subset.csv`); loader may set `is_authoritative=True`; script flag `--library-mode independent`; `spatial_split_eval` Track A; `BEST_NUMBERS` Track A fill. |
| **Effort** | **M–L** (download + name align + resample + multi-seed). |
| **Risks** | Wavelength resampling; name mismatch vs Tetracorder legend; OA cliff → messaging panic. |
| **Acceptance** | Multi-seed fuse (or SAM/MTMF) OA reported under fixed USGS CSV; endmembers **not** from GT pure pixels; provenance screams Track A. |

**Smallest concrete Track A path:**

1. Hand-pick **8–12** Cuprite minerals already in `legend.json` / options minerals.  
2. Pull public-domain USGS splib07a/08 (or ECOSTRESS mineral) ASCII → long CSV `name,wavelength,reflectance` (cite Kokaly 2017).  
3. Resample to AVIRIS wavelengths in `wavelengths.json` (reuse `resample_library`).  
4. Run: full-scene fuse once + optional 1–2 seeds of spatial eval with **that CSV only**.  
5. Write Track A cell in `BEST_NUMBERS.md` (expect OA **below** Track B; that is success of honesty).  

**Do not** block I1–I3 on Track A. Consensus: library science is primary integrity track, but **product surface alignment ships first** (thin vertical; no 385 MB download in CI).

### I6 — UI Path A “Try Cuprite” (after I1–I2)

| | |
|--|--|
| **Goal** | Non-terminal first-time user sees GT \| Ours \| Diff. |
| **User-visible** | One button → panel + agreement scorecard (not bare accuracy). |
| **Files** | API evaluate/benchmark endpoint if missing; frontend Home/MapView; serve `reference.tif` carefully (local). |
| **Effort** | **L** |
| **Risks** | Cube not in git — need install script / cache path; memory. |
| **Acceptance** | First-time UI flow matches SUPERVISOR   bar without CLI. |

### I7 — EMIT Path B polish (only when Path A is boring)

Progress poll, GLT georef, worker isolation, **no OA** without reference. Effort **L**. Not next.

---

## 3. What NOT to do next

1. **HybridSN / SpectralFormer / more HistGB** as product or default.  
2. **Track C** multi-seed horse races for +0.01 OA.  
3. Claim **0.82** or bare **0.71** as product/mineral truth.  
4. Wire **ACE / vegetation / SUnSAL** “for completeness” before defaults + library integrity.  
5. **EMIT bbox** productization before CLI/API/UI classifier alignment.  
6. Bundle **demo Fe-oxides** as science library for real sensors.  
7. Full **splib** dump (hundreds of names) without curation — false positives.  
8. PyPI/deploy/export polish (Phase 4) while product surfaces still say SAM.

---

## 4. Recommended first PR (next session)

**Title:** `product: default + CLI expose fuse_classical`

**Thin slice only:**

1. Add `fuse` / `fuse_classical` to CLI `--classifier` choices.  
2. Change default in `MapperOptions`, CLI, API parse path from `"sam"` → `"fuse_classical"`.  
3. Keep `benchmark.py` default fallback consistent; fixture packages that need SAM set explicit classifier in `options.json` / tests.  
4. Tests: default asserts + `predict --classifier fuse_classical` smoke on demo fixture.  
5. README: “unlabeled default = fuse_classical”; Cuprite script remains hero.

**Out of PR:** USGS download, UI redesign, multi-seed Track A, EMIT.

**Why first:** Unblocks every other surface; **S** effort; matches ROADMAP v0.2 #1 and PRODUCT_PATH blockers #1–2; no local-only data required for CI.

---

## 5. USGS Track A — I1 or later?

**Later: I5.** After I1 (defaults) and preferably I3 (preset). Optional parallel research once I1 lands.

Rationale: product already ships semi-dependent Track B panel (GO). Track A is the **integrity** bar for discovery language, not the next   sitting. Smallest path in §2 I5 (8–12 mineral CSV + one fuse score).

---

## 6. CLI / API default classifier alignment plan

| Surface | Today | Target | Change |
|---------|-------|--------|--------|
| Cuprite script | `fuse_classical` ✓ | keep | none |
| `MapperOptions` | `sam` | `fuse_classical` | `schemas.py` |
| CLI `--classifier` | default `sam`; choices omit fuse | default fuse; choices include fuse | `cli.py` |
| API `options.classifier` | default `"sam"` | `fuse_classical` | `api.py` |
| `benchmark.load_options` | fallback `sam` | fallback `fuse_classical` | `benchmark.py` |
| Frontend | SAM only | fuse primary | I2 PR |
| AdvancedOptions | `continuum_removal` | fuse or inherit | I2 |

**Migration:** Explicit `classifier=sam` remains valid for regression/CI planted fixtures. Document: fuse needs multi-band VNIR–SWIR + real library; tiny Cubert may still want SAM — sensor presets can override later (not I1).

**Tests to fix/extend:** `test_benchmark_package` expects `sam` in some fixtures; `test_api` default; any client assuming SAM+NNLS only.

---

## 7. Dependencies / data still local-only

| Asset | Git? | Notes |
|-------|------|-------|
| `benchmarks/cuprite_real/scene.tif` (~385 MB) | **No** (`.gitignore` `benchmarks/**/scene.tif`) | Built by validation script from raw |
| `benchmarks/cuprite_real/raw/` (AVIRIS ENVI + 7z) | **No** (`benchmarks/**/raw/`) | Required for first Cuprite run |
| `outputs/**` | **No** | Local eval/research artifacts |
| `data/` runtime DB / large mats | **No** | |
| `reference.tif`, `legend.json`, `library.csv` (scene EM), `options.json`, `wavelengths.json`, `gt/*.fd.gz` | **Yes** (labels allowed; library is scene-derived CSV ~47 KB) | |
| `examples/demo_scene.tif`, demo CSV | **Yes** | CI / toy only |
| USGS splib bundle | **Not present** | Future Track A; public domain when added |
| Earthdata / EMIT granules | User creds + `[emit]` | Path B only |

**Onboard recipe remains:** obtain raw Cuprite → `python scripts/run_cuprite_real_validation.py` → panel under `outputs/cuprite-real-eval/`.

---

## Decision summary

```text
NOW     I1  fuse defaults + CLI choices          ← next PR
THEN    I2  UI honesty (wired classical only)
THEN    I3  named product preset (gated unknowns for non-eval)
THEN    I4  open-set metrics on scoreboard
THEN    I5  USGS Track A (8–12 mineral CSV + multi-seed)
LATER   I6  UI Try Cuprite
LATER   I7  EMIT Path B
NEVER   HybridSN/HistGB as product default
```

*End.*
