# Roadmap

## v0.2 — Wire What's Built

- [ ] `classifier` option actually dispatches: `sam` → SAM+NNLS (current default), `continuum_removal` → hull-quotient + feature matching, `sff` → SFF per-pixel
- [ ] `use_ace=True` produces per-mineral ACE score layers alongside class map
- [ ] `vegetation_mask=True` excludes NDVI > threshold pixels before classification
- [ ] `unmixing=sunsal` auto-selects SUnSAL for libraries >50 minerals

## v0.3 — EMIT Pipeline Hardening

- [ ] Move bbox jobs to a separate worker process (worker + Redis services exist behind `--profile production` in docker-compose)
- [ ] Full-scene QC (not just first tile)
- [ ] Expose WGS84 georeferencing from GLT metadata
- [ ] Streaming tile processing (bounded memory for large scenes)
- [ ] Progress reporting via WebSocket or SSE

## v0.4 — Authoritative Spectral Libraries

- [ ] Bundle USGS splib07a mineral subset (public domain, Apache-2.0 compatible)
- [ ] Bundle select RELAB spectra (publicly downloadable; redistribution verification pending)
- [ ] First-run download script for ECOSTRESS spectra (JPL, fetch-at-runtime only)
- [ ] Remove demo synthetic spectra as default fallback; require explicit `--library` or bundled authoritative library

## v0.5 — Production Readiness

- [ ] GeoTIFF export with correct CRS/geotransform
- [ ] Exported abundance maps (single-band GeoTIFF per mineral)
- [ ] Band-to-mineral coverage validation with clear user-facing warnings
- [ ] SFF vectorized (no per-pixel Python loop)
- [ ] Release to PyPI

## Backlog

- Atmospheric correction (6S / MODTRAN look-alike via GEISA)
- MRDS / USMIN deposit overlay in frontend
- Spectral feature extraction reports (position, depth, FWHM per pixel)
- OSSL soil spectral library integration
- EnMAP / PRISMA / AVIRIS-NG sensor presets
- PyPI package with pre-built wheel
