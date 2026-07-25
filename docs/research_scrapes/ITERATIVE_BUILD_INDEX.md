# Iterative build research index (post-push)

**Date:** 2026-07-26  
**Repo push:** `master` @ product path + docs (`c7e8d01` lineage)

## Research outputs

| Doc | Purpose |
|-----|---------|
| [`ITERATIVE_BUILD_NEXT_2026.md`](ITERATIVE_BUILD_NEXT_2026.md) | Ordered increments I1… + first PR |
| [`USGS_LIBRARY_NEXT_PACK_2026.md`](USGS_LIBRARY_NEXT_PACK_2026.md) | Curated USGS pack design / license / Track A |

## Recommended sequence

| ID | Increment | Effort | Product? |
|----|-----------|--------|----------|
| **I1** | Default + CLI expose `fuse_classical` | S | Yes — **next PR** |
| **I2** | UI honesty (hide dead toggles, agreement copy) | S | Yes |
| **I3** | Named product preset (library path documented) | S–M | Yes |
| **I4** | Open-set / unknown rate on scoreboard | M | Yes |
| **I5** | USGS curated CSV pack (splib07 public domain) | M | Yes |
| **I6** | Track A multi-seed with fixed USGS library | M | Science integrity |
| later | EMIT Path B polish | L | After I1–I5 boring |

## Explicitly not next

HybridSN / HistGB product mode · multi-seed ML horse races · full ECOSTRESS bundle · ACE/veg theater.

## Local-only data (not in git)

- `benchmarks/cuprite_real/scene.tif` (~385 MB)
- `benchmarks/cuprite_real/raw/`

Clone + run validation still requires extracting the AVIRIS package locally.
