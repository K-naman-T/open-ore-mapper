# Industry / Operational Baseline for Hyperspectral Surface Mineral Mapping (2020–2026)

**Document for:** open-ore-mapper  
**Research window:** literature and vendor practice ~2020–2026 (with foundational methods from 1990s–2010s still in production)  
**Compiled:** 2026-07-26  
**Method:** primary vendor docs (NV5/ENVI), USGS/NASA/ESA operational products, commercial mining RS case studies, peer-reviewed method papers; local scrapes under `docs/research_scrapes/industry/`  
**Honesty rule:** overall accuracy (OA) and kappa values appear **only** when found in cited sources. No invented OA numbers.

---

## Executive summary

The **operational baseline** for surface mineral mapping from imaging spectroscopy (AVIRIS/AVIRIS-NG, HyMap, SpecTIR AISA, EnMAP, PRISMA, EMIT, etc.) remains a **classical spectroscopy stack**, not deep learning:

1. Radiometric / atmospheric prep to **surface reflectance**  
2. Bad-band removal and optional vegetation/water masks  
3. **Dimensionality reduction** (especially **MNF**)  
4. **Endmember** discovery (PPI + n-D visualizer, or automated VCA/N-FINDR) **or** curated library / in-scene target spectra  
5. Mapping with **SAM**, **SFF / continuum feature fitting**, and/or **MTMF / MF / ACE**  
6. Optional abundance maps (linear unmixing or MTMF scores)  
7. Expert review + field/XRD validation  

Commercial geoscience software (ENVI), government expert systems (**Tetracorder**), drill-core industry software (**TSG**), and cloud mining products (**Marigold** et al.) all implement variants of this chain. Deep learning appears in research and vendor roadmaps but is **not** the 2020–2026 production default for unlabeled exploration mapping.

---

## 1. Operational stack

### 1.1 Two industry workflows (ENVI formalization)

NV5’s hyperspectral analytics whitepaper (ENVI 6.0-era; Wolfe & Black, with Boardman as contributor) defines two standard paths that match how mineral mappers work in practice:

| Workflow | When used | Core steps | Typical outputs |
|----------|-----------|------------|-----------------|
| **Spectral Hourglass** | “What minerals are in this scene?” (exploration / unmixing) | Reflectance → **MNF** → **PPI** → **n-D Visualizer** endmembers → Material ID / library match → **SAM / SFF / LSU / MTMF** | Class maps, rule images, abundance / MF-score maps |
| **Target Detection** | “Where is mineral X?” (known targets) | Reflectance (or radiance for some detectors) → optional MNF (**required for MTMF**) → library or ROI targets → **ACE / CEM / MF / MTMF / SAM / SID / OSP / TCIMF…** → interactive threshold | Target ROIs, rule images, shapefiles |

Primary source:  
https://www.nv5geospatialsoftware.com/Support/Maintenance-Detail/hyperspectral-analytics-in-envi-target-detection-and-spectral-mapping-methods  
Local excerpt: `docs/research_scrapes/industry/NV5_ENVI_Hyperspectral_Analytics_excerpt.md`

ENVI training still centers Cuprite AVIRIS + SAM/SFF as the teaching default:  
https://vis-webcontent.s3.amazonaws.com/tutorials/pdfs/WholePixelHyperspectralAnalysisTutorial.pdf  
Local text: `docs/research_scrapes/industry/ENVI_SAM_SFF_Tutorial.txt`

### 1.2 Full processing chain (industry “hourglass + physics”)

```
[Sensor DN / radiance]
        │
        ▼
 Bad bands / water-vapor gaps removed
        │
        ▼
 Atmospheric correction → apparent surface reflectance
   (FLAASH/MODTRAN, QUAC, empirical line, IARR, flat field…)
        │
        ▼
 Optional: vegetation / cloud / water masks
        │
        ▼
 Spectral subset to diagnostic ranges (often SWIR 2.0–2.5 µm for clays/sulfates/carbonates;
                                       VNIR for Fe-oxides)
        │
        ├──────────────────────────────┐
        ▼                              ▼
 MNF / noise-aware reduce          Full-band (target detection often keeps full dim)
        │
        ▼
 Endmember path: PPI + n-D viz / VCA / N-FINDR / ATGP
   OR library-only / in-scene ROI means
        │
        ▼
 Identify endmembers (library match, expert rules, Material ID)
        │
        ▼
 Map: SAM | SFF | MTMF | ACE | MF | Tetracorder-style feature rules
        │
        ▼
 Threshold, clean, abundance visualization, GIS delivery
        │
        ▼
 Field spectra / XRD / XRF validation (when budget allows)
```

### 1.3 Algorithm roles and **rank by operational commonality**

Ranking is **commercial + government practice** (ENVI defaults, training curricula, mining contractors, NASA EMIT mineral pipeline, EnMAP geology apps), **not** paper citation counts.

| Rank | Method | Role | Why it ranks here | Notes |
|-----:|--------|------|-------------------|-------|
| **1** | **Surface reflectance + bad bands** | Prerequisite | Without reflectance, library and SFF break | FLAASH/QUAC industry; EMIT/EnMAP L2 products often skip user ATM |
| **2** | **SAM (Spectral Angle Mapper)** | Whole-pixel similarity / default class map | Ubiquitous in ENVI tutorials, commercial Cuprite case studies (e.g. EnMAP vs SpecTIR 2024), open tools | Scale-invariant; needs threshold; fails with huge uncurated libraries |
| **3** | **MNF (Minimum Noise Fraction)** | Dimensionality + noise separation | Hourglass **requires** it; preferred over PCA for pure-pixel work | Green et al. (1988) lineage; eigenvalue “elbow” is analyst judgment |
| **4** | **PPI + n-D Visualizer endmembers** | Unsupervised pure-pixel discovery | ENVI Spectral Hourglass core; still taught 2020s | Interactive; automation uses VCA/N-FINDR/ATGP as stand-ins |
| **5** | **MTMF (Mixture-Tuned Matched Filtering)** | Sub-pixel abundance + false-positive control | ENVI unmixing/target path; exploration literature (Boardman/Kruse) | Needs MNF space; MF score + **infeasibility** |
| **6** | **SFF / continuum removal + feature fit** | Absorption-feature mineral ID | ENVI mapping methods; physically aligned with mineral spectroscopy | Best for minerals with sharp SWIR features; continuum required |
| **7** | **Tetracorder (expert system / multi-feature rules)** | Government / mission mineral ID | USGS Clark et al.; **EMIT operational mineral mapping** | Not a single distance metric; rule files + feature weights |
| **8** | **ACE / CEM / MF** | Target detection family | ENVI Target Detection Workflow defaults set | ACE strong for unknown/variable background; MF noisier than MTMF |
| **9** | **Linear spectral unmixing (LSU / NNLS / FCLS)** | Abundance if full endmember set known | Hourglass option; fragile if endmembers incomplete | ENVI docs prefer MTMF when endmembers incomplete |
| **10** | **SID / hybrid metrics** | Alternate whole-pixel distances | Available in ENVI/pysptools; less default than SAM | Research-heavy |
| **11** | **Deep learning classifiers** | Research / site-specific supervised maps | Growing papers 2020–2026; rare as unsupervised exploration default | Needs labels; domain shift across deposits |

**Feature-fitting / expert systems vs matched filters:**  
Exploration geoscience historically splits into (A) **physics of absorptions** (SFF, Tetracorder, TSG feature indices) and (B) **statistical matched filters / geometry** (MNF–PPI–MTMF). Production shops often **run both** and reconcile.

### 1.4 Method capsule definitions (operational)

| Method | Input | Output | Key requirement |
|--------|-------|--------|-----------------|
| **MNF** | Cube (often reflectance) | Ordered noise-whitened components | Keep coherent low-index bands (eigenvalue ~ >1) |
| **PPI** | MNF cube | Purity score image | Many random projections; pure pixels at data-cloud extremes |
| **SAM** | Reflectance cube + endmembers | Angle rule images + class map | Same units as library; max-angle threshold |
| **SFF** | Continuum-removed reflectance + library | Scale + RMS per material | Diagnostic absorptions present in band set |
| **MF** | Targets + background stats | Detection / relative abundance scores | Many false positives on rare materials |
| **MTMF** | **MNF** cube + targets | MF score + infeasibility | Reject high-infeasibility hits |
| **ACE** | Targets + background covariance | Detection statistic | Good for variable background, sub-pixel |
| **Tetracorder** | Continuum-removed features + expert rules | Material IDs / weighted maps | Rule library; multi-feature decisions |

### 1.5 Preprocessing that is “non-negotiable” in ops

From ENVI guidance and operational practice:

1. **Know the sensor:** pushbroom vs whiskbroom; SNR; SWIR coverage for Al–OH / Fe–OH / Mg–OH / CO₃.  
2. **Remove bad bands:** water vapor (~1.4 µm, ~1.9 µm) and sensor-dead channels (Hyperion classic lists remain a cautionary tale).  
3. **Reflectance for library/SAM/SFF:** library and image must share units and scaling (0–1 vs 0–10000).  
4. **Resample library to sensor SRF** (USGS provides pre-convolved sets for AVIRIS, HyMap years, etc.).  
5. **In-scene endmembers often beat lab libraries alone** for mapping (illumination and mixing match the cube)—ENVI and 2024 commercial Cuprite work both emphasize this.

---

## 2. What industry actually ships vs what papers claim

### 2.1 What industry / ops **ship**

| Segment | What customers receive | Algorithms under the hood |
|---------|------------------------|---------------------------|
| **ENVI / NV5** | Hourglass & Target Detection wizards; SAM/SFF tutorials on Cuprite; FLAASH/QUAC | Full classical stack (§1) |
| **SpecTIR** | Airborne cubes + **discrete mineral / alteration maps** for mining & geothermal | Service pipeline; fusion with other geophysics (https://www.spectir.com/services) |
| **EarthDaily / Descartes Marigold** | Cloud RS for mineral exploration; published EnMAP/SpecTIR Cuprite mapping | **PCA/MNF + in-scene endmembers + SAM**; validation vs Swayze 2014 maps (2024 blog) |
| **Pixxel** | Satellite HSI products for mining (detection, monitoring, compliance messaging) | Marketing emphasizes mineral detection; public pages do **not** document open algorithm recipes (https://www.pixxel.space/solution/mining) |
| **Corescan / HyLogger + TSG** | **Drill-core** mineral logs (industry standard for core, not airborne) | Feature extraction + mineral interpretation in **The Spectral Geologist (TSG)** |
| **NASA EMIT** | Global arid-region **mineral maps** (hematite, goethite, kaolinite, etc.) | Reflectance → **feature fitting / Tetracorder-family** mineral detection (Clark et al. mission use) |
| **DLR EnMAP + EnMAP-Box / EnGeoMAP** | Open satellite data + QGIS toolbox / geologic expert apps | GFZ EnGeoMAP expert-system geology path; research mapping workflows |

Local notes:  
- `docs/research_scrapes/industry/SpecTIR_services_minerals.md`  
- `docs/research_scrapes/industry/EarthDaily_EnMAP_vs_SpecTIR_Cuprite_2024.md`

### 2.2 What papers often claim (and ops ignore)

| Paper culture | Operational reality |
|---------------|---------------------|
| New distance metrics / deep nets with high OA on **small labeled patches** | Ops need **transfer** to new districts without dense labels |
| End-to-end DL from radiance | Ops use **agency L2 reflectance** when available |
| Huge multi-class OA tables | Ops deliver **alteration mineral assemblages** for exploration vectors, not 30-class land cover |
| Full automatic endmember count | Analysts still **edit** PPI/n-D clusters and thresholds |
| “Beat Tetracorder / USGS map” with pixel OA | Often **agreement with another map**, not independent XRD grid |
| Perfect unmixing fractions | Deliver **relative** MF scores / qualitative abundance; absolute fractions rare without rigorous calibration |

### 2.3 2020–2026 shift (real, but incremental)

1. **More spaceborne HSI** (EnMAP, PRISMA, EMIT, commercial constellations) → same algorithms, harder spatial mixing.  
2. **Cloud platforms** wrap classical tools at scale (Marigold-style).  
3. **EMIT global mineral products** show government ops still trust **continuum feature expert systems**.  
4. **Core scanning** (Corescan/TSG) is where mining spends daily spectral budgets—airborne/satellite maps feed **targeting**, core spectra feed **resource definition**.  
5. DL/ML is active in research and some proprietary ranking models; **unsupervised exploration defaults remain SAM/MTMF/SFF/Tetracorder-class**.

---

## 3. Cuprite and mineral-specific accuracy claims (with caveats)

Cuprite, Nevada is the **de facto spectral reference district** (advanced argillic / argillic diversity). Almost every stack is demoed there. **Read OA numbers with extreme care.**

### 3.1 Foundational ground truth

- **Swayze et al. (2014), *Economic Geology*** — detailed imaging spectroscopy + field mapping of advanced argillic alteration; Tetracorder-style mineral maps widely used as **reference maps** by later studies and commercial blogs.  
  DOI family: Economic Geology 109(5), 1179–1221.  
- **Clark et al. Tetracorder papers** (e.g. AGU *JGR* imaging spectroscopy / expert system series) — expert-system rules; field/XRD checks at traverses (e.g. muscovite Al content, goethite) show **qualitative/semi-quantitative agreement**, not a single global OA for all minerals.  
  USGS overview: https://www.usgs.gov/publications/imaging-spectroscopy-earth-and-planetary-remote-sensing-usgs-tetracorder-and-expert  
- **USGS Cuprite mineral map products** (AVIRIS-derived Tetracorder maps) are often treated as “truth” by later automated algorithms — this **inflates OA** when the new method is correlated with the same spectroscopy family.

### 3.2 Published numeric claims (with caveats)

| Source | What was compared | Reported figure | Caveat |
|--------|-------------------|-----------------|--------|
| **Wei et al. (2017), *J. Appl. Remote Sens.*** SMMA decision-tree on diagnostic SWIR features | AVIRIS / Hyperion maps vs **USGS Tetracorder-style map** at Cuprite | AVIRIS **OA 94.82%**, **κ = 0.9317**; Hyperion **OA 74.54%**, **κ = 0.6234**; per-class producer acc. e.g. Kao+Mus 97.57%, montmorillonite **58.59%** (AVIRIS) | **Map-to-map agreement**, not independent dense XRD. Low OA minerals = mixed/dispersed classes. SNR + GSD drive AVIRIS vs Hyperion gap. PDF: https://weijing-rs.github.io/publications/Wei_et_al-JARS-2017.pdf |
| **Kruse et al. (2004) AVIRIS vs Hyperion mineral mapping** (Death Valley case; NTRS PDF) | MTMF mineral maps | **Overall accuracy 76%** reported for that site’s validation setup | Different site than Cuprite; still classic MTMF ops number. https://ntrs.nasa.gov/api/citations/20050192448/downloads/20050192448.pdf |
| **Tsubomatsu et al. (2025)** Tetracorder + Random Forest | Labels vs **2006 reference map** | **~80%** pixel agreement cited in abstract material | Again reference-map agreement; hybrid classical+ML. https://www.mdpi.com/2673-4591/94/1/25 |
| **EarthDaily Wickert & Casement (2024)** EnMAP 30 m vs SpecTIR 1 m | SAM maps vs Swayze et al. (2014) patterns | **No single OA%** in article; qualitative: EnMAP maps large coherent species (alunite types, Dickite Ridge); fails/mixes on small buddingtonite; SpecTIR finer species purity | Honest operational comparison of **GSD**. https://earthdaily.com/blog/hyperspectral-imaging-for-mining-enmap-satellite-data-versus-spectir-airborne-data |
| **ENVI training (SAM/SFF)** | Cuprite AVIRIS reflectance tutorial | No formal OA; teaches **visual rule-image thresholding** | Thresholds are analyst-dependent — ops reality |

### 3.3 Structural caveats for **all** Cuprite OA numbers

1. **Label source:** Tetracorder/USGS map vs XRD point samples vs polygon field maps — not interchangeable.  
2. **Spatial split:** Random pixel splits leak spatial autocorrelation; optimistic OA. Prefer **block / alteration-center holds**.  
3. **Class taxonomy:** “kaolinite” vs “kaolinite+muscovite” vs crystallinity/Al-content subclasses change scores.  
4. **Sensor SNR & GSD:** Hyperion-class noise and 30–60 m GSD systematically lower species purity vs AVIRIS/HyMap/SpecTIR.  
5. **Library vs in-scene endmembers:** in-scene matches inflate apparent accuracy relative to pure library transfer.  
6. **Threshold tuning on the test site:** common and rarely reported.  
7. **Mixtures:** montmorillonite, buddingtonite, edge pixels — systematically low agreement in multi-study narrative.  
8. **Do not treat research synthesis “~95% Tetracorder” style summaries as measured OA** without the original validation design.

### 3.4 Mineral-specific difficulty (practice consensus)

| Easier (distinct SWIR / large exposures at Cuprite) | Harder |
|-----------------------------------------------------|--------|
| Alunite (species separable when pure), kaolinite (doublet), coarse muscovite/illite trends, calcite (if SWIR/TIR OK) | Montmorillonite mixtures, buddingtonite (often mixed), halloysite in multi-mineral pixels, low-contrast chlorite, vegetation-mixed pixels, Fe-oxide crystallinity continuum |

---

## 4. Spectral libraries — usage norms

### 4.1 Libraries in operational use

| Library | Typical use | Norms |
|---------|-------------|--------|
| **USGS Spectral Library Version 7 (splib07)** | Default mineral reference for terrestrial HSI; Tetracorder / ENVI / research | **Leading community mineral library** (Kokaly et al. 2017, USGS DS 1035). Includes convolved versions for AVIRIS-era, HyMap 2007/2014, etc. Public domain US Gov work — redistributable with citation. https://www.usgs.gov/labs/spectroscopy-lab/usgs-spectral-library |
| **ECOSTRESS Spectral Library (JPL)** | Broad materials (minerals + veg + man-made); includes JHU/JPL/USGS Reston content | Convenient compilation (~3400+ spectra). **License is restrictive (“all rights reserved”)** — runtime fetch, do not bundle in Apache products without legal review. https://speclib.jpl.nasa.gov/ |
| **RELAB (Brown / NASA PDS)** | Planetary + lab bidirectional reflectance; large specimen count | Strong for research and exotic materials; **less default for terrestrial mining ops** than USGS. PDS access: https://pds-geosciences.wustl.edu/spectrallibrary/default.htm |
| **In-scene endmembers / field ASD** | Highest mapping fidelity for a given flight | Industry preference when ground access exists; used in EarthDaily 2024 Cuprite work |
| **CSIRO / HyLogger / TSG libraries** | Drill-core mineral interpretation | Core ops standard; not freely bulk-redistributable exploration libraries |

Project-local license analysis: `SPECTRAL_LIBRARIES_RESEARCH.md`.

### 4.2 Usage norms (what pros actually do)

1. **Curate 10–40 scene-relevant spectra**, not full 500-mineral brute force.  
2. **Convolve to sensor** bandpasses before SAM/SFF.  
3. **Scale match** reflectance (0–1 vs scaled ints).  
4. Prefer **continuum-removed** comparison for SFF/Tetracorder; **whole-spectrum angle** for SAM.  
5. Use library to **name** image endmembers after unsupervised extraction (hourglass Material ID).  
6. Maintain **multiple grain sizes / crystallinities** for Fe-oxides and clays when discriminating species.  
7. Never mix radiance image with reflectance library.

---

## 5. Open-source tools (ENVI alternatives)

Detailed inventory: `docs/research_scrapes/industry/open_source_tools_inventory.md`

| Tool | License | Closest ENVI analog | Gaps |
|------|---------|---------------------|------|
| **Spectral Python (SPy)** | MIT | ENVI I/O + basic SAM | No full hourglass UI |
| **PySptools** | Open (historical SourceForge/PyPI) | MNF, PPI, N-FINDR, ATGP, HySime, SAM, SID, ACE, CEM, MF, OSP, NNLS/FCLS, continuum | Aging maintenance; no MTMF-complete product UI |
| **HySUPP** | Open research package | Modern unmixing zoo | Research-oriented |
| **EnMAP-Box + EnGeoMAP** | GPL-3+ | QGIS hyperspectral workbench / geologic expert app | EnMAP-centric; learning curve |
| **PSI Tetracorder artifacts** | Training/research distributions | Expert system mineral ID | Not a pip-install product |
| **USGS PyHAT** | Open (USGS Astro) | Spectroscopy + ML helpers | Planetary lean |
| **GRASS `i.pysptools.unmix`** | GPL (GRASS) | Batch unmixing | GIS integration only |
| **open-ore-mapper (this project)** | project license | SAM, continuum, ACE, MTMF, SFF, NNLS/SUnSAL path | Aim: unsupervised defaults aligned with §6 |

**There is still no complete open “ENVI Hourglass Wizard” clone** with interactive n-D visualizer parity. Closest algorithmic coverage: **PySptools + SPy + custom continuum/SFF**. Closest expert-system geology: **EnGeoMAP / Tetracorder**.

---

## 6. Concrete recommendations for **open-ore-mapper** unsupervised defaults

Goal: match **industry exploration deliverables** (alteration mineral maps + confidence) without interactive ENVI n-D visualizer, without requiring labeled training data.

### 6.1 Default pipeline (recommended product path)

```
1. Ingest reflectance cube (or radiance → document ATM status)
2. Bad-band / water-vapor mask; optional NDVI vegetation mask
3. Optional SWIR-priority spectral subset for clay/sulfate/carbonate mode
4. MNF (or noise-whitened PCA) → keep components with eigenvalue ≳ 1
   or HySime/HfcVd estimate of virtual dimensionality
5. Endmember extraction (default VCA; optional N-FINDR / PPI)
   → k = HySime estimate clipped to [5, 25]
6. Endmember identification:
   a) Continuum-removed SFF / feature score vs curated USGS subset
   b) SAM angle as secondary rank
   c) Reject if best score below threshold → label "unidentified_endmember_N"
7. Scene mapping:
   PRIMARY: SAM against *identified endmembers only* (not full 500-library)
   SECONDARY product: MTMF (MNF space) MF-score + infeasibility mask
   OPTIONAL: NNLS abundance using accepted endmembers
8. Outputs: class map, rule/confidence, MF-score stack, QA layers
```

### 6.2 Default algorithm flags

| Parameter | Recommended default | Rationale |
|-----------|---------------------|-----------|
| Classifier | **SAM on scene endmembers** | Industry whole-pixel default; unsupervised after endmember ID |
| Endmember extractor | **VCA** (fallback N-FINDR) | Automatable PPI substitute |
| Dimensionality | **MNF keep** via eigenvalue > 1 or HySime | Hourglass-aligned |
| Library | **USGS splib07 curated** hydrothermal + Fe-oxide + carbonate packs | Redistributable; mining-relevant |
| Library size | **≤ 30** spectra per geologic pack | Avoid min-angle false winners |
| SAM threshold | Start **0.10 rad**; expose slider | ENVI-style interactive thresholding |
| Sub-pixel | **MTMF on** as second product, off as sole default class map | Matches ENVI “better than MF”; needs MNF |
| Feature physics | **SFF/continuum** for naming endmembers + optional hard mineral rules | Tetracorder-lite without full expert DB |
| Unmixing | NNLS if ≤ ~20 endmembers; sparse if larger | ENVI caution on incomplete LSU |
| Sensors | Prefer EnMAP/AVIRIS-NG/HyMap-class SNR; treat EMIT 60 m as mixture-first | 2024 commercial GSD lessons |

### 6.3 What **not** to default

- Full-library SAM on 200–500 spectra with no threshold (known garbage mode in literature and project experience).  
- DL model as unsupervised default.  
- Absolute abundance as “assay.”  
- Claiming Cuprite OA without documenting label source and split.  
- Bundling ECOSTRESS library files into Apache redistributable without license review.

### 6.4 QA layers industry would recognize

1. MNF eigenvalue curve + bands retained  
2. Endmember spectra plots + top-3 library matches + scores  
3. SAM angle rule image  
4. MTMF infeasibility mask  
5. Vegetation / water / nodata mask  
6. “Map agreement only” disclaimer when validating against Tetracorder reference rasters  

### 6.5 Success criteria (operational, not vanity OA)

- Endmembers are **spectrally pure and geologically plausible** under expert review.  
- Class maps **spatially coherent** with known alteration patterns on public Cuprite reference maps (qualitative + class-wise IoU), with methods section stating **reference = Swayze/USGS map**, not XRD.  
- On real exploration scenes: deliver **indicator minerals** (e.g. alunite–kaolinite–illite–chlorite–carbonate–FeOx packs) with confidence, not 100-class fantasy.

---

## 7. Sensor-specific operational notes (2020–2026)

| Sensor | GSD (typ.) | Ops note |
|--------|------------|----------|
| **AVIRIS / AVIRIS-NG** | m-scale | Gold standard research; hourglass demos; high SNR |
| **HyMap / SpecTIR AISA** | ~1–5 m | Commercial exploration workhorse airborne |
| **EnMAP** | 30 m | Species mapping possible for **large pure exposures**; mixing limits rare phases (2024 Cuprite study) |
| **PRISMA** | 30 m | Similar class to EnMAP; access/processing maturity varies |
| **EMIT** | ~60 m | Global mineral **products** via feature/expert pipeline; heavy mixing for local exploration |
| **Hyperion (archive)** | 30 m | Educational caution: low SNR → lower map agreement (Wei 2017 Hyperion OA 74.54% vs USGS map) |

---

## 8. Key primary sources (URLs)

### Vendor / software
- NV5 ENVI hyperspectral analytics (hourglass, MNF, PPI, SAM, SFF, MTMF, ACE…):  
  https://www.nv5geospatialsoftware.com/Support/Maintenance-Detail/hyperspectral-analytics-in-envi-target-detection-and-spectral-mapping-methods  
- ENVI SAM & SFF tutorial (Cuprite):  
  https://vis-webcontent.s3.amazonaws.com/tutorials/pdfs/WholePixelHyperspectralAnalysisTutorial.pdf  
- SpecTIR services: https://www.spectir.com/services  
- TSG: https://spectralgeo.com.au/the-spectral-geologist-tsg-software  
- EnMAP-Box: https://www.enmap.org/data_tools/enmapbox/  
- PySptools: https://pysptools.sourceforge.io/  
- Spectral Python: https://www.spectralpython.net/

### Government / science
- USGS Spectral Library: https://www.usgs.gov/labs/spectroscopy-lab/usgs-spectral-library  
- USGS Tetracorder publication entry:  
  https://www.usgs.gov/publications/imaging-spectroscopy-earth-and-planetary-remote-sensing-usgs-tetracorder-and-expert  
- Tetracorder training repo: https://github.com/PSI-edu/spectroscopy-tetracorder  
- EMIT mission: https://earth.jpl.nasa.gov/emit/  
- ECOSTRESS library: https://speclib.jpl.nasa.gov/  
- RELAB/PDS: https://pds-geosciences.wustl.edu/spectrallibrary/default.htm

### Case studies / papers
- EarthDaily EnMAP vs SpecTIR Cuprite (2024):  
  https://earthdaily.com/blog/hyperspectral-imaging-for-mining-enmap-satellite-data-versus-spectir-airborne-data  
- Wei et al. 2017 SMMA Cuprite OA:  
  https://weijing-rs.github.io/publications/Wei_et_al-JARS-2017.pdf  
- Kruse et al. Hyperion/AVIRIS MTMF:  
  https://ntrs.nasa.gov/api/citations/20050192448/downloads/20050192448.pdf  
- Swayze et al. 2014 Cuprite (*Economic Geology*) — essential ground-truth reference  
- Hajaj et al. 2024 review (lithological/mineral alteration HSI): ScienceDirect abstract entry  
  https://www.sciencedirect.com/science/article/abs/pii/S235293852400082X

### Local scrapes
- `docs/research_scrapes/industry/NV5_ENVI_Hyperspectral_Analytics_excerpt.md`  
- `docs/research_scrapes/industry/ENVI_SAM_SFF_Tutorial.txt`  
- `docs/research_scrapes/industry/EarthDaily_EnMAP_vs_SpecTIR_Cuprite_2024.md`  
- `docs/research_scrapes/industry/SpecTIR_services_minerals.md`  
- `docs/research_scrapes/industry/open_source_tools_inventory.md`

---

## 9. Relation to open-ore-mapper internal research

Internal `RESEARCH_SYNTHESIS.md` Lane 8 already describes the professional hourglass (curate → ATM → MNF → endmembers → classify → unmix). This baseline document **confirms that lane against 2020–2026 primary vendor and mission sources**, and adds:

- Explicit **rank order** of methods by ops commonality  
- **Industry-vs-papers** gap  
- **Cuprite OA caveats** with only source-backed numbers  
- **Library license norms**  
- **Unsupervised product defaults** for shipping without ENVI  

Where internal synthesis quotes approximate accuracy bands without a primary table, treat **this file’s §3 tables** as the citable numeric set.

---

## 10. Bottom line

**Industry baseline 2020–2026:** reflectance-ready HSI → **MNF** → **endmembers (PPI/VCA)** → map with **SAM + (SFF or Tetracorder-style features)** and **MTMF** for sub-pixel/rare phases → expert QA.  

**open-ore-mapper should default to an automated hourglass** (VCA + curated USGS + SAM + optional MTMF/SFF), not full-library SAM and not DL-first, and must label Cuprite metrics as map-agreement or field-validated with explicit splits.

---

*End of report.*
