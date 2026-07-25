# Cuprite real validation package

## Sources
- **Cube:** AVIRIS Cuprite 1995 ENVI cube from [nicedi/AVIRIS-Cuprite-Nevada-Tetracorder-Results](https://github.com/nicedi/AVIRIS-Cuprite-Nevada-Tetracorder-Results) (`cubes/cuprite95`)
- **Ground truth:** Tetracorder 4.4 mineral `*.fd.gz` fit maps from the same release (`group.1um`, `group.2um`)
- **Library:** median spectra of high-purity GT pixels per mineral (scene endmembers) — not independent lab spectra

## Reproduce
```bash
# cube already in raw/ after 7z extract; GT in gt/
python scripts/run_cuprite_real_validation.py
# → outputs/cuprite-real-eval/comparison_panel.png
```

## Caveats
Scene-derived endmembers are **not** a fully independent validation of discovery.
They show the engine can map real AVIRIS reflectance against Tetracorder labels with a scene-appropriate library.
Independent USGS lab spectra remain the next bar for library purity.
