# Roadmap

**Canonical plan:** [README.md](README.md)  
**Numbers + images:** [docs/BEST_NUMBERS.md](docs/BEST_NUMBERS.md) · [README.md](README.md)  
**Claims:** [docs/research_scrapes/ADVERSARIAL_CONSENSUS.md](docs/research_scrapes/ADVERSARIAL_CONSENSUS.md)

Phases: **0 scoreboard (done base) → 1 library / classical integrity → 2 UI honesty → 3 EMIT region → 4 polish.**  
Do not skip honesty of Phase 0 when adding features.

## Phase 0 — Benchmark scoreboard (base delivered)

- [x] Cuprite package `benchmarks/cuprite_real/` + Tetracorder reference  
- [x] Classical `fuse_classical` validation script (default product demo path)  
- [x] Side-by-side panel + metrics (`outputs/cuprite-real-eval/`, `docs/assets/cuprite-*.png`)  
- [x] Map-to-map agreement framing (not “82% product accuracy”)  
- [x] Spatial multi-seed Track B classical bar (~0.66 fuse)  
- [ ] Independent library Track A multi-seed (next integrity win)  
- [ ] Open-set / unknown rate on scoreboard (reject over-paint)

## v0.2 — Wire product path cleanly

- [x] `fuse_classical` / MTMF / MNF / CR dispatch in `OreMapper`  
- [ ] Schema + CLI + API default classifier aligned with product (`fuse_classical` or documented library preset)  
- [ ] Hide or hard-disable unwired ACE / vegetation / SUnSAL in UI  
- [ ] Curated USGS mineral pack for unlabeled runs (no pure-GT endmembers required)

## v0.3 — EMIT Path B (after Path A is boring)

- [ ] Progress reporting (real, not fake 0–90%)  
- [ ] Full-scene QC + WGS84 georef from GLT  
- [ ] Worker isolation for large granules  
- [ ] One documented region→map demo with Earthdata

## v0.4 — Authoritative libraries

- [ ] Bundle USGS splib07a mineral subset  
- [ ] Runtime ECOSTRESS / RELAB fetch documented and tested  
- [ ] Remove silent demo-library fallback for “real” sensors

## v0.5 — Production export

- [ ] GeoTIFF class / abundance export with CRS  
- [ ] PyPI release  

## Research-only (never product default)

- [x] RF / HistGB / 1D-CNN multi-seed Track C (documented as map imitation)  
- [ ] HybridSN / SpectralFormer only if they beat Track C **and** product still ships classical  
- [ ] Supervised UI mode when user paints ROIs  

## Backlog

- Atmospheric correction, deposit overlays, EnMAP/PRISMA presets, vectorized SFF  
