# Plan: Open Ore Mapper → Spectral (v2 Pivot)

**Objective:** Rebrand from mineral-specific tool to a universal spectral matching engine. Domain-agnostic. Anyone with a hyperspectral cube and a spectral library CSV gets classification.

**Principle:** Delete before you rename. Test after every phase. Adversarial subagent reviews every test file.

---

## Phase 0: Before Anything — Run the Full Suite

Ensure everything passes before touching anything:

```
make check-all  # lint + typecheck + test-all
cd frontend && npm run lint && npm run build
```

Capture the baseline. If anything fails, stop and fix first.

---

## Phase 1: Delete Dead Modules + Strip Dependencies

### 1.1 Delete source modules (12 files)

| File | Reason |
|------|--------|
| `mineral_features.py` | Hardcoded mineral absorption DB — anti-pivot |
| `vegetation.py` | Never wired into pipeline |
| `ace.py` | Never wired into pipeline |
| `ml_rf.py` | Research only, supervised |
| `ml_boost.py` | Research only, supervised |
| `ml_cnn1d.py` | Research only, supervised |
| `evaluate.py` | Needs reference labels — not product |
| `benchmark.py` | Depends on evaluate.py |
| `spatial_eval.py` | Depends on evaluate.py |
| `relab_fetcher.py` | RELAB = mineral-only, domain-specific |
| `emit_client.py` | EMIT bbox pipeline — experimental, domain-specific |
| `public_scenes.py` | Domain-specific scene catalog |

### 1.2 Delete test files that import deleted modules (14 files)

| Test File | Deletes With |
|-----------|-------------|
| `test_ace.py` | ace.py |
| `test_vegetation.py` | vegetation.py |
| `test_ml_rf.py` | ml_rf.py |
| `test_ml_boost.py` | ml_boost.py |
| `test_ml_cnn1d.py` | ml_cnn1d.py |
| `test_evaluate.py` | evaluate.py |
| `test_benchmark_package.py` | benchmark.py + evaluate.py |
| `test_cuprite_demo_path.py` | evaluate.py |
| `test_sff.py` | mineral_features.py (transitive via sff.py) |
| `test_emit_client.py` | emit_client.py |
| `test_bbox_jobs.py` | emit_client.py (transitive via api.py) |
| `test_relab_fetcher.py` | relab_fetcher.py |
| `test_api.py` | benchmark.py + emit_client.py (transitive) |
| `test_cli.py` | benchmark.py, relab_fetcher.py, public_scenes.py (transitive) |

Surviving: 17 test files (test_classify_dispatch, test_continuum_removal, test_cr_sam, test_e2e_mineral_detection, test_mnf, test_mtmf, test_preprocessing, test_qc, test_rendering, test_sam, test_service, test_spectral_library, test_store, test_sunsal, test_tileserver, test_tiling, test_unmixing, test_wavelengths)

### 1.3 Delete data dirs

| Path | Why |
|------|-----|
| `benchmarks/cuprite_real/` | Cuprite validation — domain-specific |
| `benchmarks/cuprite/` | Cuprite variant |
| `benchmarks/demo_fixture/` | Demo fixture with mineral reference |
| `docs/BEST_NUMBERS.md` | Scoreboard Tracks A/B/C — mineral domain |
| `docs/research_scrapes/` | Adversarial research — mineral domain |
| `outputs/` (all subdirs) | Cached run artifacts |

### 1.4 Strip deleted imports from surviving source (7 files)

**`sff.py`:**
The file depends directly on `mineral_features`. Since mineral_features is deleted, and generalizing SFF is a v2 item, we have two choices:
- (A) **Delete sff.py entirely** — cleanest, removes ~206 lines of mineral-specific code, SFF isn't a primary classifier.
- (B) Generalize SFF — significant work, not v1.

**Decision: Delete sff.py.** SFF was the weakest link in the chain. fuse_classical is the default.

**`cr_sam.py`:**
Refactor to remove `mineral_features` dependency. The `VnirSwirGating` class and mineral group logic are stripped. CR-SAM becomes a simple pipeline: continuum removal → SAM. Keep `linear_continuum_remove` and rewrite `classify_cube_cr_sam` without group gating.

**`service.py`:**
- Remove `import cr_sam`, `import sff` lines
- Remove ACE/veg mask error blocks (already raised as errors)
- Strip `_IMPLEMENTED_CLASSIFIERS` of `sff` and `continuum_removal`
- Keep `cr_sam` in implemented classifiers (now generic)
- Rename `OreMapper` → `SpectralMatcher` (deferred to Phase 2)

**`schemas.py`:**
- Remove `use_ace`, `vegetation_mask`, `ndvi_threshold`, `topographic_correct`, `dem_type`, `solar_azimuth`, `solar_elevation` fields
- Rename `minerals` → `classes` (deferred to Phase 2)
- Remove DEFAULT_DEMO_MINERALS, DEFAULT_REAL_MINERALS
- Rename `MineralStatistics` → `ClassStatistics` (deferred to Phase 2)

**`cli.py`:**
- Remove evaluate, list-scenes, download-scene, fetch-library subcommands
- Remove imports of benchmark, public_scenes, relab_fetcher
- Update predict command to use new naming (Phase 2)
- Add `--library` as required flag (no more demo minerals)

**`api.py`:**
- Remove `/v1/benchmarks/run` endpoint
- Remove `/v1/predict/bbox` endpoint + `_run_bbox_pipeline` function
- Remove `/v1/maps/{uuid}`, `/v1/maps/{uuid}/tiles/*`, `/v1/jobs/{job_id}` endpoints
- Remove EMIT/benchmark imports
- Remove `store` import (was for bbox jobs)
- Keep: `/health`, `/v1/predict`, `/v1/qc/raster`, `/v1/minerals` (rename to `/v1/classes`)
- Simplify `_parse_options` — strip ACE/veg/emit fields
- Strip static file serving (old vanilla JS frontend)

**`__init__.py`:**
- Update exports to match new names (Phase 2)

### 1.5 Delete old static frontend

| Path | Reason |
|------|--------|
| `src/open_ore_mapper/static/` | Legacy vanilla JS frontend, replaced by React SPA |

---

## Phase 2: Rename Everything — Domain-Agnostic Naming

### 2.1 Package rename

| Old | New | Files |
|-----|-----|-------|
| `open-ore-mapper` (package name) | `spectral` | pyproject.toml |
| `open_ore_mapper` (Python package) | `spectral_matching` | All `.py` files, all `from open_ore_mapper` imports |
| `open-ore-mapper` (CLI entry) | `spectral-match` | pyproject.toml scripts |
| `open-ore-mapper` (Docker image) | `spectral` | Dockerfile, docker-compose.yml |

### 2.2 Class/type renames

| Old | New |
|-----|-----|
| `OreMapper` | `SpectralMatcher` |
| `MapperOptions` | `MatchOptions` |
| `MapperResult` | `MatchResult` |
| `MineralStatistics` | `ClassStatistics` |
| `minerals` (field) | `classes` |
| `SpectralLibrary` | unchanged (it was already generic) |
| `UNKNOWN_CLASS` | unchanged |
| `class_map_png_data_url(minerals=)` | rename param to `classes=` |
| `mineral_statistics` | `class_statistics` |
| `mineral_color` (frontend) | `class_color` |

### 2.3 API endpoint renames

| Old | New |
|-----|-----|
| `POST /v1/predict` | `POST /v1/match` |
| `POST /v1/qc/raster` | unchanged |
| `GET /v1/minerals` | `GET /v1/classes` |
| `GET /health` | unchanged |

### 2.4 File renames

| Old | New |
|-----|-----|
| `service.py` | `engine.py` |
| `schemas.py` | unchanged (just internal renames) |
| `spectral_library.py` | `library.py` |

---

## Phase 3: New Features

### 3.1 GeoTIFF Export

New module: `src/spectral_matching/export.py`

```
export_geotiff(path, class_map, confidence_map, source_cube_path, classes):
    Read CRS + geotransform from source TIFF
    Write output TIFF with:
      Band 1: class_map (uint8)
      Band 2: confidence (float32)
      Color table from CLASS_COLORS
```

Dependencies: `tifffile` (already used), `rasterio` (new optional dep). Use tifffile for reading geotags, write with tifffile's geotiff capabilities. If source isn't a TIFF, skip CRS and write plain tiff.

### 3.2 Library as First-Class Upload

Update `POST /v1/match` to accept an optional second file:
- `file` (UploadFile): the cube
- `library_file` (UploadFile, optional): the library CSV

If `library_file` is provided:
1. Parse CSV → extract class names
2. Pass to `SpectralLibrary.load_csv()`
3. Override any `classes` / `spectral_library` options

If not provided:
- Require `classes` list in options
- Use bundled starter library (see 3.3)

Update `MatchOptions`:
- `spectral_library` → accepts path OR None (for uploaded library)
- `classes` → required when no library_file provided
- `classifier` → defaults to "fuse_classical"

### 3.3 Starter Libraries

New directory: `data/starter_libraries/`

| File | Source | Classes |
|------|--------|---------|
| `usgs_minerals.csv` | USGS Spectral Library v7 | 15 common minerals |
| `ecostress_veg.csv` | ECOSTRESS spectral library | 10 vegetation types |
| `urban_materials.csv` | ASTER spectral library | 8 urban surfaces |

Format: `class,wavelength,reflectance` (same CSV format already supported)

### 3.4 Auto-Algorithm Selection

New static method in `SpectralMatcher`:

```python
@staticmethod
def _auto_classifier(n_classes: int, n_bands: int) -> str:
    if n_classes >= 50:
        return "mnf_mtmf"  # sparse + sub-pixel
    if n_bands > 100:
        return "fuse_classical"  # ensemble
    return "sam"  # simple angular matching
```

Wire into `predict_cube` when `classifier="auto"`.

---

## Phase 4: Frontend Rebrand

### 4.1 Delete/minimize

| Component | Action |
|-----------|--------|
| `components/input/AdvancedOptions.tsx` | Remove ACE, veg mask, excluded bands controls |
| `components/input/MineralSelector.tsx` | Rename → ClassSelector, fetch from `/v1/classes` |
| `pages/Home.tsx` | Remove benchmark/scorecard flow entirely. Remove EMIT default sensor. Remove walkthrough references to EMIT/minerals. |
| `pages/MapView.tsx` | Remove scorecard viewer/score tab. Simplify to: Class Map + Statistics + QC + Export tabs. |
| `components/map/SettingsPanel.tsx` | Remove benchmark button, ACE/veg toggles. Add "Upload Library" button. |
| `api/client.ts` | Remove Scorecard types. Rename endpoint URLs. |

### 4.2 Add

| Component | Purpose |
|-----------|---------|
| `components/input/LibraryUpload.tsx` | Drag-drop zone for library CSV. |
| `api/client.ts` → `uploadAndMatch()` | New function: upload cube + optional library CSV → map result. |

### 4.3 Rename

| Old | New |
|-----|-----|
| "Open Ore Mapper" | "Spectral" |
| "Map Minerals" button | "Match Spectra" button |
| "minerals" across all components | "classes" |
| "mineral map" | "class map" |
| `/api/v1/predict` | `/api/v1/match` |
| `/api/v1/minerals` | `/api/v1/classes` |
| `MINERAL_COLORS` (lib/colors.ts) | `CLASS_COLORS` |

### 4.4 Clean up

| Item | Action |
|------|--------|
| `hooks/useWalkthrough.tsx` | Rewrite walkthrough steps (remove EMIT, benchmark, mineral references) |
| `lib/colors.ts` | Keep the palette, rename exports |
| `styles/globals.css` | No changes needed (dark theme stays) |
| `components/map/GlobeMap.tsx` | Unchanged |
| `components/map/MapLegend.tsx` | `minerals` → `classes` prop |
| `components/map/LayerPanel.tsx` | `minerals` → `classes` prop |
| `components/sidebar/StatisticsTab.tsx` | `mineralColor` → `classColor` |
| `components/sidebar/QCTab.tsx` | Unchanged |
| `components/sidebar/ExportTab.tsx` | Update download URLs/filenames |
| `App.tsx` | Update title |

---

## Phase 5: Tests — Adapt + Build + Adversarial Review

### 5.1 Adapt surviving tests

17 test files survived module deletion. Each needs:
- Import path updates (`open_ore_mapper` → `spectral_matching`)
- Class name updates (`OreMapper` → `SpectralMatcher`, `MapperOptions` → `MatchOptions`)
- Field name updates (`minerals` → `classes`)
- Remove references to deleted classifiers (sff, continuum_removal)

**Subagent task:** Adapt all 17 surviving test files to new naming.

### 5.2 Write new tests

| Test File | Tests What |
|-----------|-----------|
| `test_export.py` | GeoTIFF export: writes valid TIFF, preserves bands, handles missing CRS, handles non-TIFF source |
| `test_library_upload.py` | Library CSV upload: valid CSV, missing columns, empty CSV, class name extraction, resampling |
| `test_auto_classifier.py` | Auto-algorithm: large library → mnf_mtmf, many bands → fuse_classical, small → sam |
| `test_cr_sam_generic.py` | CR-SAM without mineral features: generic continuum removal + SAM, no group gating, works on synthetic non-mineral spectra |

### 5.3 API tests (replacing deleted test_api.py)

New `test_api_v2.py`:
- `test_health`
- `test_get_classes`
- `test_match_upload_cube_only`
- `test_match_upload_cube_and_library`
- `test_qc_raster`
- `test_match_validation_errors`

### 5.4 Adversarial Test Review (CRITICAL)

After ALL tests are written, dispatch an adversarial subagent for EACH test file with the prompt:

> "You are an adversarial code reviewer. This test file should catch ALL edge cases and fail loudly on bugs. Review [test_file]. Find every untested edge case, every silent pass, every weak assertion. Be ruthless. Return a list of concrete improvements needed."

For each test file:
1. Write the test
2. Dispatch adversarial subagent review
3. Fix all issues found
4. Re-run adversarial subagent review
5. Approve only when review returns zero issues

**This must be done for every test file — new and adapted.**

---

## Phase 6: Docs + CI + Final Polish

### 6.1 Rewrite README

Title: "Spectral — Universal Hyperspectral Classification"
- What: spectral matching engine, domain-agnostic
- How: `spectral-match my-cube.tif --library my-classes.csv --output out/`
- Library format: `class,wavelength,reflectance`
- Classifiers: sam, mtmf, mnf_sam, mnf_mtmf, cr_sam, fuse_classical (default)
- Starter libraries included
- GeoTIFF export
- Docker one-liner
- No benchmarks, no Cuprite, no Tetracorder, no ore/mineral framing

### 6.2 Update pyproject.toml

- name: `spectral`
- description: "Universal spectral matching engine for hyperspectral classification"
- scripts: `spectral-match = "spectral_matching.cli:main"`
- Drop `[project.optional-dependencies].emit` and `.ml`

### 6.3 Update Docker

- Image name: `spectral`
- Remove EMIT install (`.[api,emit]` → `.[api]`)
- Update WORKDIR/Copy paths

### 6.4 Update docker-compose

- service name: `spectral`
- image: `ghcr.io/${GITHUB_REPOSITORY:-spectral}/backend:${IMAGE_TAG:-latest}`

### 6.5 Update Makefile

- Remove `test-emit`, `test-e2e`, `test-eval`, `demo-fixture`, `demo-cuprite`
- `test` command updates (dropped test ignores)
- `check-all` updates

### 6.6 Update CI (GitHub Actions)

- Remove EMIT-specific test step
- Update test command
- Update build step naming

### 6.7 Delete old docs

| Path | Action |
|------|--------|
| `docs/BEST_NUMBERS.md` | Delete |
| `docs/research_scrapes/` | Delete |
| `docs/assets/` (Cuprite images) | Delete |
| `PLAN.md` | Delete (old infra plan) |
| `TECH_PLAN.md` | Delete (old tech plan) |
| `ROADMAP.md` | Rewrite (new roadmap) |
| `PROVENANCE.md` | Keep (license attribution) |

---

## Phase 7: Build + Verify End-to-End

### 7.1 Backend

```
make install
make lint       # ruff check .
make typecheck  # mypy src/spectral_matching
make test       # pytest -v
```

All must pass with zero errors.

### 7.2 Frontend

```
cd frontend
npm run lint    # oxlint
npm run build   # vite build
```

Zero errors.

### 7.3 Docker

```
docker compose build
docker compose up -d
curl http://localhost:8000/health
curl http://localhost:8000/v1/classes
# Upload test cube + library → verify match result
docker compose down
```

### 7.4 CLI end-to-end

```
spectral-match examples/salinasA_corrected.mat \
  --library examples/library.csv \
  --classes "hematite,goethite,kaolinite" \
  --output-dir /tmp/spectral-test
# Verify: class_map.png, confidence.png, result.json exist
```

---

## Subagent Dispatch Map

Each task below runs as an independent subagent. Tasks with `(parallel)` can run simultaneously.

### Batch A: Delete Phase (parallel)
1. Delete 12 source modules
2. Delete 14 test files
3. Delete data dirs (benchmarks/, docs/assets/, docs/research_scrapes/, outputs/, static/)

### Batch B: Refactor surviving source (parallel)
4. Refactor cr_sam.py (strip mineral features dependency)
5. Strip service.py (ACE/veg/sff/continuum_removal refs)
6. Strip schemas.py (ACE/veg/emit fields)
7. Strip cli.py (remove deleted subcommands)
8. Strip api.py (remove deleted endpoints)
9. Delete sff.py

### Batch C: Rename (sequential — renames cascade)
10. Rename Python package: `open_ore_mapper` → `spectral_matching` (every .py file)
11. Rename classes/types: `OreMapper` → `SpectralMatcher`, etc. (every .py file)
12. Rename CLI: `open-ore-mapper` → `spectral-match`
13. Rename API endpoints
14. Rename files: service.py → engine.py, spectral_library.py → library.py
15. Rename frontend

### Batch D: New features (parallel)
16. Build GeoTIFF export module
17. Build library upload endpoint
18. Build starter libraries
19. Build auto-algorithm selection

### Batch E: Frontend rebuild (parallel)
20. Delete scorecard/benchmark/emit/mineral components
21. Rename all frontend text/imports
22. Build library upload component

### Batch F: Tests (parallel batch, then sequential adversarial)
23. Adapt 17 surviving tests
24. Write test_export.py
25. Write test_library_upload.py
26. Write test_auto_classifier.py
27. Write test_cr_sam_generic.py
28. Write test_api_v2.py

### Batch G: Adversarial review (sequential per file)
29-46. For each of 18 test files (17 adapted + 5 new - 4 overlap = 18): adversarial review → fix → re-review

### Batch H: Docs + CI (parallel)
47. Rewrite README
48. Update pyproject.toml
49. Update Docker/Makefile/CI
50. Delete old docs

### Batch I: Final verification
51. Full backend suite (lint + typecheck + test)
52. Frontend build
53. Docker end-to-end
54. CLI end-to-end
