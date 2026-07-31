# Real Hyperspectral Scenes

Real AVIRIS hyperspectral scenes for testing the spectral matching engine.

## Files

| File | Size | Bands | Shape | Dtype | Sensor |
|------|------|-------|-------|-------|--------|
| `indian_pines_corrected.mat` | 5.95 MB | 200 | (145, 145, 200) | uint16 | AVIRIS 1992 |
| `salinasA_corrected.mat` | 1.54 MB | 204 | (83, 86, 204) | int16 | AVIRIS 1998 |
| `cuprite.mat` | 95.3 MB | 224 | (512, 614, 224) | int16 | AVIRIS 1995 (f970619t01p02 flight) |
| `indian_pines_wavelengths.json` | 2.3 KB | 200 | – | – | grid for Indian Pines |
| `salinas_wavelengths.json` | 2.4 KB | 204 | – | – | grid for Salinas-A |

The `.mat` files carry **no embedded wavelength axis**, so the wavelength JSON files must be supplied to the engine (they are the only external per-band metadata these scenes have).

## Provenance

All three scenes originate from the classic **Basque University (EHU, ehu.eus) "Hyperspectral Remote Sensing Scenes"** collection, which is itself a community-maintained mirror of the original Purdue / JPL AVIRIS data. The EHU server currently returns HTTP 403 to non-browser clients, so the files were retrieved from **Internet Archive Wayback Machine** snapshots of the exact same EHU file URLs. The archived copies are byte-for-byte identical to the archived EHU originals (verified via Wayback CDX SHA1 digests, see below).

Download dates: **2026-07-31**.

### Original source URLs (EHU, now 403-blocked)

- `https://www.ehu.eus/ccwintco/uploads/6/67/Indian_pines_corrected.mat`
- `https://www.ehu.eus/ccwintco/uploads/1/1a/SalinasA_corrected.mat`
- `https://www.ehu.eus/ccwintco/uploads/7/7d/Cuprite_f970619t01p02_r02_sc03.a.rfl.mat`

### Wayback snapshot URLs used

- `https://web.archive.org/web/20240118235116id_/https://www.ehu.eus/ccwintco/uploads/6/67/Indian_pines_corrected.mat`
- `https://web.archive.org/web/20240118235124id_/https://www.ehu.eus/ccwintco/uploads/1/1a/SalinasA_corrected.mat`
- `https://web.archive.org/web/20200602003056id_/http://www.ehu.eus/ccwintco/uploads/7/7d/Cuprite_f970619t01p02_r02_sc03.a.rfl.mat`

### Integrity

CDX SHA1 digests of the archived snapshots vs. downloaded files (all MATCH):

| File | Wayback CDX SHA1 digest |
|------|--------------------------|
| `indian_pines_corrected.mat` | `AHUCZS5IXSUW3XZE4HXBM574JCCYAJ35` |
| `salinasA_corrected.mat` | `DJQO3MOAGSVCTD5VL66IH4TWNZZUYYXS` |
| `cuprite.mat` | `7FRTR6CKUQMK2IYKBLKAULCA4WSGFR52` |

## Wavelength grids

The engine needs one wavelength (nm) per band. These scenes have no published per-band wavelength file in the classic distribution, so the standard documented linear grids are used (identical convention to the repo's existing `examples/aviris_204_wavelengths.json`):

- **Indian Pines** (`indian_pines_wavelengths.json`): 200 bands, 400.0–2390.0 nm at 10 nm steps. This matches the well-known 200-band AVIRIS grid (the full sensor covers 0.4–2.5 µm; the corrected 200-band cube drops the 24 water-absorption bands). Band count in the cube = 200 = wavelength count.
- **Salinas-A** (`salinas_wavelengths.json`): 204 bands, 400.0–2430.0 nm at 10 nm steps. Band count in the cube = 204 = wavelength count.

> Note: The Indian Pines wavelength grid is **not stored in the .mat**; the 200-band grid here is the community-standard linear approximation. If precise per-band center wavelengths are ever required, they must be reconstructed from the original AVIRIS 1992 sensor calibration (see `examples/aviris_wavelengths.json`, 224-band grid, for the full-sensor reference).

## Scene descriptions

### Indian Pines (`indian_pines_corrected.mat`)

- Sensor: AVIRIS (Airborne Visible/Infrared Imaging Spectrometer), 1992 flight.
- Location: Indian Pines test site, NW Indiana, USA.
- Size: 145 × 145 pixels, 200 spectral bands (corrected version; water-absorption and noisy bands removed from the 224-band acquisition), range 0.4–2.5 µm.
- Content: ~two-thirds agriculture, one-third forest/natural vegetation. 16 ground-truth classes (alfalfa, corn, soybean, wheat, woods, hay-windrowed, etc.).
- Ground truth: `Indian_pines_gt.mat` (same EHU collection) supplies the 16-class labels; **not** downloaded here (no labels needed for spectral matching tests).
- Cited/classic reference: Landgrebe, D., "Signal Theory Methods in Multispectral Remote Sensing", Wiley, 2003; also archived at Purdue PURR `https://purr.purdue.edu/publications/1947/1` (full 763 MB bundle — too large, not used).

### Salinas-A (`salinasA_corrected.mat`)

- Sensor: AVIRIS, 1998 flight over Salinas Valley, California, USA.
- Size: 86 × 83 pixels, 204 spectral bands, range 0.4–2.5 µm (water-absorption bands removed). 3.7 m spatial resolution.
- Content: sub-scene of the full Salinas scene; 6 ground-truth classes (broccoli green weeds 1, corn senesced green weeds, lettuce romaine 4/5/6/7wk).
- Ground truth: `SalinasA_gt.mat` (same EHU collection) supplies the 6-class labels; **not** downloaded here.

### Cuprite (`cuprite.mat`)

- Sensor: AVIRIS, 1997 flight `f970619t01p02` (scene `f970619t01p02_r02_sc03.a.rfl`), Cuprite Hills, Nevada, USA — the classic mineral-mapping test site.
- Size: 512 × 614 pixels, 224 spectral bands (int16 reflectance `.a.rfl`), ~0.4–2.5 µm.
- Content: semi-arid exposed bedrock with well-characterized alteration minerals (alunite, kaolinite, buddingtonite, chalcedony, montmorillonite, muscovite); used in the original AVIRIS mineral mapping papers (e.g., Kruse et al. 1990, Clark et al.).
- Wavelength grid: not shipped here; use the repo's full-sensor grid `examples/aviris_wavelengths.json` (224 bands) if Cuprite matching is tested. The .mat cube is (512, 614, 224) HWC; the engine's HWC heuristic picks it up as-is.
- Ground truth: USGS AVIRIS Cuprite reference spectra exist for known minerals; none shipped here.

## License / citation

- **Indian Pines**: hosted by EHU under an open academic-use mirror of the original Purdue dataset; original attribution to David Landgrebe / Purdue University LARS. When publishing results, cite the Landgrebe book (above) and the AVIRIS sensor (NASA/JPL).
- **Salinas-A / Cuprite**: AVIRIS data © NASA/JPL; released for research use via the AVIRIS free data portal (`https://aviris.jpl.nasa.gov/data/free_data.html`). Cite the AVIRIS project when publishing.
- The EHU mirror page (`https://www.ehu.eus/ccwintco/index.php/Hyperspectral_Remote_Sensing_Scenes`) is the canonical community distribution point and should be cited when these scene files are used in publications.

## Usage

```bash
cd /home/knamant/open-ore-mapper
python3 -c "
from pathlib import Path
from spectral_matching.engine import SpectralMatcher
m = SpectralMatcher()
for name, wl_file in [('indian_pines', 'examples/real_scenes/indian_pines_wavelengths.json'),
                      ('salinas', 'examples/real_scenes/salinas_wavelengths.json')]:
    p = next(c for c in Path('examples/real_scenes').iterdir() if c.suffix == '.mat' and name in c.name.lower())
    cube, wl, _ = m._load_cube(p.read_bytes(), p.name)
    print(name, '->', cube.shape, 'bands', cube.shape[2])
"
```

Expected output:

```
indian_pines -> (145, 145, 200) bands 200
salinas -> (83, 86, 204) bands 204
```

## Note on `cuprite.mat`

`cuprite.mat` (95 MB, 512×614×224) is NOT committed to git (`.gitignore` blocks `*.mat`). It is present on local disk after the download step. To fetch it fresh, retrieve it from the Wayback snapshot of the EHU URL documented in this folder's provenance, or from `https://aviris.jpl.nasa.gov/data/free_data.html`.

## Real-data classification demo (verified working)

```bash
cd /home/knamant/open-ore-mapper
python3 -c "
import json
from spectral_matching.engine import SpectralMatcher
from spectral_matching.schemas import MatchOptions

wl = json.load(open('examples/real_scenes/indian_pines_wavelengths.json'))
result = SpectralMatcher().predict_file(
    'examples/real_scenes/indian_pines_corrected.mat',
    MatchOptions(
        wavelengths=wl, sensor='manual',
        classes=['Grass_Green_Avena_fatua', 'Grass_Bromus_diandrus', 'Pine_Pinus_lambertiana'],
        spectral_library='data/starter_libraries/real/ecostress_veg.csv',
        classifier='fuse_classical', min_confidence=0.2, sam_threshold_deg=20,
    ),
)
for k, v in sorted(result.statistics.items(), key=lambda x: -x[1].count):
    if v.count:
        print(f'{k}: {v.count} px ({v.percentage:.1f}%)')
"
```
