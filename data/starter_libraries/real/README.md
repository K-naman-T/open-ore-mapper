# Real Measured Spectra

Real laboratory reflectance spectra for the `spectral_matching` engine, replacing
(or supplementing) the synthetic starter spectra with measured data.

## Files

| File | Classes | Description |
|------|---------|-------------|
| `relab_minerals.csv` | 13 | Measured RELAB bidirectional reflectance spectra of common rock-forming minerals and iron oxides |

## Format

Same CSV format as the other starter libraries:

```
class,wavelength,reflectance
Olivine,450.0,0.535105
Olivine,460.0,0.534670
...
```

- `class` — material class name
- `wavelength` — wavelength in nanometres (common grid, 450.0–2500.0 nm at 10 nm spacing, 206 bands)
- `reflectance` — reflectance factor in [0, 1]

All classes share the same strictly increasing wavelength grid.

---

## Provenance: RELAB Spectral Library

The spectra in `relab_minerals.csv` are bidirectional reflectance measurements made
at the NASA/Keck **Reflectance Experiment Laboratory (RELAB)** at Brown University
(Pl: Ralph Milliken, formerly Carle Pieters), archived as PDS4 products at the NASA
PDS Geosciences Node.

- **Archive root:** `https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/`
- **Reflectance data:** `https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/bdr3/`
- **Citation:** Milliken, R. (2020). RELAB Spectral Library Bundle, NASA Planetary Data System.
  `urn:nasa:pds:relab::1.0` — DOI: `10.17189/1519032`
- **Download date:** 2026-07-31

Each class is a single measured spectrum of a distinct RELAB specimen (no two classes
share a sample). Wavelengths are in nanometres; reflectance is the RELAB-reported
reflectance factor (already in [0,1]).

### Samples used

| Class | RELAB sample ID | Specimen name (from PDS4 label) | Label file |
|-------|-----------------|---------------------------------|------------|
| Olivine | `c1dd37` | Olivine (Fo 90) | `bdr3/c1dd37.xml` |
| Orthopyroxene | `c1dl01` | Orthopyroxene- En 100 | `bdr3/c1dl01.xml` |
| Clinopyroxene | `c1ag10` | Augite | `bdr3/c1ag10.xml` |
| Hematite | `c1jb548` | Hematite Iron Oxide- Lane hematite | `bdr3/c1jb548.xml` |
| Goethite | `c1jbh57` | Goethite 21717 fine unsorted (Red coating) | `bdr3/c1jbh57.xml` |
| Magnetite | `c1jb764` | Magnetite | `bdr3/c1jb764.xml` |
| Anorthite | `c1dh18` | Anorthite (An 91) | `bdr3/c1dh18.xml` |
| Quartz | `c1dh03` | Quartz 1 | `bdr3/c1dh03.xml` |
| Calcite | `c1jbe58a` | Big Timber calcite | `bdr3/c1jbe58a.xml` |
| Montmorillonite | `c1jb784` | Montmorillonite- CMS standard SWy-2 | `bdr3/c1jb784.xml` |
| Kaolinite | `c1jb225a` | Kaolinite- KGa-1 <125 um resieved on January 2008 | `bdr3/c1jb225a.xml` |
| Basalt | `c1ac01` | Basalt- BaG1 | `bdr3/c1ac01.xml` |
| Serpentine | `c1jb732` | Chrysotile | `bdr3/c1jb732.xml` |

Exact file URLs (example for Olivine; substitute the sample ID):

```
https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/bdr3/c1dd37.tab
https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/bdr3/c1dd37.xml
```

### Processing / resampling

1. Each `.tab` (PDS4 table) product is parsed for `wavelength` (nm) and `reflectance`
   columns (first two numeric columns of the data table).
2. Raw spectra were resampled to a **common grid of 450.0–2500.0 nm at 10 nm spacing
   (206 bands)** using `numpy.interp` (linear interpolation).
3. Interpolated reflectance was clamped to [0, 1]. Raw RELAB values already fell in
   [0, 1]; clamping only guards against any floating-point edge overshoot.

### License / usage

PDS4 archive products at the NASA PDS Geosciences Node are **U.S. government works
and are in the public domain** (NASA/Caltech/Tri-Institutional). No NASA endorsement
implied. Attribute the data via the citation above when used in publications.

Note: RELAB spectra at these wavelengths are bidirectional reflectance measurements
made in the lab (BDR spectrometer, ~0.3–2.6 µm); instrument details are in each PDS4
label and in the RELAB User's Manual in the `document/` collection of the archive.

### References

- RELAB archive: `https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/`
- RELAB facility: `https://sites.brown.edu/relab/`
- DOI: `10.17189/1519032`
- Sample-composition references embedded in labels, e.g.:
  - Dyar, M. D. et al. (2009) American Mineralogist, 94, 883-898 (olivine).
  - Klima, R. L. et al. (2007) Meteoritics & Planetary Science 42, 235-253 (pyroxenes).
