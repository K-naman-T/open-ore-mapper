# Satellite Hyperspectral Scenes

Real spaceborne hyperspectral granules for testing the spectral matching engine.

## Files

| File | Size | Bands | Shape | Source |
|------|------|-------|-------|--------|
| `M3T20090420T051311_V01_RFL.h5` | 7.4 MB | 256 | 84×100×256 | M3 (Moon Mineralogy Mapper), target mode |

The M3 granule embeds its wavelength grid (HDF5 `/wavelengths` + `/sensor_band_parameters/wavelengths`), so the engine reads it directly with no separate JSON file.

## Provenance

- **Product:** `M3T20090420T051311_V01_RFL` — Chandrayaan-1 Moon Mineralogy Mapper (M3), Level 2 reflectance, target mode, 2009-04-20 (orbit 07671)
- **Source:** NASA PDS volume `CH1M3_0004` — https://planetarydata.jpl.nasa.gov/img/data/m3/CH1M3_0004/DATA/20090415_20090816/200904/L2/
- **Files used:** PDS3 label `M3T20090420T051311_V01_L2.LBL`, ENVI header + raw `_RFL.IMG` (608 samples × 84 lines × 256 bands, BIL, float32, −999 ignore value)
- **Wavelengths:** 256 bands, 446.02–2991.17 nm, read from the product's ENVI header; 9 bands masked (0–8 and 255) via `good_wavelengths` / bbl
- **Crop:** central 84×100×256 patch, gzip-compressed; reflectance 0–0.21 (lunar maria), −999 sentinels replaced with NaN
- **Download date:** 2026-08-08
- **License:** NASA PDS, public domain. Cite: Green et al. (2011), "The Moon Mineralogy Mapper (M3) imaging spectrometer for lunar science", *J. Geophys. Res.*, ISRO/NASA Chandrayaan-1.

## Notes

- M3 target-mode raw has 260 channels; this L2 product drops 4 to 256 bands, so the engine's `m3` preset (260) does not auto-match. The embedded HDF5 wavelengths make that irrelevant — the engine reads the real 256-band grid directly.
- Other satellite granules (EMIT, AVIRIS, EnMAP, PRISMA, Hyperion) require NASA Earthdata Login credentials and are not anonymously downloadable; they can be added manually. See `.superpowers/sdd/PLAN_V2/task-data-satellite-report.md` for URLs.
