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

## Starter libraries
- `usgs_minerals` — 12 common minerals (450-2500nm)
- `ecostress_veg` — 8 vegetation types
- `urban_materials` — 6 urban surface materials

## API
| Endpoint | Purpose |
|----------|---------|
| `POST /v1/match` | Upload cube (+ optional library CSV) → classification |
| `POST /v1/qc/raster` | Raster quality analysis |
| `GET /v1/classes` | List available classes |
| `GET /health` | Health check |

## License
Apache 2.0
