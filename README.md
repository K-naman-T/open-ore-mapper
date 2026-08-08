# Spectral

**Domain-agnostic spectral matching** from hyperspectral cubes — bring your
own cube and spectral library, get a classified map.

## What it does

Upload a hyperspectral raster (.tif, .h5, .mat) and a spectral library CSV
(`class,wavelength,reflectance`) → get pixel-level classification using
classical spectral matching algorithms.

Default classifier: `fuse_classical` (MTMF + CR-SAM + MNF-SAM ensemble).

## Quickstart

### CLI
```bash
spectral-match examples/salinasA_corrected.mat \
  --library examples/library.csv \
  --classes "ClassA,ClassB,ClassC" \
  --output /tmp/result/
```

### API + UI
```bash
uvicorn spectral_matching.api:app --host 127.0.0.1 --port 8000
# http://127.0.0.1:8000/

cd frontend && npm run dev
# http://localhost:5173/
```

### Docker
```bash
docker compose up -d
curl http://localhost:8000/health
```

## Classifiers
- `auto` — auto-select based on library size (default)
- `sam` — Spectral Angle Mapper + NNLS
- `mtmf` — Mixture-Tuned Matched Filter
- `mnf_sam` — MNF-reduced SAM
- `mnf_mtmf` — MNF-reduced MTMF
- `cr_sam` — Continuum-Removed SAM
- `fuse_classical` — Ensemble: 0.7×MTMF + 0.2×CR-SAM + 0.1×MNF-SAM

## Library format
CSV with columns: `class,wavelength,reflectance`
All classes must share the same wavelength grid (strictly increasing).

## Sensor presets
The engine ships wavelength grids for well-known hyperspectral sensors. Pick a preset via `--sensor <name>` (CLI) or the `sensor` option (API) when your cube's band count matches; otherwise pass wavelengths explicitly or let auto-detection match by band count.

| Preset | Bands | Range (nm) | Grid |
|--------|-------|-----------|------|
| `aviris` | 224 | 400–2500 | ~10 nm, calibrated |
| `aviris_ng` | 425 | 376.86–2496.86 | uniform 5.0 nm |
| `hyspex_vnir` | 186 | 405.70–996.49 | uniform 3.19 nm |
| `hyspex_swir` | 288 | 952.83–2516.64 | uniform 5.45 nm |
| `casi_1500` | 288 | 380–1050 | ~2.4 nm, configurable |
| `aisafenix` | 620 | 380–2500 | dual VNIR+SWIR |
| `emit` | 285 | 381–2497.5 | non-uniform (read from product) |
| `enmap` | 244 | 418–2445 | non-uniform (92+152) |
| `prisma` | 239 | 400–2505 | non-uniform (66+173) |
| `hyperion` | 220 | 400–2500 | non-uniform |
| `hico` | 128 | 352.528–1079.984 | uniform 5.728 nm |
| `desis` | 235 | 400–1000 | per-product centers |
| `m3` | 260 | 430–3000 | non-linear |
| `cubert_ultris_s5` | 51 | 450–850 | snapshot camera |

`spectral-match sensors` lists presets with sources. Exact grids are used where verified (AVIRIS-NG, HySpex, HICO); other sensors use documented ranges. When a scene ships its own wavelength metadata (ENVI `.hdr` `wavelength = {...}`, EMIT NetCDF `sensor_band_parameters/wavelengths`), prefer that over the preset.

## Starter libraries
- `usgs_minerals` — 12 common minerals (450-2500nm)
- `ecostress_veg` — 8 vegetation types
- `urban_materials` — 6 urban surface materials
- `usgs_minerals_real` — 46 real lab minerals (USGS splib07a)
- `ecostress_veg_real` — 14 real vegetation spectra (ECOSTRESS)
- `relab_minerals` — 13 real lab spectra (RELAB)

## API
| Endpoint | Purpose |
|----------|---------|
| `POST /v1/match` | Upload cube (+ optional library CSV) → classification |
| `POST /v1/qc/raster` | Raster quality analysis |
| `GET /health` | Health check |

## License
Apache 2.0
