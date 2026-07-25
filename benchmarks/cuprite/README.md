# Cuprite benchmark (optional full GT package)

Path A **CI default** is `../demo_fixture/` (planted dense spectra + scorecard).

This directory is reserved for a **real** Cuprite AVIRIS + published mineral map/ROIs package:

| File | Purpose |
|------|---------|
| `scene.mat` / `scene.tif` | Cuprite AVIRIS reflectance |
| `library.csv` | USGS-derived dense mineral spectra |
| `reference.tif` or `rois.json` | Ground truth |
| `legend.json` / `options.json` / `wavelengths.json` | Same schema as demo_fixture |

Fetch when network allows (EHU catalog id `cuprite_aviris`):

```bash
open-ore-mapper download-scene cuprite_aviris --output-dir benchmarks/cuprite
# then add library + reference and:
open-ore-mapper evaluate --benchmark benchmarks/cuprite --output-dir outputs/cuprite-eval
```

Until those assets exist, use:

```bash
make demo-fixture
# or
open-ore-mapper evaluate --benchmark benchmarks/demo_fixture --output-dir outputs/demo-fixture-eval
```
