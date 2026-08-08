# Classic Hyperspectral Scenes

Well-known public hyperspectral scenes for testing the spectral matching engine.

## Files

| File | Size | Bands | Shape | Sensor |
|------|------|-------|-------|--------|
| `PaviaU.mat` | 34.8 MB | 103 | 610×340×103 | ROSIS (Pavia University) |
| `PaviaU_wavelengths.json` | 0.8 KB | 103 | – | ROSIS 430–860 nm |

## Provenance

- **Pavia University** — ROSIS (Reflective Optics System Imaging Spectrometer) sensor, 103 bands, 610×340 pixels. Classic urban/remote-sensing benchmark scene.
- **Source:** Basque University (EHU) "Hyperspectral Remote Sensing Scenes" mirror, retrieved via Internet Archive Wayback Machine snapshot of the exact EHU file URL (the live EHU server returns HTTP 403 to non-browser clients).
  - URL: `https://www.ehu.eus/ccwintco/uploads/e/ee/PaviaU.mat` (via Wayback)
  - Byte-exact archived copy; SHA1 `6a69e109508b89ec9098dd2b2188f3483d49bafc`
- **MATLAB structure:** variable `paviaU`, shape (610, 340, 103), uint16 — bands last (HWC)
- **Wavelengths:** not embedded in the .mat; supplied separately in `PaviaU_wavelengths.json` (103 bands, 430–860 nm, ~4.2 nm spacing, ROSIS documented grid)
- **Download date:** 2026-08-08
- **License:** public for research use; cite the original ROSIS/Pavia University dataset owners and the EHU mirror when publishing.

## Notes

- Other classic scenes (Pavia Centre ~129MB, Botswana ~79MB, KSC ~57MB) exceed the 40MB demo-size cap on the EHU mirror and were not included.
- Houston 2013 (CASI-1500, 144 bands) source at Purdue returns 404; GRSS DFC archive may host it.
