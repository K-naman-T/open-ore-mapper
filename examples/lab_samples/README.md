# Lab / material hyperspectral sample scenes

Lab-measured hyperspectral images of physical samples, converted from ENVI
format to TIFF + `wavelengths.json` for the spectral matching engine.

## nwa480_2cm_patch.tif

- **Sample:** NWA480 meteorite (northwest Africa 480), ~2 cm spatial resolution.
- **Imager:** HySpex SWIR camera, imaged at 2 cm distance.
- **Source:** Zenodo record
  [4459182](https://zenodo.org/records/4459182) — "HySpex datasets of NWA480",
  author Lu Pan, published 2021-01-23.
- **Original file:** `nwa480_2cm_georef_cropped.img` + `.hdr`
  (214,456,320 bytes, ENVI BIP, float32). Downloaded via the Zenodo Records API
  (files[].links.self).
- **Processing:** Full scene is 358 samples x 520 lines x 288 bands; central
  200x200 pixel patch cropped to keep file under 50 MB
  (`examples/lab_samples/nwa480_2cm_patch.tif`, 46,115,694 bytes). BIP
  interleave reshaped to HWC before writing.
- **Bands:** 288, HySpex SWIR, 953-2516 nm (see `wavelengths.json`).
- **Wavelengths source:** the `wavelength = { ... }` array parsed from the
  ENVI `.hdr` (the sensor's real center-wavelength grid).
- **License:** CC-BY-4.0.

## apple_skin_flesh.tif

- **Sample:** Gala apple (skin/flesh), "Sample Hyperspectral Apple Skin and
  Flesh Dataset (SFTCI study)".
- **Imager:** lab hyperspectral camera, 400-1000 nm range.
- **Source:** Zenodo record
  [20719557](https://zenodo.org/records/20719557), published 2026-06-16.
- **Original file:** `square` (ENVI data, no extension) + `square.hdr`
  (1,966,080 bytes, ENVI BSQ, float32). Downloaded via the Zenodo Records API.
- **Processing:** Full scene is 64 x 64 x 120 bands; BSQ interleave reshaped
  to HWC. No cropping needed.
- **Bands:** 120, 400-1000 nm (5 nm steps, see `wavelengths.json`).
- **Wavelengths source:** the `wavelength = { ... }` array parsed from the
  ENVI `.hdr`.
- **License:** CC-BY-4.0.

## Files

| Scene | Bands | Shape | Wavelengths |
|-------|-------|-------|-------------|
| `nwa480_2cm_patch.tif` | 288 | 200x200x288 | `nwa480_2cm_patch_wavelengths.json` |
| `apple_skin_flesh.tif` | 120 | 64x64x120 | `apple_skin_flesh_wavelengths.json` |

`wavelengths.json` files contain a JSON array of floats (center wavelength in
nm per band) parsed directly from the corresponding ENVI `.hdr`.

## Notes

- Both source records are CC-BY-4.0; attribution is retained above.
- Raw ENVI `.img`/data files were removed after conversion to keep the repo
  lean; re-download via the links above if the full-resolution scenes are
  needed.
