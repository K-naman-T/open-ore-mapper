# Round-2 deep research — master index (2026-07-26)

Parallel agents: industry baseline · HSI DL papers · Scrapling bulk fetch · open implementations.

## Deliverables

| Report | Path |
|--------|------|
| Industry / ops mineral baseline | [`INDUSTRY_MINERAL_BASELINE_2026.md`](INDUSTRY_MINERAL_BASELINE_2026.md) |
| HSI DL implement ranking | [`HSI_DL_BASELINES_IMPLEMENT_2026.md`](HSI_DL_BASELINES_IMPLEMENT_2026.md) |
| Open code to wrap | [`OPEN_IMPLEMENTATIONS_2026.md`](OPEN_IMPLEMENTATIONS_2026.md) |
| Round-2 scrapes + synthesis | [`round2/SYNTHESIS.md`](round2/SYNTHESIS.md) · [`round2/index.json`](round2/index.json) |
| Industry HTML snippets | [`industry/`](industry/) |
| Prior ML direction | [`../ML_RESEARCH_DIRECTION.md`](../ML_RESEARCH_DIRECTION.md) |
| **Adversarial consensus (binding claims)** | [`ADVERSARIAL_CONSENSUS.md`](ADVERSARIAL_CONSENSUS.md) |
| Adversary briefs | `ADVERSARIAL_METRICS_SKEPTIC.md`, `ADVERSARIAL_PRODUCT_REALIST.md`, `ADVERSARIAL_ML_RESEARCHER.md`, `ADVERSARIAL_CLASSICAL_RS.md` |

## Executive synthesis (no hedging)

### Two baselines, not one

| Track | Community standard | Our status | Product role |
|-------|-------------------|------------|--------------|
| **Unsupervised mineral ops** | ENVI Hourglass: reflectance → MNF → endmembers → **SAM / SFF / MTMF**; Tetracorder-class feature systems (EMIT minerals lineage) | fuse / MTMF / CR / MNF largely done | **Default ship** |
| **Supervised HSI classification** | RF/SVM floor → **1D-CNN → HybridSN → SpectralFormer** (+ SSRN/SSFTT); toolboxes DeepHyperX | RF-MNF multi-seed **~0.79** done; DL **not** yet | Optional labeled mode / research OA |

Industry does **not** ship DL-first for unlabeled exploration. Academia **does** treat HybridSN / SpectralFormer as supervised baselines — implement them under **our spatial multi-seed**, ignore paper 99% random-split OA.

### Implement order (community-backed)

| Pri | What | Why | Code / notes |
|----:|------|-----|----------------|
| **1** | LightGBM/XGB on same features as RF | Tabular SOTA; MIT/Apache; one evening | extend `ml_rf` |
| **2** | **1D-CNN** (Hu et al. style) | Mineral physics is spectral; trivial 8 GB | reimpl (DeepHyperX is GPLv3 — don’t vendor) |
| **3** | **HybridSN** (3D→2D patches) | De facto spectral–spatial CNN baseline | [HybridSN-pytorch](https://github.com/purbayankar/HybridSN-pytorch) MIT-ish; MNF→30, patch 7 |
| **4** | **SpectralFormer** (pixel CAF → patch) | Canonical transformer HSI baseline | [official](https://github.com/danfenghong/IEEE_TGRS_SpectralFormer) **GPLv3** — research plugin, not core merge |
| **5** | Semi-sup pseudo-label from MTMF/CR | Cuprite mostly unlabeled | after P0 nets |
| **6** | SSRN / SSFTT / FreeNet / Mamba | Only if 1–4 fail bar | see DL report |

**Bar to beat:** RF-MNF spatial multi-seed OA **~0.79** (+0.02 and kaolinite R not worse).

### Hard flags from literature

- HybridSN/SSRN README OA ~99% on Indian Pines under **% random train** — **not** transferable to our protocol.
- SpectralFormer IP patch OA ~82% on fixed split — still not spatial blocks.
- No clean open HybridSN-style dense multi-class OA table on **AVIRIS Cuprite Tetracorder** in this scrape set; Cuprite open papers skew **unmixing** (LDVAE) or lab mineral CNN.
- Paper mineral OA vs USGS map (e.g. Wei 2017 AVIRIS 94.8%) is **map-to-map agreement**, different from our fd-max hard labels + spatial hold-out.

### Product recommendation (unchanged by DL literature)

1. **Unsupervised default:** hourglass-style fuse / MTMF + curated library (not full-library SAM).  
2. **Supervised mode (when labels):** RF → LightGBM → 1D-CNN → HybridSN → SpectralFormer, all on `spatial_split_eval` multi-seed.  
3. **Do not** default product to GPL DeepHyperX/SpectralFormer inside MIT/Apache core without license review.

## Scraped paper artifacts (round2)

| Artifact | Status |
|----------|--------|
| HybridSN ar5iv 1902.06701 | full HTML + tables |
| SpectralFormer ar5iv 2107.02988 | full HTML + tables |
| DeepHyperX / HybridSN / SpectralFormer / SSRN READMEs | fetched |
| NV5 SAM/SFF Cuprite tutorial | usable |
| NV5 Hourglass body | **failed** (docs shell) |
| Cuprite unmix (LDVAE, SpACNN) + HU review | fetched |

## Next engineering (if green-lit)

```text
1. scripts/ml_spatial_lgbm_baseline.py   # same seeds/features as RF
2. src/open_ore_mapper/ml_cnn1d.py       # Hu-style, spatial protocol
3. scripts/ml_spatial_hybridsn.py        # patch train, multi-seed
4. research plugin: SpectralFormer on chomp
5. Scoreboard append to BEST_NUMBERS.md
```
