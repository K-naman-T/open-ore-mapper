# EarthDaily / Descartes Labs — EnMAP vs SpecTIR at Cuprite (2024)

**Source:** https://earthdaily.com/blog/hyperspectral-imaging-for-mining-enmap-satellite-data-versus-spectir-airborne-data  
**Published:** 2024-06-13  
**Authors (case study):** Lori Wickert, Samuel Casement (spectral geologists)  
**Platform used:** Marigold (Descartes Labs / EarthDaily online mineral exploration RS interface)

## Sensors compared

| Attribute | SpecTIR airborne (2023) | EnMAP (DLR, 2022+) |
|-----------|-------------------------|--------------------|
| Instrument | SpecIM AISA Fenix-1K | EnMAP spaceborne |
| Spatial GSD | **1 m** | **30 m** |
| Spectral | 325 VNIR–SWIR bands; ~2.6 nm VIS, ~6.3 nm SWIR | 246 bands; ~6.5 nm VIS, ~10 nm SWIR |
| Range | 400–2450 nm | 400–2450 nm |
| Processing | SpecTIR radiometric + geometric + surface reflectance mosaic | DLR archive reflectance products |

Site: Cuprite, Nevada (low-sulfidation epithermal with high-sulfidation overprint; Swayze et al. 2014 ground truth / Tetracorder maps).

## Operational methods used (industry practice signals)

1. **First-look composition:** PCA and MNF RGB composites to differentiate lithology/alteration variance.  
2. **Masking:** vegetation/water/snow when present (not needed at arid Cuprite).  
3. **Endmembers:** **in-scene** spectra at Swayze et al. (2014) reference locations — not pure library-only mapping.  
4. **Classifier for consistency:** **Spectral Angle Mapper (SAM)** for all mineral species maps.  
5. **Reference maps:** Swayze et al. 2014 Tetracorder-style mineral maps (clays, micas, sulfates, carbonates).  
6. **Exploration product style:** RGB ternary (TRatio) of alunite temperature endmembers as vectoring visualization.  
7. **Caveat language:** sub-pixel unmixing needs endmember ID first; rule-of-thumb mentioned (~1/3 of pixel) is practitioner lore, not a validated OA metric in this post.

## Key findings (no overall accuracy % published in this article)

- EnMAP (30 m) can still map **species-level** alunites and large coherent features (e.g., Dickite Ridge) when exposures are large and spectrally distinct.  
- SpecTIR (1 m) shows **much more** mineral-species spatial detail and better purity of small/mixed exposures (buddingtonite, halloysite mixtures).  
- 30 m spatial mixing flattens/distorts rare endmembers (buddingtonite site mixes with Na-montmorillonite; playa false response).  
- Residual atmospheric features near ~2000 nm noted in EnMAP reflectance; bands excluded from mapping.  
- **Unsupervised discovery of unknown endmembers is much harder** than mapping when ground-truth locations are already known.

## Industry stack implications

Commercial mining RS (2024) still ships:
- PCA/MNF first looks  
- In-scene endmembers  
- SAM as workhorse supervised mapper  
- Ground-truth / classic Tetracorder Cuprite products as validation backdrop  
- Cloud platforms (Marigold) wrapping the same classical algorithms — not deep-learning-first mineral maps

## References cited in article (primary)

- Swayze et al. (2014). Mapping Advanced Argillic Alteration at Cuprite, Nevada, Using Imaging Spectroscopy. *Economic Geology* 109(5), 1179–1221.  
- Kruse et al. (2011). Effect of Reduced Spatial Resolution on Mineral Mapping… *Remote Sensing* 3, 1584–1602.  
- Rowan et al. (2003) ASTER Cuprite hydrothermal alteration. *Economic Geology*.
