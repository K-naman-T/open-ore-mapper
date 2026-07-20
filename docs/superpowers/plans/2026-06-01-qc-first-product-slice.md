# QC-First Product Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first production-grade Open Ore Mapper slice: robust HDF5 loading, raster quality control, band masking, and QC access through CLI/API.

**Architecture:** Keep the Python package as the authoritative engine. Add a focused QC module and small schema extensions, then route CLI/API calls through the same `OreMapper` service so the behavior is identical across interfaces.

**Tech Stack:** Python 3.10+, NumPy, h5py, tifffile, FastAPI, pytest, ruff, mypy.

**Repository Constraint:** This repo currently has no commits. Do not create commits during implementation unless the user explicitly authorizes commits.

---

## File Structure

- Create `src/open_ore_mapper/qc.py` for raster QC dataclasses and analysis functions.
- Modify `src/open_ore_mapper/preprocessing.py` to support band-count-aware cube orientation and band masking helpers.
- Modify `src/open_ore_mapper/schemas.py` to add QC/provenance options and result fields.
- Modify `src/open_ore_mapper/service.py` to load HDF5 embedded wavelengths, run QC, mask bands, and expose QC-only analysis.
- Modify `src/open_ore_mapper/cli.py` to add `qc-raster` and prediction QC options/output.
- Modify `src/open_ore_mapper/api.py` to add `POST /v1/qc/raster` and parse QC options.
- Add `tests/test_qc.py` for QC behavior.
- Update existing service, preprocessing, CLI, and API tests.

---

### Task 1: HDF5 Metadata Loading And Cube Orientation

**Files:**
- Modify: `src/open_ore_mapper/preprocessing.py`
- Modify: `src/open_ore_mapper/service.py`
- Modify: `tests/test_preprocessing.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write failing orientation tests**

Add tests that require `ensure_hwc(cube, band_count=256)` to convert `(256, 111, 170)` into `(111, 170, 256)` while preserving an already-HWC `(111, 170, 256)` cube.

- [ ] **Step 2: Run orientation tests and verify RED**

Run `pytest tests/test_preprocessing.py -v`. Expected: tests fail because `ensure_hwc` does not accept `band_count`.

- [ ] **Step 3: Implement band-count-aware `ensure_hwc`**

Update `ensure_hwc` to accept `band_count: int | None = None`. If `band_count` is provided and exactly one axis matches it, move that axis to the last dimension. If the last axis already matches, leave it unchanged. Preserve the existing heuristic when no band count is available.

- [ ] **Step 4: Add HDF5 embedded wavelength test**

Add a service test that creates an in-memory or temp HDF5 file with `/hdr` shaped `(3, 4, 5)` and `/wavelengths` length `3`, then verifies prediction resolves `sensor == "embedded_hdf5"` and returns three wavelengths after orientation.

- [ ] **Step 5: Implement scene loading with embedded wavelengths**

Introduce an internal scene-loading result in `service.py` that returns `cube` and `embedded_wavelengths`. HDF5 loading must prefer datasets `hdr`, `cube`, `data`, `image`, `hsi`, `HSI`, and use `/wavelengths` when present to orient the cube.

- [ ] **Step 6: Verify Task 1**

Run `pytest tests/test_preprocessing.py tests/test_service.py -v`. Expected: all selected tests pass.

---

### Task 2: Raster QC And Band Masking

**Files:**
- Create: `src/open_ore_mapper/qc.py`
- Modify: `src/open_ore_mapper/schemas.py`
- Modify: `src/open_ore_mapper/preprocessing.py`
- Modify: `src/open_ore_mapper/service.py`
- Add: `tests/test_qc.py`
- Modify: `tests/test_service.py`

- [ ] **Step 1: Write failing QC tests**

Create tests that build a small cube with one band mostly NaN and assert QC reports that band as excluded with reason `low_finite_fraction`.

- [ ] **Step 2: Run QC tests and verify RED**

Run `pytest tests/test_qc.py -v`. Expected: import or function failure because `open_ore_mapper.qc` does not exist.

- [ ] **Step 3: Implement `qc.py`**

Add dataclasses `BandQuality`, `RasterQualityReport`, and function `analyze_raster_quality(cube, wavelengths, excluded_band_indices=None, min_band_valid_fraction=0.5)`. Report status `pass`, `warn`, or `fail`, excluded band indices, retained band indices, valid pixel fraction over retained bands, and warnings.

- [ ] **Step 4: Add band-mask helper**

Add `select_bands(cube, wavelengths, retained_indices)` to `preprocessing.py`, returning the filtered cube and filtered wavelength list.

- [ ] **Step 5: Extend schemas**

Add `excluded_band_indices`, `min_band_valid_fraction`, and `quality_report` support. Keep defaults backward compatible.

- [ ] **Step 6: Integrate QC into prediction**

Run QC before library resampling. Filter cube and wavelengths to retained bands. Fail with `ValueError("At least two usable spectral bands are required after QC")` when fewer than two retained bands remain. Include QC warnings in `MapperResult.warnings`.

- [ ] **Step 7: Verify Task 2**

Run `pytest tests/test_qc.py tests/test_service.py tests/test_preprocessing.py -v`. Expected: all selected tests pass.

---

### Task 3: CLI And API QC Surfaces

**Files:**
- Modify: `src/open_ore_mapper/cli.py`
- Modify: `src/open_ore_mapper/api.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_api.py`
- Modify: `README.md`

- [ ] **Step 1: Write failing CLI/API tests**

Add a CLI test for `open-ore-mapper qc-raster` that writes a JSON report. Add an API test for `POST /v1/qc/raster` returning status and band count.

- [ ] **Step 2: Run CLI/API tests and verify RED**

Run `pytest tests/test_cli.py tests/test_api.py -v`. Expected: route/subcommand missing failures.

- [ ] **Step 3: Implement CLI `qc-raster`**

Add parser options `--sensor`, `--wavelengths`, `--exclude-bands`, `--min-band-valid-fraction`, and `--output`. Print JSON to stdout if no output is supplied. Prediction should accept the same QC options and write `quality_report.json` in the output directory.

- [ ] **Step 4: Implement API `/v1/qc/raster`**

Add multipart route accepting `file` and JSON `options`. Reuse the same option parsing as prediction. Return `mapper.to_quality_response(report)`.

- [ ] **Step 5: Update README**

Document QC-first behavior, HDF5 `/wavelengths`, `qc-raster`, prediction QC options, and the warning about spectral similarity vs confirmed ore deposits.

- [ ] **Step 6: Verify Task 3**

Run `pytest tests/test_cli.py tests/test_api.py -v`. Expected: all selected tests pass.

---

### Task 4: Full Verification And Self-Review

**Files:**
- Review all modified files.

- [ ] **Step 1: Run lint**

Run `. .venv/bin/activate && ruff check .`. Expected: `All checks passed!`.

- [ ] **Step 2: Run type check**

Run `. .venv/bin/activate && mypy src/open_ore_mapper`. Expected: `Success: no issues found`.

- [ ] **Step 3: Run test suite**

Run `. .venv/bin/activate && pytest -v`. Expected: all tests pass.

- [ ] **Step 4: Inspect git diff**

Run `git diff -- src tests README.md docs`. Confirm changes match this plan and no private data, model weights, or unrelated files were added.

- [ ] **Step 5: Do not commit**

Leave changes uncommitted unless the user explicitly authorizes a commit.
