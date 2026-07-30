# Starter Libraries

Three spectral library CSV files for use with the `spectral_matching` engine. Each file
contains synthetic reflectance spectra at ~200 bands from 450–2500 nm (~10.3 nm spacing).

## Format

All files use the same format:

```
class,wavelength,reflectance
Alunite,450.0,0.631234
Alunite,460.3,0.642188
...
```

- `class` — material class name (mineral, vegetation type, or surface type)
- `wavelength` — wavelength in nanometres
- `reflectance` — reflectance value in [0, 1]

## Files

| File | Classes | Description |
|------|---------|-------------|
| `usgs_minerals.csv` | 12 | Common minerals (Alunite, Calcite, Chlorite, Dolomite, Epidote, Goethite, Hematite, Illite, Jarosite, Kaolinite, Montmorillonite, Muscovite) with representative absorption features |
| `ecostress_veg.csv` | 8 | Vegetation types (Broadleaf, Conifer, Grassland, Shrubland, Tundra, Crop, Wetland, Urban) based on ECOSTRESS endmember characteristics |
| `urban_materials.csv` | 6 | Urban surfaces (Asphalt, Concrete, Metal Roof, Red Tile, White Roof, Bare Soil) |

## Source

These are **synthetic starter spectra** generated for software development and
demonstration purposes. They are not authoritative scientific data. Absorption
features are modelled as Gaussian dips at characteristic wavelengths with
approximate depths. Use them for:

- Pipeline testing and integration
- UI demonstration
- Teaching and exploration

For production work, replace with library-grade spectra (e.g. USGS Spectral
Library, ECOSTRESS spectral library).
