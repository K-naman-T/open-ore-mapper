# Open Ore Mapper Product Design

## Product Goal

Open Ore Mapper is an open, reproducible tool for mapping exposed surface mineral signatures from hyperspectral raster cubes. It is not an ore-reserve predictor and must not imply that it can detect buried deposits without suitable spectral evidence.

## Target Users

- Exploration geologists doing first-pass spectral screening.
- Remote-sensing analysts validating mineral signatures and alteration proxies.
- Students and researchers who need an inspectable SAM/NNLS baseline.
- Developers who need a clean open-source mineral-mapping package and API.

## Product Positioning

The product maps spectral similarity and abundance-like estimates for exposed or near-surface materials using public or user-supplied hyperspectral data. Results are decision support outputs, not confirmed mineral-resource claims. Every output must include wavelength, library, band-quality, threshold, and provenance context.

## MVP Product Shape

The first complete product is a Python engine plus optional API and web UI. The Python package remains authoritative and fully usable without a browser. The API and future UI wrap the same service behavior.

The MVP supports:

- User-uploaded `.tif`, `.tiff`, `.h5`, and `.hdf5` raster cubes.
- Sensor preset wavelengths, manual wavelengths, and HDF5-embedded `/wavelengths` arrays.
- SAM mineral matching and NNLS abundance-like estimation.
- Unknown-class handling through confidence and angle thresholds.
- Data-quality reporting before and during prediction.
- Band exclusion from automatic QC or explicit user options.
- Provenance and warnings in every prediction response.
- CLI and API access to raster QC.

## Non-Goals For MVP

- CNN training or retraining.
- Claims that the product discovers ore deposits.
- Automatic global satellite catalog processing.
- Bundling large external datasets inside git.
- Private datasets, private model weights, private old app code, or proprietary spectra.

## Data Strategy

The product must treat external data as user-controlled or downloaded into local cache, not as source-controlled assets. The bundled demo spectra remain synthetic and clearly labeled as non-authoritative.

The Nature/Zenodo SWIR mineral dataset may be integrated later as a downloader-backed demo/reference source. It must be treated as laboratory sample hyperspectral imagery, not georeferenced satellite imagery. Each downloaded sample must be verified against Zenodo metadata, inspected for HDF5 structure, and passed through band-quality QC before it is listed as curated.

## Corrupted Band And NaN Handling

Coworker concerns about corrupted middle bands are handled as a first-class product requirement. The system must never assume a raster is clean just because it opens successfully.

Raster QC must compute:

- Cube shape after orientation to height, width, bands.
- Wavelength count and wavelength range.
- Per-band finite fraction.
- Per-band finite mean and standard deviation.
- Per-band rejection reasons, including user exclusion and low finite coverage.
- Overall finite valid-pixel fraction after usable-band selection.
- Pass, warn, or fail status.
- Human-readable warnings suitable for CLI/API/UI display.

Prediction must only use QC-usable bands. If all bands, or too many bands, are unusable, prediction must fail with a clear error instead of producing misleading maps.

## HDF5 Requirements

The loader must support common HDF5 dataset names including `hdr`, `cube`, `data`, `image`, `hsi`, and `HSI`. If an HDF5 file contains `/wavelengths`, the loader must use it when manual wavelengths are not supplied. If a cube axis length matches the embedded wavelength count, the loader must orient that axis to the band dimension.

This is required for public SWIR datasets where the array can be stored as `bands, y, x` rather than `y, x, bands`.

## Processing Flow

Prediction flow:

1. Load cube bytes from file or API upload.
2. Orient cube to height, width, bands.
3. Resolve wavelengths from manual input, HDF5 metadata, or sensor preset.
4. Run raster QC.
5. Remove excluded or low-quality bands.
6. Resample the selected spectral library to the retained wavelength grid.
7. Build valid-pixel mask over retained bands.
8. Run SAM and NNLS in tiles.
9. Fuse SAM strength and NNLS abundance estimates.
10. Apply confidence and spectral-angle thresholds.
11. Return class map, confidence map, top-abundance map, statistics, warnings, and QC/provenance metadata.

## API Requirements

The API must expose:

- `GET /health`
- `GET /v1/minerals`
- `POST /v1/qc/raster`
- `POST /v1/predict`

The API must continue rejecting server-side spectral-library paths. Future library upload support should use multipart uploads, not arbitrary server paths.

## CLI Requirements

The CLI must expose:

- `open-ore-mapper qc-raster INPUT [--sensor SENSOR] [--wavelengths FILE] [--exclude-bands CSV] [--min-band-valid-fraction FLOAT] [--output FILE]`
- `open-ore-mapper predict INPUT --output-dir DIR [...]`

Prediction outputs must include `result.json`, image PNGs, and `quality_report.json`.

## Trust And Provenance Requirements

Every result must include enough context for a reviewer to understand what happened:

- Algorithm identifier.
- Sensor or wavelength source.
- Wavelengths used after QC filtering.
- Original band count.
- Retained and excluded band indices.
- QC status and warnings.
- Mineral names and library source.
- Threshold settings.

The product should prefer explicit warnings over silent best-effort behavior.

## First Implementation Slice

The first build slice is the QC-first engine/API/CLI foundation. It does not build the web UI yet. The slice adds embedded HDF5 wavelength handling, robust cube orientation, raster QC, band masking, API/CLI QC surfaces, and test coverage.

## Acceptance Criteria

- HDF5 cubes with `/hdr` and `/wavelengths` can be loaded and oriented correctly.
- A cube shaped `bands, y, x` is converted to `y, x, bands` when the band axis matches wavelength count.
- QC identifies low-validity bands and returns explicit warnings.
- Prediction excludes failed bands before SAM/NNLS.
- Prediction fails clearly when fewer than two usable bands remain.
- CLI can write a standalone raster QC report.
- API can return a raster QC report.
- Existing tests still pass.
- New tests cover HDF5 embedded wavelengths, QC reports, CLI QC, API QC, and prediction band filtering.
