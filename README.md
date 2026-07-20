# Open Ore Mapper

Open Ore Mapper is a local-first tool for mapping exposed surface mineral signatures from hyperspectral raster cubes using public spectral matching methods.

It is not a buried ore-body detector. It identifies spectral evidence at or near the surface when the input bands cover diagnostic wavelengths.

## What It Does

- Spectral Angle Mapper classification
- NNLS abundance-like strength layers
- Tiled raster processing
- User-provided spectral library CSV support
- CLI output as PNG previews and JSON statistics
- Optional FastAPI service

## Install

```bash
python -m pip install -e '.[dev,api]'
```

## CLI Quickstart

```bash
open-ore-mapper predict scene.tif \
  --sensor cubert_ultris_s5 \
  --minerals hematite_demo,goethite_demo \
  --output-dir outputs/scene-001
```

Outputs:

- `result.json`
- `class_map.png`
- `confidence.png`
- `top_abundance.png`

Use manual wavelengths with a JSON array:

```bash
open-ore-mapper predict scene.tif \
  --wavelengths examples/manual_wavelengths.json \
  --library examples/demo_library.csv \
  --minerals hematite_demo,goethite_demo \
  --output-dir outputs/manual-run
```

## Python API

```python
from open_ore_mapper import MapperOptions, OreMapper

mapper = OreMapper()
result = mapper.predict_file(
    "scene.tif",
    MapperOptions(
        sensor="cubert_ultris_s5",
        minerals=["hematite_demo", "goethite_demo"],
    ),
)
print(result.statistics)
```

## API Quickstart

Launch the local web app:

```bash
uvicorn open_ore_mapper.api:app --host 127.0.0.1 --port 8001
```

Then open [http://127.0.0.1:8001/](http://127.0.0.1:8001/) in your browser. The app provides a UI for uploading rasters, running QC, and running predictions, using the same API endpoints as the CLI.

Endpoints:

- `GET /health`
- `GET /v1/minerals`
- `POST /v1/predict` with multipart field `file` and optional form field `options` as JSON.
- `POST /v1/qc/raster` with multipart field `file` and optional form field `options` as JSON.

Example `options` JSON:

```json
{"minerals":["hematite_demo","goethite_demo"],"min_confidence":0.0,"sam_threshold_deg":180.0}
```

## Raster Quality Control

Open Ore Mapper performs quality control on every input raster before mineral mapping:

1. **Band-level QC:** Each band is checked for its fraction of finite (non-NaN, non-inf) pixels. Bands below `min_band_valid_fraction` (default 0.5) are excluded.
2. **User exclusions:** Bands can be explicitly excluded via `excluded_band_indices`.
3. **Valid pixel fraction:** After QC, the fraction of pixels that are finite and non-zero across all retained bands is reported.
4. **Status:** `pass` (all clear), `warn` (bands excluded or partial valid pixels), or `fail` (fewer than 2 usable bands).

### `.mat` (MATLAB) Scene Support

Open Ore Mapper can load hyperspectral cubes from `.mat` files using `scipy.io.loadmat`.
The loader selects the first non-private 3D floating-point array, or recognizes common keys
(`cube`, `data`, `hsi`, `image`, `scene`, `SalinasA_corrected`, `indian_pines_corrected`).

## Public Hyperspectral Scenes

Open Ore Mapper includes a catalog of real public airborne/satellite hyperspectral scenes
for testing and demonstration. These are provided by the Grupo de Inteligencia Computacional
at the Universidad del País Vasco (EHU).

### Caveats

- **Salinas-A** and **Indian Pines** are real airborne AVIRIS hyperspectral scenes but are
  **agricultural/vegetation/land-cover scenes**, not mineral ore scenes. They are useful for
  testing the software pipeline (loading, QC, SAM classification) with real sensor data.
- **Cuprite AVIRIS** is a mineral-relevant AVIRIS reflectance scene over Cuprite, NV, a
  well-known hydrothermal alteration mineral site. This is the best choice for mineral mapping
  demonstrations. The file is large (~100 MB) and network-dependent.
- **Demo mineral library** values bundled with this repository are synthetic. For real
  mineral mapping, you must supply a user spectral library CSV using `--library`.

### List available scenes

```bash
open-ore-mapper list-scenes
```

### Download a scene

```bash
open-ore-mapper download-scene salinas_a_corrected --output-dir data/public
```

Then run quality control or prediction with approximate AVIRIS wavelengths:

```bash
open-ore-mapper qc-raster data/public/SalinasA_corrected.mat \
  --wavelengths examples/aviris_204_wavelengths.json

open-ore-mapper predict data/public/SalinasA_corrected.mat \
  --wavelengths examples/aviris_204_wavelengths.json \
  --library examples/demo_library.csv \
  --minerals hematite_demo,goethite_demo \
  --output-dir outputs/salinas-a
```

For the Cuprite scene:

```bash
open-ore-mapper download-scene cuprite_aviris --output-dir data/public
open-ore-mapper predict data/public/Cuprite_f970619t01p02_r02_sc03.a.rfl.mat \
  --wavelengths examples/aviris_wavelengths.json \
  --library examples/demo_library.csv \
  --minerals hematite_demo,goethite_demo \
  --output-dir outputs/cuprite
```

### CLI: `qc-raster`

```bash
open-ore-mapper qc-raster scene.tif --sensor cubert_ultris_s5
```

Options:

- `--sensor`, `--wavelengths`: Wavelength source (same as `predict`).
- `--exclude-bands`: Comma-separated zero-based band indices, e.g. `0,3,10`.
- `--min-band-valid-fraction`: Minimum valid pixel fraction per band (default 0.5).
- `--output`: Write JSON to a file instead of stdout.

### Prediction QC Options

The `predict` command also accepts `--exclude-bands` and `--min-band-valid-fraction`:

```bash
open-ore-mapper predict scene.tif \
  --sensor cubert_ultris_s5 \
  --minerals hematite_demo,goethite_demo \
  --exclude-bands 0,10 \
  --output-dir outputs/scene-001
```

A `quality_report.json` is written alongside the existing outputs.

### API: `POST /v1/qc/raster`

Accepts multipart `file` and optional `options` JSON form field (same format as `/v1/predict`). Returns the quality report as JSON.

```bash
curl -X POST http://127.0.0.1:8001/v1/qc/raster \
  -F "file=@scene.tif" \
  -F 'options={"sensor":"cubert_ultris_s5"}'
```

### HDF5 `/wavelengths`

When loading `.h5` or `.hdf5` files, the mapper automatically reads embedded wavelengths from the `/wavelengths` dataset if present. This dataset is also used to orient the cube (band axis detection).

## Spectral Similarity

Open Ore Mapper identifies spectral similarity at or near the surface. A match indicates that the input spectrum is consistent with a reference mineral spectrum. It does **not** confirm the presence of a buried ore body. Always validate with field sampling, petrology, and geochemistry.

## Spectral Library CSV Format

User-provided libraries use long-form CSV:

```csv
name,wavelength,reflectance
hematite_demo,450,0.42
hematite_demo,550,0.30
goethite_demo,450,0.38
goethite_demo,550,0.44
```

Rules:

- Required columns: `name`, `wavelength`, `reflectance`.
- Wavelengths must be strictly increasing for each mineral.
- Selected minerals must share the same wavelength grid.
- Reflectance values must be finite numbers.

## Demo Spectra

The bundled `examples/demo_library.csv` values are synthetic demos for software testing. They are not authoritative mineral spectra and should not be used as field evidence without replacing them with reviewed, fit-for-purpose spectral libraries.

## IP Boundary

This repository intentionally excludes private datasets, model weights, institutional branding, and proprietary spectra. See `PROVENANCE.md`.

## License And Provenance

Open Ore Mapper is licensed under Apache-2.0. See `LICENSE` and `PROVENANCE.md`.
