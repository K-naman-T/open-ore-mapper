# USGS curated mineral library pack — next integrity increment

**Date:** 2026-07-26  
**Goal:** Land a **non-scene** mineral pack for the **unlabeled classical product path** (Track A foundation).  
**Not this task:** re-score with pure-GT scene endmembers (Track B already done).

---

## 0. Why this is the next integrity increment

| Track | Library source | Status (2026-07-26) |
|-------|----------------|---------------------|
| **B** full-scene / multi-seed | Median pure Tetracorder pixels | Scored (~0.72 / ~0.66 fuse) — **semi-dependent** |
| **C** supervised | Train labels → RF/HistGB/CNN | Research only — not product |
| **A** independent lab | USGS/lab CSV, **no pure-GT EMs** | **Missing** — required for honest “discovery” language |

Evidence in-repo:

- `benchmarks/cuprite_real/library.csv` = **scene endmembers** (8 minerals × 219 AVIRIS bands). README states it is not independent lab spectra.
- `scripts/run_cuprite_real_validation.py` rebuilds that CSV from high-purity GT pixels.
- `docs/BEST_NUMBERS.md` §Track A: multi-seed OA with non-scene library **not yet scored**.
- `ROADMAP.md`: “Curated USGS mineral pack for unlabeled runs”; “Independent library Track A multi-seed (next integrity win)”.
- Fail-closed: real mineral names without `--library` raise (no silent demo fallback) — `service.py` `_load_library`.

**Product win:** a user can run classical `fuse_classical` / SAM / MTMF with **real absorption features** and no Tetracorder labels.

---

## 1. Recommended mineral list (22 names)

Two tiers. Names are **stable OOM class ids** (lowercase, no spaces). Map 1:1 to Tetracorder legend where possible; extend for Cuprite classic SWIR suite.

### Tier 1 — Cuprite scoreboard core (8)  
Matches `benchmarks/cuprite_real/legend.json` (must exist for Track A map-to-map on current reference):

| OOM name | Role at Cuprite | Prefer USGS sample (splib07 AVIRIS-95 AREF, Chapter M) |
|----------|-----------------|--------------------------------------------------------|
| `kaolinite` | Dominant Al-clay | `Kaolinite_CM3_BECKa` or `CM9` fine-grained |
| `alunite` | Advanced argillic | `Alunite_GDS83_Na63_BECKb` (or Na-rich series) |
| `calcite` | Carbonate / playa | `Calcite_HS48.3B_BECKa` |
| `chalcedony` | Silica / sinter | `Chalcedony_CU91-6A_BECKa` (**Cuprite sample**) |
| `muscovite` | Phyllic / sericite | `Muscovite_GDS107_BECKa` |
| `montmorillonite` | Smectite | `Montmorillonite_CM20_BECKb` (or SWy-1 if present in ASD pack) |
| `hematite` | Fe-oxide | `Hematite_GDS27_BECKa` (powder; not coating-only) |
| `goethite` | Fe-oxide / limonite | `Goethite_HS36.3_BECKb` |

### Tier 2 — Cuprite-like unlabeled expansion (14)  
Classic Swayze/Clark suite + alteration neighbors; useful for product defaults and false-positive stress:

| OOM name | Why |
|----------|-----|
| `buddingtonite` | NH₄ feldspar — Cuprite classic; not in current 8-class GT |
| `dickite` | Kaolin polytype / advanced argillic |
| `halloysite` | Kaolin family confusion class |
| `pyrophyllite` | High-T Al alteration |
| `illite` | Sericite neighbor (muscovite confusion) |
| `jarosite` | Acid sulfate / Fe-sulfate |
| `gypsum` | Evaporite / sulfate water features |
| `opal` | Hydrated silica (with chalcedony) |
| `chlorite` | Propylitic background |
| `epidote` | Propylitic |
| `dolomite` | Carbonate neighbor of calcite |
| `nontronite` | Fe-smectite |
| `quartz` | Bright background / silicification (low diagnostic SWIR) |
| `magnetite` | Low-albedo oxide background |

**Pack size:** 22 spectra (within 10–30 target).  
**Optional slim pack (12):** Tier 1 + `buddingtonite`, `dickite`, `jarosite`, `pyrophyllite`.

Do **not** ship full Chapter M (~500+ minerals): project plan and ENVI practice both warn full libraries → false positives.

### Name alignment rules

- CSV `name` column = OOM id above (not USGS title string).
- Provenance file records exact USGS filename + sample id.
- Do **not** use `*_demo` names in this pack.
- `load_csv_library` requires **identical wavelength grid for all selected minerals** — build pack on one grid.

---

## 2. Source, license, redistribution

### Primary source: **USGS Spectral Library Version 7 (splib07)**

| Item | Value |
|------|--------|
| Data release | Kokaly et al. 2017, DOI [10.5066/F7RR1WDJ](https://doi.org/10.5066/F7RR1WDJ) |
| Report | Data Series 1035, [10.3133/ds1035](https://doi.org/10.3133/ds1035) |
| ScienceBase root | [item 5807a2a2e4b0841e59e3a18d](https://www.sciencebase.gov/catalog/item/5807a2a2e4b0841e59e3a18d) |
| ASCII child | [item 586e8c88e4b0f5ce109fccae](https://www.sciencebase.gov/catalog/item/586e8c88e4b0f5ce109fccae) “Spectra of materials in ASCII format” |
| Full mega-zip | `usgs_splib07.zip` ~5.1 GB on root item (avoid for pack build) |
| **Preferred download** | `ASCIIdata_splib07b_cvAVIRISc1995.zip` (~4.1 MB) **and/or** `ASCIIdata_splib07b_cvASD.zip` (~27 MB) |
| Lab tag | **splib07a** = measured native; **splib07b** = oversampled parent for convolutions |
| Product portal | https://www.usgs.gov/labs/spectroscopy-lab/usgs-spectral-library |

**Verified 2026-07-26:** AVIRIS-1995 ASCII zip downloads without auth; ~3148 files; `ChapterM_Minerals/` present; shared wavelength file `s07_AV95_Wavelengths_in_microns_224ch_AVIRIS95.1.txt` (224 channels, starts ~0.383 µm — matches Cuprite cube style).

**ASCII spectrum layout (convolved packs):**

```
s07_AV95 Record=…: Kaolinite CM3 … BECKa AREF
 5.3230727e-001
 5.6835204e-001
 …
```

- Line 0: header (title + instrument + `AREF` absolute reflectance).  
- Remaining lines: **reflectance only** (not λ,ρ pairs).  
- Pair with companion `*Wavelengths_in_microns*` file.  
- Prefer `*_AREF.txt`; skip `*_RREF.txt`, `errorbars/`, and pure-TIR `NIC4*` unless needed.  
- Deleted channels in native packs: `-1.23e34` (filter out).

### Which zip for which purpose

| Zip | Use |
|-----|-----|
| **`ASCIIdata_splib07b_cvAVIRISc1995.zip`** | Track A / Cuprite validation — bandpass-matched to AVIRIS-95; smallest |
| **`ASCIIdata_splib07b_cvASD.zip`** | Product default pack — dense 350–2500 nm @ 1 nm; resample to any sensor via existing `resample_library` |
| `ASCIIdata_splib07a.zip` | Audit / pick “best lab” sample if convolution artifacts suspected |

**Recommendation:** Build **product CSV from ASD convolution** (or native ASD in splib07a) → dense grid → OOM resamples to scene. Optionally also emit `libraries/usgs_cuprite_aviris95.csv` pre-convolved for fairer Track A on Cuprite.

### License vs Apache-2.0 project

| Source | Redistribute in repo? | Notes |
|--------|----------------------|--------|
| **USGS splib07** | **YES** | USGS-authored data is U.S. public domain; free use with attribution requested ([USGS copyrights & credits](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits)). DS1035 notes product is “for the most part” public domain; use USGS-measured mineral AREF only. |
| **ECOSTRESS / ASTER-JPL amalgam** | **NO bundle** | Footer: *Copyright © 2017, California Institute of Technology. ALL RIGHTS RESERVED.* Fetch-at-runtime only (`SPECTRAL_LIBRARIES_RESEARCH.md`). Contains USGS Reston spectra **mixed** with JPL/JHU — do not treat whole ECOSTRESS download as PD. |
| **RELAB** | Bundle only after per-policy check | `CONTRIBUTING.md`: fetch-at-runtime pending verification. |
| **Synthetic** `build_realistic_library.py` / `*_demo` | OK for tests | **Not** Track A / not product integrity. |

**Apache-2.0 compatibility:** Bundling USGS public-domain subset is allowed. Keep USGS data as **data files with NOTICE**, not re-licensed as Apache code. Ship:

```
libraries/usgs_v7_cuprite/NOTICE.txt
  USGS Spectral Library Version 7 (Kokaly et al. 2017)
  https://doi.org/10.5066/F7RR1WDJ
  U.S. public domain. Attribution requested.
  Subset: see manifest.json (sample ids).
```

`CONTRIBUTING.md` already allows “public-domain spectral libraries (USGS splib07a…)” with source URL + file list in PR description.

### splib08

Repo notes mention ongoing **splib08** work. **Do not block** on splib08: Version 7 is the frozen citable release with ScienceBase ASCII + AVIRIS-95 convolution. Revisit when USGS publishes a stable v8 data release with equivalent ASCII.

---

## 3. File layout

```
libraries/
  usgs_v7_cuprite/
    README.md                 # how to rebuild; citations
    NOTICE.txt                # public domain + DOI
    manifest.json             # OOM name → USGS filename, chapter, instrument, hash
    cuprite_core.csv          # Tier 1 (8) — dense or AVIRIS-95 grid
    cuprite_extended.csv      # Tier 1+2 (22)
    wavelengths_nm.json       # pack grid (nm), optional convenience
  README.md                   # index of packs

scripts/
  build_usgs_cuprite_library.py   # download zip → parse → write CSVs + manifest

examples/
  demo_library.csv            # KEEP as plumbing-only scaffolding (*_demo)
  # do NOT put USGS pack only under examples/ — product default should be libraries/
```

**Why `libraries/` not only `examples/`:**  
- `examples/demo_library.csv` is synthetic / demo-named.  
- Product default path must not look like a prototype.  
- `benchmarks/cuprite_real/library.csv` stays **scene-EM** for Track B reproducibility; do **not** overwrite with USGS (would destroy semi-dependent scoreboard reproducibility). Instead add:

```
benchmarks/cuprite_real/library_usgs.csv   # optional symlink or copy of cuprite_core/extended
benchmarks/cuprite_real/README.md          # document both libraries
```

### OOM CSV schema (already enforced)

```csv
name,wavelength,reflectance
kaolinite,383.15,0.5323
kaolinite,392.84,0.5684
...
alunite,383.15,0.61
...
```

Requirements from `spectral_library.load_csv_library`:

- Columns exactly: `name`, `wavelength`, `reflectance`
- Wavelengths **strictly increasing** per mineral
- **Same wavelength vector** for every selected mineral
- Finite floats; reflectance typically 0–1

Wavelength unit in CSV: **nanometers** (matches scene cubes and current cuprite library). Convert USGS microns × 1000.

Approx size: 22 minerals × ~2151 ASD bands ≈ 50k rows ≈ 1–2 MB CSV — fine to git.

---

## 4. Wiring CLI / product default (no pure-GT EMs)

### Current fail-closed behavior (keep)

```text
--library set     → load_csv_library + resample_library
*_demo only       → load_demo_library (plumbing)
real names, no CSV → ValueError ("Authoritative spectra unavailable…")
```

API rejects `spectral_library` paths (CLI-only) — leave as-is until multipart upload.

### Gaps to close

| Gap | Location | Fix |
|-----|----------|-----|
| CLI default minerals = **demo** | `cli.py` `_run_predict`: `DEFAULT_DEMO_MINERALS` | If `--library` provided, default minerals = all names in CSV (or Tier-1 list). Without library, keep fail-closed for real names. |
| Schema default minerals = real, no library | `schemas.DEFAULT_REAL_MINERALS` | Point docs + optional `OPEN_ORE_LIBRARY` env to `libraries/usgs_v7_cuprite/cuprite_extended.csv` |
| Classifier default `sam` | CLI / schema | Separate issue (product wants `fuse_classical`); pack is independent |
| `load_csv_library` always `is_authoritative=False` | `spectral_library.py` | Set `is_authoritative=True` when manifest says USGS, or when path under `libraries/usgs_*` / source string |
| Package data | `pyproject.toml` packages only `src/open_ore_mapper` | Add package-data or document “clone repo + path”; for PyPI later, ship pack under `src/open_ore_mapper/data/libraries/` **or** download script on first use |

### Concrete product command (target)

```bash
open-ore-mapper predict path/to/scene.tif \
  --wavelengths benchmarks/cuprite_real/wavelengths.json \
  --library libraries/usgs_v7_cuprite/cuprite_extended.csv \
  --minerals kaolinite,alunite,calcite,chalcedony,muscovite,montmorillonite,hematite,goethite \
  --classifier fuse_classical \
  --output-dir outputs/cuprite-usgs-lib/
```

**Defaults without GT:**

1. Prefer env `OPEN_ORE_LIBRARY` → path to extended CSV if file exists.  
2. Else, if installed package data present, use bundled pack.  
3. Else require explicit `--library` (fail-closed).  
4. Never invent spectra from Gaussians / RELAB cache labeled as authoritative without CSV.

**Do not** auto-select `benchmarks/cuprite_real/library.csv` as product default — that is scene pure-GT EMs.

### Builder script contract

`scripts/build_usgs_cuprite_library.py`:

1. Download chosen zip to `~/.cache/open-ore-mapper/usgs_splib07/` (checksum).  
2. Parse wavelength file + selected AREF spectra.  
3. Filter bad values; convert µm → nm.  
4. Optionally thin ASD to 5 nm for smaller CSV (document).  
5. Write `cuprite_core.csv`, `cuprite_extended.csv`, `manifest.json`.  
6. Print SAM angle matrix among pack members (sanity; median pairwise ≫ 0).

---

## 5. How Track A multi-seed uses the pack later

### What Track B does today

`scripts/spatial_split_eval.py` → `spatial_eval.run_spatial_split_eval`:

1. Spatial block split (seeds 42, 7, 99, 123, 2024).  
2. **`build_train_endmember_library`** from pure GT pixels in **train** blocks only.  
3. Classify; score **test** blocks only.  
4. Writes `train_library.csv` per seed.

### Track A change (minimal)

Keep spatial split + test scoring. **Replace step 2** with fixed USGS pack:

```text
library_csv = libraries/usgs_v7_cuprite/cuprite_core.csv   # 8 names ∩ legend
minerals    = legend class_names (intersection with pack)
# Do NOT call build_train_endmember_library
# Background stats for MTMF: still from train-block pixels (or full-scene valid) — OK, not class EMs
```

Implementation sketch:

- Add `--library-mode {train_endmembers,fixed_csv}` and `--library-csv` to `spatial_split_eval.py`.  
- Or new thin wrapper `scripts/spatial_split_eval_track_a.py`.  
- Multi-seed harness (same seeds as `outputs/research_spatial_fuse_multi/`).  
- Artifacts: `outputs/research_track_a_usgs/` with `all_seeds.json`, per-seed metrics, **no** train_library from GT pure pixels (or write a copy of the fixed CSV for provenance).

### Evaluation honesty for Track A

| Claim | Allowed? |
|-------|----------|
| “Multi-seed OA with **USGS lab** library vs Tetracorder” | Yes, with library provenance |
| “Independent mineral truth / ore proof” | **No** — still map-to-map vs Tetracorder |
| “Product discovery accuracy = Track B 0.66” | **No** — expect **lower** OA; that is the integrity point |
| Always-assign fuse OA without unknown rate | Mark as closed-set agreement; prefer open-set later |

### Taxonomy caveats (Track A blockers to metrics interpretation)

- GT has **8** classes; pack may have **22** → either (a) score only 8-class subset, or (b) map extras to ignore / confusion bins. Prefer **(a)** for comparable OA.  
- USGS lab vs airborne mixture / grain size / continuum → SAM/MTMF transfer loss expected.  
- `chalcedony` CU91-6A is Cuprite-sourced lab sample — still **not** scene pure-pixel EM; OK for Track A.  
- Class name collisions (muscovite vs illite vs sericite in Tetracorder) may need alias table in `manifest.json`.

### Ordering of work

1. Land pack CSV + builder + NOTICE (this doc).  
2. Smoke: `predict` + `evaluate` on cuprite_real **with** `library_usgs.csv` (full-scene OA diagnostic).  
3. Track A multi-seed fuse/MTMF/MNF-SAM.  
4. Publish numbers under BEST_NUMBERS Track A; **do not** replace Track B headline.

---

## 6. Blockers

### Shipping / legal

| # | Blocker | Severity | Mitigation |
|---|---------|----------|------------|
| L1 | Confusing USGS PD with **ECOSTRESS all-rights-reserved** | High if wrong source | Only ScienceBase splib07 ASCII; never speclib.jpl.nasa.gov bulk |
| L2 | Full 5 GB zip in CI/git | High | Subset CSV only; cache full zip outside git |
| L3 | Sample selection subjectivity | Med | Pin sample ids in `manifest.json` + regenerate script |

### Technical / product

| # | Blocker | Severity | Mitigation |
|---|---------|----------|------------|
| T1 | `load_csv_library` shared grid only | Low | Builder enforces one grid |
| T2 | Linear `np.interp` resample (not SRF convolution) | Med | Prefer AVIRIS-95 pre-convolved pack for Cuprite Track A; ASD+interp OK for product v1 (document) |
| T3 | CLI defaults still demo minerals + `sam` | High for   | Wire library default + `fuse_classical` separately (PRODUCT_PATH research) |
| T4 | `is_authoritative` never set for CSV | Med | Flag USGS pack True; keep scene-EM False |
| T5 | Package install path | Med | `importlib.resources` under package data **or** env path |
| T6 | Overwrite `cuprite_real/library.csv` | High if done naively | New filename; keep scene EM for Track B |
| T7 | Expected OA drop vs Track B | Social | Document before scoring; Track A is integrity not trophy |
| T8 | MTMF background still needs image stats | Low | Image covariance ≠ class EM; allowed in Track A |
| T9 | Missing minerals in ASD zip naming | Low | Fall back AVIRIS-95 or Beckman; assert in builder |
| T10 | Quartz/magnetite weak SWIR features | Low | Optional exclude from argmax packs; keep for abundance context only |

### Explicit non-blockers

- FTP `ftpext.cr.usgs.gov` dead — ScienceBase HTTPS works.  
- Old URL `speclab.cr.usgs.gov` deprecated — use DOI / ScienceBase.  
- Apache-2.0 project license does **not** forbid PD data bundling with NOTICE.

---

## 7. Implementation checklist (concrete)

- [ ] `scripts/build_usgs_cuprite_library.py` downloads ASD + AVIRIS-95 zips to cache  
- [ ] Emit `libraries/usgs_v7_cuprite/{cuprite_core,cuprite_extended}.csv` + `manifest.json` + `NOTICE.txt`  
- [ ] Unit test: load extended CSV, resample to 50 bands, shapes finite  
- [ ] Unit test: real mineral names + pack path succeeds; without path still fail-closed  
- [ ] Copy/link core pack → `benchmarks/cuprite_real/library_usgs.csv`  
- [ ] Document predict one-liner in `benchmarks/cuprite_real/README.md`  
- [ ] Track A: `spatial_split_eval --library-mode fixed_csv --library-csv …` multi-seed fuse  
- [ ] Fill `docs/BEST_NUMBERS.md` Track A table (mean±std OA)  
- [ ] PR description: DOI, ScienceBase item, sample list, public domain note  

---

## 8. Citations (required in NOTICE / README)

1. Kokaly, R.F., Clark, R.N., Swayze, G.A., Livo, K.E., Hoefen, T.M., Pearson, N.C., Wise, R.A., Benzel, W.M., Lowers, H.A., Driscoll, R.L., and Klein, A.J., 2017, **USGS Spectral Library Version 7**: U.S. Geological Survey Data Series 1035, 61 p., https://doi.org/10.3133/ds1035  

2. Kokaly, R.F., et al., 2017, **USGS Spectral Library Version 7 Data**: U.S. Geological Survey data release, https://doi.org/10.5066/F7RR1WDJ  

3. USGS, Copyrights and Credits — public domain policy: https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits  

---

## 9. One-paragraph recommendation

Ship a **22-mineral (or 12-slim) USGS splib07 subset** as long-form CSV under `libraries/usgs_v7_cuprite/`, built by a deterministic script from ScienceBase **`ASCIIdata_splib07b_cvASD.zip`** (product) and **`…cvAVIRISc1995.zip`** (Cuprite Track A), with NOTICE + sample-level `manifest.json`. Keep fail-closed loading; wire CLI/env default to this pack for real mineral names; **never** overwrite scene-EM `benchmarks/cuprite_real/library.csv`. Next integrity metric is multi-seed classical OA with this fixed pack (Track A)—expect lower OA than pure-GT endmembers; that delta is the product honesty gain.
