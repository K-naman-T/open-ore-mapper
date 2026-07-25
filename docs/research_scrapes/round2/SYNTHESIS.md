# Round 2 research scrapes — synthesis

**Dir:** `docs/research_scrapes/round2/`  
**Index:** [`index.json`](index.json)  
**Fetched:** 2026-07-26  
**Tools:** `scrapling extract get URL OUTPUT.html --timeout 90 --impersonate chrome` (positional output); `curl -L` for raw GitHub READMEs. Markdownify not installed → HTML + extracted `.txt`.

---

## 1. Retrieval inventory

| Source | File(s) | Bytes (primary HTML/md) | Usable? |
|--------|---------|------------------------:|---------|
| HybridSN ar5iv `1902.06701` | `hybridsn_1902.06701.html` (+`.txt`, abs) | 345 360 | **Yes** — full paper + tables |
| SpectralFormer ar5iv `2107.02988` | `spectralformer_2107.02988.html` (+`.txt`, abs) | 472 352 | **Yes** — full paper + Tables V–X |
| SpectralFormer code | `spectralformer_github.html`, `spectralformer_README.md` | 262 457 / 6 587 | **Yes** |
| HybridSN code | `hybridsn_github.html`, `hybridsn_README.md` | 289 072 / 4 481 | **Yes** |
| SSRN code (Zhong) | `ssrn_github.html`, `ssrn_README.md` | 285 746 / 4 612 | **Yes** (code); paper **not** on ar5iv |
| DeepHyperX | `deephyperx_readme.html`, `deephyperx_README.md` | 301 096 / 8 173 | **Yes** |
| NV5 Whole-Pixel (SAM/SFF) | `nv5_whole_pixel_tutorial.html` | 423 678 | **Yes** — full tutorial body |
| NV5 Spectral Hourglass | `nv5_spectral_hourglass.html` | 33 712 | **No** — docs chrome only (“No results found”) |
| HyDeMiC mineral CNN `2601.17352` | `hydemic_2601.17352.html` | 81 976 | **Yes** |
| SpACNN-LDVAE Cuprite unmix `2311.10701` | `spacnn_ldvae_2311.10701.html` | 327 184 | **Yes** |
| LDVAE unmixing `2203.01327` | `ldvae_unmix_2203.01327.html` | 480 938 | **Yes** |
| HU algorithms review `2507.14260` | `hyperspectral_unmixing_review_2507.14260.html` | 270 459 | **Yes** |
| arXiv API (SSRN / Cuprite CNN) | — | 0 | **Fail** HTTP 429 |

**SpectralFormer arXiv ID verified:** Hong et al., `2107.02988` (not a wrong ID).  
**SSRN (Spectral–Spatial Residual Network, Zhong et al., TGRS 2018):** no public arXiv HTML found; IEEE-only; implementation at https://github.com/zilongzhong/SSRN.

---

## 2. Method names & recommended pipelines (from scrapes)

### A. Classic whole-pixel mineral mapping (ENVI / NV5)

From `nv5_whole_pixel_tutorial.html` (title: *Hyperspectral Analysis: SAM and SFF Tutorial*):

1. **Atmosphere → reflectance** (tutorial data pre-processed with **FLAASH**).
2. **Spectral Angle Mapper (SAM)** against library / ROI / ASCII endmembers  
   - Angle in *n*-D spectral space; illumination/albedo insensitive.  
   - Outputs: **rule images** (per-endmember angle; darker = better match) + **classification map** (min angle class; max-angle threshold in radians).
3. **Spectral Feature Fitting (SFF)** — absorption-feature focused: continuum removal → scale factor → band-wise least squares → **RMS images**.  
   - Requires selecting the narrowest range covering the absorption feature.
4. Scene used in exercises: **AVIRIS Cuprite Hills, southern Nevada** (`CupriteReflectance`, mineral ROIs, SAM/SFF products).

Hourglass wizard page did **not** deliver step text this round. From product naming / prior round chrome only: commercial **Spectral Hourglass** path remains MNF → PPI → n-D visualizer → endmembers → mapping (not extractable from this scrape’s body).

### B. HSI *land-cover* DL baselines (not mineral-native, but standard OA benchmarks)

| Method | Idea | Code |
|--------|------|------|
| **HybridSN** (Roy et al., 2019) | 3D-CNN spectral–spatial → 2D-CNN spatial hierarchy | https://github.com/gokriznastic/HybridSN (Keras); PyTorch ports exist |
| **SSRN** (Zhong et al., 2018) | Sequential **spectral residual blocks** + **spatial residual blocks** on raw 3-D cubes; BN; identity skip | https://github.com/zilongzhong/SSRN |
| **SpectralFormer** (Hong et al., 2021/22) | Transformer backbone with **Group-wise Spectral Embedding (GSE)** + **Cross-layer Adaptive Fusion (CAF)**; pixel- or patch-wise | https://github.com/danfenghong/IEEE_TGRS_SpectralFormer |
| **DeepHyperX** (Audebert et al. toolbox) | Unified PyTorch harness: SVM + many 1D/2D/3D CNNs for fair HSI experiments | https://github.com/nshaud/DeepHyperX |

DeepHyperX datasets auto-download: Indian Pines, PaviaU/C, KSC, Botswana (+ DFC2018 manual).  
Models listed in README: SVM/SGD, baseline NN, Hu 1D-CNN, Hamida/Lee/Chen/Li/Luo/He 3D-CNN variants, etc. (`main.py --model hamida --dataset PaviaU --patch_size 7 …`).

### C. Mineral / Cuprite-oriented open papers (ar5iv this round)

| Paper | Role |
|-------|------|
| **HyDeMiC** (`2601.17352`) | Supervised CNN mineral classifier on AVIRIS-simulated lab spectra (115 classes); noise robustness study; mineral names include Cuprite/Malachite/Chalcopyrite — **not** the Nevada Cuprite cube |
| **LDVAE unmixing** (`2203.01327`) | Dirichlet abundance bottleneck + Normal endmembers; transfer from USGS-library synthetic → Cuprite/Urban/Samson |
| **SpACNN-LDVAE** (`2311.10701`) | Spatial-attention CNN + LDVAE unmixing; Cuprite 512×614×188, ~12 minerals |
| **HU review** (`2507.14260`) | Survey of linear/sparse/nonlinear unmixing; AVIRIS Cuprite as standard HU benchmark |

---

## 3. Concrete numbers (with source files)

### HybridSN — `hybridsn_1902.06701.html` Table II (30% train / 70% test)

Indian Pines **OA** (excerpt):

| Method | IP OA (%) |
|--------|----------:|
| SVM | 85.30 ± 2.8 |
| 2D-CNN | 89.48 ± 0.2 |
| 3D-CNN | 91.10 ± 0.4 |
| M3D-CNN | 95.32 ± 0.1 |
| SSRN | **99.19 ± 0.3** |
| **HybridSN** | **99.75 ± 0.1** |

Also: HybridSN README map figures report IP OA **99.81%**, UP **99.99%**, SA **100%** at 30% train (`hybridsn_README.md`) — single-run maps, slightly above Table II means.

Paper notes ~50 epochs to convergence; spatial window sensitivity in Table IV (25×25 used).

### SSRN — `ssrn_README.md`

- Indian Pines OA **99.44%** with **20%** training samples.  
- Pavia University OA **99.91%** with **10%** training samples.  
- Network sketch: 7×7×200 input → 2 spectral + 2 spatial residual blocks → 5×5×24 → FC to L classes.

### SpectralFormer — `spectralformer_2107.02988.html` Tables VIII–X  
Standard train/test splits (not 30% random). Method order: KNN, RF, SVM, 1-D CNN, 2-D CNN, RNN, miniGCN, ViT, **SF pixel-wise**, **SF patch-wise**.

| Dataset | SF pixel OA | SF patch OA | Best classic backbone OA (2-D CNN) | ViT OA |
|---------|------------:|------------:|-----------------------------------:|-------:|
| Indian Pines | **78.55%** | **81.76%** | 75.89% | 71.86% |
| Pavia University | **87.94%** | **91.07%** | 86.05% | 76.99% |
| Houston 2013 | **86.14%** | **88.01%** | 83.72% | 80.41% |

Abstract claim (same file): ~**10% OA** over plain transformers; ≥**2% OA** over other SOTA backbones; patch-wise ≥**3% OA** over second-best (e.g. vs 78.55% context on IP).  
GSE+CAF “more than **4%**” joint gain in ablation (MathML in HTML).

### SpectralFormer README training recipes — `spectralformer_README.md`

Indian Pines examples:

- ViT: `patches=1 band_patches=1 mode=ViT epoch=1400`  
- Pixel SF: `patches=1 band_patches=3 mode=CAF epoches=290`  
- Patch SF: `patches=7 band_patches=3 mode=CAF epoches=300 weight_decay=5e-3`

### HyDeMiC — `hydemic_2601.17352.html`

- Clean / 1–2% noise: **MCC = 1.00**, **TPR = 1.00**; mean prediction confidence **99.12%**, median **99.61%**.  
- 5% noise: MCC/TPR **0.999**.  
- 10% noise: MCC/TPR **0.92**.  
- Spectra: lab → **224-band AVIRIS-like** simulation; 115 mineral categories.

### ENVI tutorial — `nv5_whole_pixel_tutorial.html`

No published OA% in the tutorial body (procedure-focused). Operational constraints extracted:

- SAM requires **apparent reflectance** matching library units.  
- SAM threshold in **radians**; unclassified if angle > max.  
- SFF needs continuum removal + absorption-window selection; products: scale + RMS images per endmember.

---

## 4. Failures & caveats

1. **NV5 Spectral Hourglass** (`nv5_spectral_hourglass.html`): 200 OK but **no wizard article** — only Docs Center shell / “No results found”.  
2. **SSRN original paper**: not on ar5iv/arXiv; numbers from GitHub README + HybridSN’s comparative table only.  
3. **arXiv API** query for SSRN / Cuprite CNN: **HTTP 429**. Cuprite-related papers found via web search then direct ar5iv GET (worked).  
4. **No pure “Cuprite scene CNN land-cover OA” classic** in this set: open hits are **unmixing** (LDVAE/SpACNN) or **lab mineral CNN** (HyDeMiC), not HybridSN-style maps on AVIRIS Cuprite.  
5. HSI DL OAs (IP/Pavia 99%+) are **dense land-cover benchmarks** with spatial patches — not drop-in for sparse mineral mapping with library spectra.  
6. Intermediate `.txt` files are local HTML→text extracts for search; prefer HTML for structure.

---

## 5. Implications for open-ore-mapper

1. **Keep library SAM / continuum / SFF-style matching** as the interpretable mineral path (NV5 tutorial confirms industry workflow on Cuprite).  
2. **Treat HybridSN / SSRN / SpectralFormer / DeepHyperX** as **classification baselines** if labeled mineral maps exist — not as replacements for spectral libraries.  
3. **SpectralFormer** is the modern transformer baseline (GSE+CAF); code is complete and reproducible.  
4. **DeepHyperX** is the best single harness to re-run classical CNN baselines fairly.  
5. For **subpixel mineral mapping**, prioritize **unmixing** literature (LDVAE, HU review, Cuprite AVIRIS 1997 cube) over Indian Pines OA tables.  
6. Re-fetch Hourglass with a real browser or archived ENVI PDF if MNF/PPI defaults are required.

---

## 6. Code links (verified this round)

| Resource | URL |
|----------|-----|
| HybridSN paper | https://ar5iv.labs.arxiv.org/html/1902.06701 |
| HybridSN code | https://github.com/gokriznastic/HybridSN |
| SpectralFormer paper | https://ar5iv.labs.arxiv.org/html/2107.02988 |
| SpectralFormer code | https://github.com/danfenghong/IEEE_TGRS_SpectralFormer |
| SSRN code | https://github.com/zilongzhong/SSRN |
| DeepHyperX | https://github.com/nshaud/DeepHyperX |
| NV5 SAM/SFF tutorial | https://www.nv5geospatialsoftware.com/docs/Whole-Pixel_Hyperspectral_Analysis_Tutorial.html |
| HyDeMiC | https://ar5iv.labs.arxiv.org/html/2601.17352 |
| LDVAE unmixing | https://ar5iv.labs.arxiv.org/html/2203.01327 |
| SpACNN-LDVAE | https://ar5iv.labs.arxiv.org/html/2311.10701 |
| HU review | https://ar5iv.labs.arxiv.org/html/2507.14260 |
