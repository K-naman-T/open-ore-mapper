# HSI deep-learning community baselines for mineral mapping (implement research)

**Date:** 2026-07-26  
**Workspace:** `/home/knamant/open-ore-mapper`  
**Compute target:** RTX 4060 Laptop **8 GB** (chomp)  
**Eval protocol (non-negotiable):** spatial-block multi-seed (`docs/RESEARCH_PROTOCOL.md`); **no** random-pixel paper OA as win condition.  
**Our ceiling so far:** full-scene classical fuse OA ≈ **0.71**; spatial multi-seed RF-MNF OA ≈ **0.79** (`docs/BEST_NUMBERS.md`).  
**Win gate (ML_RESEARCH_DIRECTION):** mean OA(ML) > best classical spatial + 0.02 **and** kaolinite recall not degraded.

This note is a **literature inventory + ranked implement list**.  
**Do not invent metrics.** Paper OA numbers below are **quoted claims under each paper’s own split**; they are **not** transferable to Cuprite Tetracorder spatial blocks.

Related local notes: `docs/ML_RESEARCH_DIRECTION.md`, scrapes in `docs/research_scrapes/ml/`, `docs/research_scrapes/round2/`.

---

## 0. Executive ranked implement list (RTX 4060 8 GB + our spatial protocol)

| Priority | Model | Why for us | Open code | Est. fit on 8 GB |
|----------|-------|------------|-----------|------------------|
| **P0** | **1D-CNN (Hu-style / DeepHyperX 1D)** | Spectral absorption = mineral physics; light; fair RF competitor; no patch leakage ambiguity | DeepHyperX / easy reimpl | **Excellent** (batch 128–512) |
| **P0** | **HybridSN (3D→2D)** | *De facto* community hybrid CNN baseline; many reimpls; PCA/MNF-first patches | [gokriznastic/HybridSN](https://github.com/gokriznastic/HybridSN) | **Good** if bands reduced (MNF 15–30), patch ≤11–15 |
| **P0** | **SpectralFormer (pixel + patch)** | Spectral-sequence transformer; official PyTorch; pixel-wise mode fits sparse labels | [danfenghong/IEEE_TGRS_SpectralFormer](https://github.com/danfenghong/IEEE_TGRS_SpectralFormer) | **Good** pixel-wise; patch 7×7 OK |
| **P1** | **SSRN** | Classic residual 3D spectral→spatial; still default comparison in surveys | [zilongzhong/SSRN](https://github.com/zilongzhong/SSRN) (TF/Keras; port to PT) | **Good** with small patches + band reduction |
| **P1** | **SSFTT** | Lightweight CNN + **single-layer** transformer; common 2022+ baseline | [zgr6010/HSI_SSFTT](https://github.com/zgr6010/HSI_SSFTT) | **Good** |
| **P1** | **FreeNet (FPGA framework)** | Patch-free whole-map FCN; conceptually closer to “map the scene” | [Z-Zheng/FreeNet](https://github.com/Z-Zheng/FreeNet) | **Risky on 8 GB** for full 750×614×219; needs crop/tile + β compression |
| **P2** | **SS-Mamba / MambaHSI** | New SOTA trend; linear complexity claims | [SS-Mamba](https://github.com/mengduanjinghua/Spectral-spatial-Mamba-for-HSIC), [MambaHSI](https://github.com/li-yapeng/MambaHSI) | **Mixed** (CUDA/mamba deps; image-level MambaHSI heavy) |
| **P2** | **Few-shot / metric (DFSL, mineral metric nets)** | Label-sparse minerals; one-class / rare classes | [gokling1219/DFSL](https://github.com/gokling1219/DFSL) | **Good** if embeddings stay small |
| **P2** | **Semi-supervised pseudo-label (IPG / progressive PL)** | Most Cuprite pixels unlabeled (ignore 255) | papers mostly; glue to our MTMF conf | **Good** if teacher is classical/RF |

**Do not implement first for OA hunting:** heavy ViT-only on full bands, pure 3D-CNN deep stacks on 219 bands without reduction, image-level Mamba without tiling.

**Already done (mandatory baseline):** RF on reflectance / MNF / MTMF features under spatial multi-seed — **keep as bar**.

---

## 1. Critical caveat: random-pixel splits inflate OA

Almost all HSI land-cover papers train/test by **randomly sampling labeled pixels** (or fixed % per class) **inside the same scene**. Adjacent pixels share texture and are near-duplicates → OA 95–99% is common and **does not measure spatial generalization**.

| Split style | Typical paper practice | Our protocol | Trust paper OA? |
|-------------|------------------------|--------------|-----------------|
| Random % of labeled pixels | HybridSN 30/70; many CNN papers 10%/5% per class | **Forbidden** as primary | **No** for mineral mapping claims |
| Fixed sample counts / official train ROIs | SpectralFormer IP/Houston tables; FreeNet Houston contest split | Better, still same-scene | **Weak** external validity |
| Spatial block / geographic hold-out | Rare in classic HSI CNN papers | **Required** | Only if re-run under our protocol |

**Flag:** Any method that “only looks good under random pixel splits” is **every standard CNN/transformer HSI classifier** until re-evaluated spatially. HybridSN’s near-100% OA tables are the textbook example.

Spatial autocorrelation literature (non-HSI but same principle): block CV vs random points can collapse inflated scores (e.g. Karasiak et al. 2022 *Machine Learning*; Kattenborn et al. 2022 on autocorrelated samples).

For **open-ore-mapper**, re-implement baselines as:

1. Extract train-block labels only (same grid as `spatial_split_eval.py`).  
2. Fit PCA/MNF **on train blocks only**.  
3. Score **test-block labeled pixels only**.  
4. Multi-seed (42, 7, 99, 123, 2024).  
5. Report mean±std OA / κ / per-class recall (kaolinite).

---

## 2. Canonical supervised models (2015–2026 community baselines)

### 2.1 Summary table

| Model | Year | Venue / ID | Input | Open code | Typical datasets | Paper split (quoted) | Approx params / VRAM notes |
|-------|------|------------|-------|-----------|------------------|----------------------|----------------------------|
| **1D-CNN** | 2015 | Hu et al., *J. Sensors* [DOI 10.1155/2015.258619](https://doi.org/10.1155/2015/258619) | 1D spectrum | reimpl / DeepHyperX | IP, etc. | random/fixed labeled pixels | ~10k–200k; **≪1 GB** |
| **3D-CNN** | 2016 | Chen et al., *IEEE TGRS* | patch cube | many reimpls; DeepHyperX | IP, Pavia, Salinas | random % | depends on cube; reduce bands |
| **SSRN** | 2018 | Zhong et al., *IEEE TGRS* 56(2):847–858 | 3D patch (e.g. 7×7×B) | [zilongzhong/SSRN](https://github.com/zilongzhong/SSRN) | IP, Pavia, KSC | small % train common | residual 3D; **medium** |
| **HybridSN** | 2019/20 | Roy et al., arXiv:[1902.06701](https://arxiv.org/abs/1902.06701); *IEEE GRSL* | 25×25×B_PCA then 3D+2D | [gokriznastic/HybridSN](https://github.com/gokriznastic/HybridSN) | IP, PaviaU, Salinas | **30% train random** | **~5.12 M** (IP, Table I); GTX 1060-class OK |
| **FreeNet / FPGA** | 2020 | Zheng et al., arXiv:[2011.05670](https://arxiv.org/abs/2011.05670); *IEEE TGRS* | **whole image** FCN | [Z-Zheng/FreeNet](https://github.com/Z-Zheng/FreeNet) | PaviaU, Salinas, Houston | 200/class or contest split | β channel compression; **needs full-image activation memory** |
| **SpectralFormer** | 2021 | Hong et al., arXiv:[2107.02988](https://arxiv.org/abs/2107.02988); *IEEE TGRS* | pixel **or** patch (7×7) | [danfenghong/IEEE_TGRS_SpectralFormer](https://github.com/danfenghong/IEEE_TGRS_SpectralFormer) | IP, PaviaU, Houston2013 | fixed sample tables (not pure %) | 5 encoder blocks, d=64; GTX 1080 Ti class |
| **SSFTT** | 2022 | Sun et al., *IEEE TGRS* 60 | patch; 3D/2D CNN → tokens → 1-layer Transformer | [zgr6010/HSI_SSFTT](https://github.com/zgr6010/HSI_SSFTT) | IP, Pavia, Salinas, etc. | typical random % papers | **lightweight** vs deep ViT |
| **SS-Mamba** | 2024 | Huang et al., arXiv:[2404.18401](https://arxiv.org/abs/2404.18401); *Remote Sens.* 16, 2449 | patch tokens spatial+spectral | [mengduanjinghua/Spectral-spatial-Mamba-for-HSIC](https://github.com/mengduanjinghua/Spectral-spatial-Mamba-for-HSIC) | standard HSI | standard | linear SSM complexity claim |
| **MambaHSI** | 2024/25 | Li et al., arXiv:[2501.04944](https://arxiv.org/abs/2501.04944); *IEEE TGRS* | **image-level** spatial-spectral Mamba | [li-yapeng/MambaHSI](https://github.com/li-yapeng/MambaHSI) | four HSI datasets | paper-specific | first image-level Mamba-HSI claim; **VRAM-heavy** |
| **Survey zoo** | 2024 | Ahmad et al., arXiv:[2404.14955](https://arxiv.org/abs/2404.14955) | multi | [mahmad00/…Survey-2024](https://github.com/mahmad00/Conventional-to-Transformer-for-Hyperspectral-Image-Classification-Survey-2024) | multi | mixed | code catalog, not one model |

**Toolboxes (prefer over one-off rewrites):**

| Toolbox | URL | Notes |
|---------|-----|-------|
| **DeepHyperX** | https://github.com/nshaud/DeepHyperX | PyTorch zoo: SVM, NN, 1D/2D/3D CNN, hybrids; patch size configurable; Visdom |
| **Hyperspectral-Classification** | https://github.com/eecn/Hyperspectral-Classification | Older PT zoo; HybridSN paper compares against it |
| **Candy-CY multi-model** | https://github.com/Candy-CY/Hyperspectral-Image-Classification-Models | HybridSN, SSFTT, etc. descriptions |
| **DeepHS Benchmark** | https://github.com/cogsys-tuebingen/hsi_benchmark | Broader HSI apps + HybridSN among 23 models |

---

### 2.2 Per-model detail (claims with caveats)

#### A. 1D-CNN (Hu et al. 2015) — **P0**

- **Paper:** Hu, Huang, Wei, Zhang, Li — “Deep Convolutional Neural Networks for Hyperspectral Image Classification,” *Journal of Sensors*, 2015, Article ID 258619. DOI: [10.1155/2015/258619](https://doi.org/10.1155/2015/258619).  
- **Idea:** Treat spectrum as 1D signal; conv along wavelength. No spatial context.  
- **Input:** spectrum length B (or CR/MNF reduced).  
- **Why minerals:** Alteration minerals are **spectral-feature** problems (kaolinite doublet, alunite, etc.). Spatial CNN can over-smooth sparse outcrops.  
- **Code:** No single canonical 2015 repo; implement from DeepHyperX `nn` / `hamida` / 1D modules, or ~50 lines PyTorch.  
- **Params/VRAM:** Tiny. Trivial on 8 GB.  
- **Datasets in lineage:** Indian Pines-style land-cover (not Cuprite).  
- **Split caveat:** Original and reimpls use random labeled pixels.  
- **Implement note:** Match RF feature sets (raw, CR-SWIR, MNF) for apples-to-apples.

#### B. 3D-CNN (Chen et al. 2016 lineage) — **P1 (behind HybridSN)**

- **Paper:** Chen, Jiang, Li, Jia, Ghamisi — “Deep Feature Extraction and Classification of Hyperspectral Images Based on Convolutional Neural Networks,” *IEEE TGRS*, 2016.  
- **Idea:** Joint spectral-spatial 3D kernels on patches.  
- **Input:** S×S×B cubes.  
- **Caveat:** Full 3D on B=219 is expensive; always PCA/MNF first for us.  
- **Code:** DeepHyperX 3D models; many forks.  
- **Flag:** Same random-split inflation as HybridSN family.

#### C. SSRN — **P1**

- **Paper:** Zhong, Li, Luo, Chapman — “Spectral–Spatial Residual Network for Hyperspectral Image Classification: A 3-D Deep Learning Framework,” *IEEE TGRS*, vol. 56, no. 2, pp. 847–858, 2018.  
- **Code:** https://github.com/zilongzhong/SSRN (TensorFlow/Keras official).  
- **Input:** raw 3D cubes (example architecture discussion uses ~7×7×200). Spectral residual blocks (1×1×m kernels) then spatial residual blocks.  
- **Claim (abstract):** end-to-end residual framework alleviates declining accuracy of deep models; supervised.  
- **Datasets:** standard land-cover HSI (IP etc. in paper experiments).  
- **Params:** moderate residual 3D — port to PyTorch for our stack; watch memory with B≈200.  
- **Cuprite:** Not a mineral paper.

#### D. HybridSN — **P0**

- **Paper:** Roy, Krishna, Dubey, Chaudhuri — “HybridSN: Exploring 3D-2D CNN Feature Hierarchy for Hyperspectral Image Classification,” arXiv:[1902.06701](https://arxiv.org/abs/1902.06701) (2019); *IEEE GRSL* 2020.  
- **Code:** https://github.com/gokriznastic/HybridSN (Keras; MIT).  
- **Input:** PCA to B=30 (IP) or 15 (UP/SA); **25×25** spatial window; three 3D conv → reshape → 2D conv → dense.  
- **Params (quoted, Table I IP):** **5,122,176** trainable parameters.  
- **Hardware in paper:** Acer Predator, **GTX 1060**, 16 GB RAM — similar class to 4060 laptop for small batches.  
- **Split (quoted):** “**30% and 70%** of the data are randomly divided into training and testing” — **random-pixel protocol**.  
- **Claimed OA (Table II, their protocol, OA%):** HybridSN IP **99.75±0.1**, UP **99.98**, SA high 99s — **do not compare to our 0.79**. Table V with 10% train still reports 98+% on IP for HybridSN.  
- **Train time (Table III, their hardware):** IP ~14 min train / ~5 s test.  
- **Mineral mapping:** no Cuprite.  
- **Our port recipe:** MNF 20–30 (train-fit) instead of full-scene PCA; patch 7–11 first for VRAM; class weights for rare minerals; spatial multi-seed only.

#### E. FreeNet / FPGA — **P1 (map-style), VRAM caution**

- **Paper:** Zheng, Zhong, Ma, Zhang — “FPGA: Fast Patch-Free Global Learning Framework for Fully End-to-End Hyperspectral Image Classification,” arXiv:[2011.05670](https://arxiv.org/abs/2011.05670); *IEEE TGRS* 2020.  
- **Code:** https://github.com/Z-Zheng/FreeNet  
- **Input:** **entire image** once (FCN encoder–decoder + spectral attention SE-style + lateral SSF). GS² stratified sampling for sparse labels.  
- **Claim:** faster inference than overlapping patches; competitive/superior OA vs patch CNNs on PaviaU / Salinas / Houston under paper settings (e.g. FreeNet Pavia OA reported near saturation ~99.8% with 200 train/class — **again not our split**).  
- **Hardware in paper:** NVIDIA Tesla **P100 16 GB**.  
- **8 GB issue:** Activations for Cuprite 750×614×219 full forward can exceed 8 GB even if params are modest — use β compression factor, tile with overlap, or reduce bands before FreeNet.  
- **Why interesting for minerals:** whole-map consistency; GS² sampling is closer to sparse labeled pixels than dense crop patches.

#### F. SpectralFormer — **P0**

- **Paper:** Hong, Han, Yao, Gao, Zhang, Plaza, Chanussot — “SpectralFormer: Rethinking Hyperspectral Image Classification with Transformers,” arXiv:[2107.02988](https://arxiv.org/abs/2107.02988); *IEEE TGRS* 2021.  
- **Code:** https://github.com/danfenghong/IEEE_TGRS_SpectralFormer  
- **Modules:** Group-wise Spectral Embedding (GSE) + Cross-layer Adaptive Fusion (CAF); ViT-style encoders; **pixel-wise or patch-wise** (patch 7×7 unfolded per band).  
- **Implementation defaults (paper §III-B):** 5 encoder blocks, embedding 64, 4-head SA, Adam, batch 64; trained on GTX **1080 Ti 11 GB**.  
- **Datasets:** Indian Pines, Pavia University, Houston2013 (fixed train/test sample tables).  
- **Quoted OA (IP, Table VIII, their fixed split):** ViT pixel **71.86%**; SpectralFormer pixel **78.55%**; patch **81.76%**. Pavia patch OA **91.07%**; Houston patch **88.01%**.  
  - *Caveat:* Still same-scene labeled pixels; not spatial blocks. Numbers are **far more honest** than HybridSN’s 99% random-split regime but still not our protocol.  
- **Mineral fit:** Spectral grouping is well-motivated for absorption features; pixel-wise mode avoids forcing large homogeneous patches on sparse alteration.

#### G. SSFTT — **P1**

- **Paper:** Sun, Zhao, Zheng, Wu — “Spectral–Spatial Feature Tokenization Transformer for Hyperspectral Image Classification,” *IEEE TGRS*, vol. 60, 2022 (often cited without free arXiv preprint; IEEE paywall).  
- **Code:** https://github.com/zgr6010/HSI_SSFTT  
- **Idea:** 3D+2D CNN shallow features → Gaussian-weighted tokenization → **single-layer** transformer (lighter than full ViT).  
- **Role in community:** Default transformer baseline in many 2023–2025 comparisons (alongside SpectralFormer).  
- **Split:** Standard random % in original and followers — **flag**.  
- **VRAM:** Generally friendlier than deep SpectralFormer stacks.

#### H. SS-Mamba & MambaHSI — **P2**

| Variant | Paper | Code | Input | Notes |
|---------|-------|------|-------|-------|
| **SS-Mamba** | Huang, Chen, He — arXiv:[2404.18401](https://arxiv.org/abs/2404.18401); *Remote Sens.* 2024, 16, 2449 | [Spectral-spatial-Mamba-for-HSIC](https://github.com/mengduanjinghua/Spectral-spatial-Mamba-for-HSIC) | patch spectral+spatial tokens + Mamba blocks | “preliminary attempt”; competitive with SOTA claim under paper eval |
| **MambaHSI** | Li et al. — arXiv:[2501.04944](https://arxiv.org/abs/2501.04944); *IEEE TGRS* | [li-yapeng/MambaHSI](https://github.com/li-yapeng/MambaHSI); also [MambaHSI_Plus](https://github.com/RockAilab/MambaHSI_Plus) | **whole-image** spatial Mamba + spectral Mamba + fusion | “first image-level HSI classification model based on Mamba” (paper claim) |
| Others | HS-Mamba, 3DSS-Mamba, structure-aware Mamba (2025 MDPI) | scattered | mixed | research-track, not community baseline yet |

- **Deps risk:** `mamba-ssm` / selective scan CUDA builds can be painful on laptop drivers.  
- **8 GB:** Prefer **patch SS-Mamba** over full-image MambaHSI for Cuprite.  
- **Split flag:** Same as other modern HSI classifiers.

#### I. Metric learning / few-shot for minerals — **P2 (rare classes)**

| Method | Link | Relevance |
|--------|------|-----------|
| **DFSL** (deep few-shot HSI) | Paper lineage TGRS 2018-ish; code [gokling1219/DFSL](https://github.com/gokling1219/DFSL) | Meta-learning with few labels/class — rare minerals |
| **Metric learning mineral detection** | Jabłońska, Zięba, Tanajewski — “Metric learning networks for accurate mineral detection…,” *Expert Systems with Applications*, 2025 (ScienceDirect [S0957417425043076](https://www.sciencedirect.com/science/article/pii/S0957417425043076)) | **One-class mineral** detection; **Cuprite** discussed as hydrothermal alteration benchmark; augmentation + metric nets |
| Cross-domain few-shot HSI | many 2024–2026 arXiv (e.g. spectral-spatial SSL few-shot [2505.12482](https://arxiv.org/abs/2505.12482)) | Transfer across sensors/scenes — future, not first baseline |

**Caveat:** Jabłońska et al. is **one-class / detection**, not multi-class Tetracorder fd-max. Do not paste their accuracy numbers onto our multi-class OA scoreboard without reading their task definition.

---

## 3. Mineral-specific / Cuprite / alteration literature

HSI **land-cover** baselines ≠ mineral mapping. Operational mineral RS still leans classical:

| Theme | Notes for open-ore-mapper |
|-------|---------------------------|
| **Tetracorder / USGS Cuprite** | Expert spectral system; our GT is Tetracorder fd-max hard labels → optimizing DL to GT can overfit an algorithm’s quirks (protocol § label circularity) |
| **Cuprite as unmixing benchmark** | Often 12 minerals, abundance maps — different task than multi-class hard maps |
| **Metric learning @ Cuprite (2025)** | Jabłońska et al. — see §2.2-I |
| **CNN alteration mapping** | e.g. multi-sensor CNN for alteration north of Broken Hill (Landsat/ASTER; arXiv:[2502.18533](https://arxiv.org/html/2502.18533v1)) — **not AVIRIS HSI 200-band**, still shows CNN used in exploration for **zones**, not pure library matching |
| **Drone / lab mineral HSI + DL** | Okada et al. 2020 *Minerals* (grain size + mineral type; lab/process setting) — different scale |
| **EnMAP / fused composites @ Cuprite** | Industry case studies (EarthDaily etc.) — classical + ML fusion narratives; not open reimpl baselines |

**What tends to work when labels are sparse / Tetracorder-like (synthesis, not a single paper law):**

1. **Strong spectral front-end** (CR, band subsets SWIR 2000–2450 nm, MNF) before any net.  
2. **Light spectral models** (1D-CNN, SpectralFormer pixel) over huge spatial patches.  
3. **Class-balanced / weighted loss** — kaolinite/alunite vs dominant muscovite.  
4. **Semi-supervised / pseudo-labels** from high-confidence classical scores on unlabeled pixels (ignore 255).  
5. **Metric / one-class** for rare minerals rather than forcing softmax on 8+ classes with tiny support.  
6. **Distrust** 90%+ OA Cuprite CNN claims that used ROI pure-pixel random splits or different GT taxonomies.

---

## 4. Semi-supervised & few-shot (sparse labels)

Most of our scene is **unlabeled** (fd < 20 → ignore 255). Supervised-only nets waste that.

| Family | Example | Paper / code | Fit |
|--------|---------|--------------|-----|
| Progressive pseudo-label | Zhao et al. 2024 *Remote Sens.* progressive PL selection (spatial–spectral consistency) | MDPI [rs16101747](https://www.mdpi.com/2072-4292/16/10/1747) | High for Cuprite |
| SAM-based iterative PL (IPG) | Zhao et al. 2024 Frontiers Plant Sci. — IPG with Segment Anything for HSI SSL | Frontiers article | Interesting glue to spatial regions; **not** spectral SAM |
| Classic semi-sup CNN | Wu & Prasad 2018 — pseudo-labels for HSI | PubMed 29990156 | Older baseline idea |
| Few-shot / DFSL | [gokling1219/DFSL](https://github.com/gokling1219/DFSL) | GitHub | Rare classes |
| Contrastive pretrain → fine-tune | many 2023–2025 | scattered | Phase C stretch |

**Implement suggestion (Phase C):**  
Teacher = RF-MNF or MTMF confidence on unlabeled train-region pixels → hard/soft pseudo-labels → student = 1D-CNN or SpectralFormer → evaluate **only** on spatial test-block true Tetracorder labels.

---

## 5. VRAM & engineering budget (RTX 4060 8 GB)

Assumptions: mixed precision optional; PyTorch; Cuprite 750×614×219 float32 cube ~400 MB raw.

| Setup | Recommended | Avoid on 8 GB |
|-------|-------------|----------------|
| 1D spectrum B≤219 | batch 256–512 | — |
| Patch 7×7×30 MNF | batch 32–64 HybridSN/SSRN | 25×25×219 raw 3D |
| SpectralFormer pixel | batch 64–128 | huge embedding + full-band without care |
| FreeNet whole image | tile 256–384 + β≪1 + band reduce | single-shot full 219-band FCN |
| MambaHSI image-level | try after tiling or skip | naive full-res |
| Freezing / AMP | always for 3D | full fp32 large 3D |

**Band reduction policy (aligned with protocol):** MNF or PCA fit **train blocks only** → 15–30 components for 3D/hybrid; keep full or SWIR CR for 1D-CNN/SpectralFormer experiments as ablations.

---

## 6. Implement roadmap (ordered)

### Phase P0 — must have community bars (1–2 weeks engineering)

1. **Data adapter:** wrap `spatial_eval` splits → tensors + ignore_index 255.  
2. **1D-CNN** (DeepHyperX-style) on: reflectance | CR-SWIR | MNF.  
3. **HybridSN** (MNF 30, patch 7 then 11) multi-seed.  
4. **SpectralFormer** pixel-wise multi-seed; optional patch 7.  
5. Compare to RF-MNF 0.79 ± 0.04 under **identical seeds**.

### Phase P1 — if P0 loses or ties RF

6. **SSFTT** and/or **SSRN** (PyTorch ports).  
7. **FreeNet** tiled + GS²-like sampling for unlabeled-aware training.  
8. Class-weighted CE + rare-class focal loss ablations (kaolinite recall).

### Phase P2 — research stretch

9. Pseudo-label SSL from MTMF/RF.  
10. DFSL / metric learning for minority minerals.  
11. Patch SS-Mamba if deps install cleanly.  
12. Skip image-level MambaHSI unless FreeNet path already works.

### Explicit non-goals

- Chasing paper OA on Indian Pines.  
- Random 30% pixel train “validation” for product claims.  
- Full-scene endmember-leaked DL OA as success.

---

## 7. Methods that “only look good under random pixel splits”

**Hard flag — re-run required before any trust:**

| Method | Why OA looks great in papers | Expect under spatial blocks |
|--------|------------------------------|-----------------------------|
| HybridSN, deep 3D-CNN, SSRN (standard configs) | 10–30% random train; spatial leak via neighbors in train | Large drop; may lose to RF |
| SSFTT / many Transformers | same | same |
| FreeNet high-OA tables | still same-scene labeled pixels; dense urban/ag classes | Unknown; better spatial context may help **or** oversmooth sparse minerals |
| SpectralFormer | better fixed splits but same scene | Moderate drop expected; spectral bias may retain more |
| Mamba-HSI SOTA tables | same community protocol | Unknown; do not cite as Cuprite ready |
| Any method reporting OA>0.95 on IP with >5% random train | near-duplicate leakage | Treat as **invalid** for our scoreboard |

**Not automatically invalid:** RF, 1D spectral models, classical SAM/MTMF — but still must use spatial protocol (we already do).

---

## 8. Suggested citation anchors (for README / paper later)

```text
Hu et al. 2015 J. Sensors — 1D-CNN HSI
Chen et al. 2016 TGRS — 3D CNN HSI
Zhong et al. 2018 TGRS — SSRN
Roy et al. 2020 GRSL / arXiv:1902.06701 — HybridSN
Zheng et al. 2020 TGRS / arXiv:2011.05670 — FreeNet/FPGA
Hong et al. 2021 TGRS / arXiv:2107.02988 — SpectralFormer
Sun et al. 2022 TGRS — SSFTT
Huang et al. 2024 Remote Sens. / arXiv:2404.18401 — SS-Mamba
Li et al. 2024/25 TGRS / arXiv:2501.04944 — MambaHSI
Ahmad et al. 2024 arXiv:2404.14955 — conventional→transformer survey
Jabłońska et al. 2025 ESWA — metric learning mineral detection (Cuprite context)
```

---

## 9. Local scrape / code references

| Resource | Path / URL |
|----------|------------|
| This report | `docs/research_scrapes/HSI_DL_BASELINES_IMPLEMENT_2026.md` |
| HybridSN HTML scrape | `docs/research_scrapes/round2/hybridsn_1902.06701.html` |
| SpectralFormer scrape | `docs/research_scrapes/round2/spectralformer_2107.02988.html` |
| SpectralFormer GH scrape | `docs/research_scrapes/round2/spectralformer_github.html` |
| DeepHyperX readme scrape | `docs/research_scrapes/round2/deephyperx_readme.html` |
| Prior ML direction | `docs/ML_RESEARCH_DIRECTION.md` |
| Protocol | `docs/RESEARCH_PROTOCOL.md` |
| Best numbers | `docs/BEST_NUMBERS.md` |

Optional future scrapes (not bulk-downloaded here): FreeNet ar5iv `2011.05670`, SS-Mamba `2404.18401`, SSFTT IEEE HTML if available.

---

## 10. Bottom line

1. **Community baselines worth implementing:** 1D-CNN, HybridSN, SpectralFormer, then SSRN/SSFTT, optionally FreeNet.  
2. **Paper OAs are not transferable** — especially HybridSN’s ~99% under 30% random train.  
3. **RF-MNF multi-seed ~0.79** is the real bar; only beat it under **spatial** multi-seed.  
4. **8 GB path:** reduce bands, small patches or pixel-wise spectral models first; whole-image FreeNet/MambaHSI later with tiling.  
5. **Mineral sparsity:** prioritize spectral models + semi-sup/metric for rare classes over giant spatial transformers.

*Report generated for open-ore-mapper research pipeline; all numeric paper claims are citations of published tables/abstracts under foreign evaluation protocols, not measurements on Cuprite Tetracorder spatial blocks.*
