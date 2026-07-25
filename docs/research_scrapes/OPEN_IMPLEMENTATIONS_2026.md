# Open implementations for supervised mineral classification (2026-07-26)

Research scrape for **open-ore-mapper** Phase B / thin-wrap candidates.  
Target protocol: `spatial_eval.make_spatial_split` → train on train-block pure GT → full-scene predict → `evaluate_maps` on test blocks only.  
Hardware constraint: **RTX 4060 Laptop 8 GB** (chomp). Cube shape: **(H, W, B)** e.g. Cuprite 750×614×219.

Related internal docs: `docs/ML_RESEARCH_DIRECTION.md`, `docs/RESEARCH_PROTOCOL.md`, `src/open_ore_mapper/ml_rf.py`, `src/open_ore_mapper/spatial_eval.py`.

**Legend (fit scores):**  
- **Install** = pip/clone friction  
- **License** for product/vendoring  
- **Custom cube** = min code for our (H,W,B)+labels  
- **Spatial blocks** = can respect block split without rewrite  
- **8 GB** = practical VRAM with B′≈20–30 after MNF/PCA  

---

## 1. DeepHyperX

| Field | Detail |
|-------|--------|
| **Repo** | https://github.com/nshaud/DeepHyperX |
| **Clone** | `git clone https://github.com/nshaud/DeepHyperX.git` |
| **Stars / activity** | ~492 ★; **archived 2024-09-09**; last push 2022-09-30 |
| **License** | **GPLv3 for research/non-commercial**; commercial needs ONERA contact. **Not Apache/MIT** — careful if vendoring into Apache/MIT product. |
| **Stack** | PyTorch (+ Visdom, scikit-learn SVM) |
| **Install** | `pip install -r requirements.txt` or Docker `registry.gitlab.inria.fr/naudeber/deephyperx:preview`. Python 2.7/3.5+ era; expect pin/port for modern torch. |

### Models list (`models.py` / README)

| CLI name | Class | Notes |
|----------|-------|-------|
| `svm` / SGD | sklearn | Linear / RBF / poly grid search |
| `nn` | `Baseline` | 4-layer MLP on spectrum |
| `hu` | `HuEtAl` | **1D CNN** (best first DL for us) |
| `hamida` | `HamidaEtAl` | 3D CNN, default patch 5 |
| `lee` | `LeeEtAl` | Contextual deep CNN / FCN-ish |
| `chen` | `ChenEtAl` | 3D CNN, large patch 27 (VRAM heavy) |
| `li` | `LiEtAl` | 3D CNN patch 5 |
| `he` | `HeEtAl` | Multi-scale 3D, patch 7 |
| `luo` | `LuoEtAl` | HSI-CNN, patch 3 |
| `sharma` | `SharmaEtAl` | 2D CNN, patch 64 (too large for Cuprite tiles) |
| `liu` | `LiuEtAl` | Semi-supervised 2D CNN |
| `boulch` | `BoulchEtAl` | Semi-supervised 1D autoencoder + head |
| `mou` | `MouEtAl` | GRU spectral RNN |

No HybridSN / SpectralFormer (pre-dates those).

### Train custom cube

1. Edit `custom_datasets.py`: add entry to `CUSTOM_DATASETS_CONFIG` with loader returning  
   `(img H×W×B, gt H×W, rgb_bands, ignored_labels, label_values, palette)`.
2. Point `--dataset` at that name; place arrays under `--folder`.
3. Example:

```bash
python main.py --model hu --dataset Cuprite --training_sample 0.5 --cuda --patch_size 1
python main.py --model hamida --dataset Cuprite --patch_size 7 --epoch 50 --cuda
```

**Caveat:** default split is **random labeled pixels** (`training_sample` fraction), **not spatial blocks**. Must replace sampling in `datasets.py` / `utils.py` with train-block masks from our `SpatialSplit`.

### Fit for open-ore-mapper

| Criterion | Assessment |
|-----------|------------|
| Installability | Medium — archived, Visdom, old deps |
| License | **Poor for product** (GPL dual) — **thin-wrap/citation only**, do not copy wholesale into MIT/Apache tree without legal pass |
| Min custom cube | ~20–40 lines in `custom_datasets.py` |
| Spatial block protocol | **Rewrite required** (pixel-random by default) |
| 8 GB VRAM | **OK** for `hu` (1D), `hamida`/`li`/`he` at patch 5–7 + batch 32–100; avoid `chen` (27) and full-B 3D without PCA |

**Verdict:** Best **architecture zoo** to steal ideas from; prefer **reimplement 1D CNN / Hamida-style** under our license rather than vendoring GPL tree.

---

## 2. SpectralFormer (official)

| Field | Detail |
|-------|--------|
| **Repo** | https://github.com/danfenghong/IEEE_TGRS_SpectralFormer |
| **Clone** | `git clone https://github.com/danfenghong/IEEE_TGRS_SpectralFormer.git` |
| **Stars / activity** | ~333 ★; last push **2024-11-30** (alive) |
| **License** | **GPLv3** (README “Licensing”) — no SPDX on GitHub |
| **Stack** | PyTorch 1.6-era + scipy.io MAT; ~2 files: `demo.py`, `vit_pytorch.py` (~150 LOC model) |
| **Install** | No `requirements.txt`; `pip install torch scipy scikit-learn matplotlib` |

### How it runs

- Expects MAT with keys `input`, `TR`, `TE` (pre-split train/test maps) for Indian / Pavia / Houston.
- Modes: `ViT` (baseline), `CAF` (SpectralFormer with group-wise spectral embedding + cross-layer fusion).
- Pixel-wise: `--patches=1 --band_patches=3 --mode=CAF`  
- Patch-wise: `--patches=7 --band_patches=3 --mode=CAF`  
- Model: `ViT(image_size, near_band, num_patches=band, dim=64, depth=5, heads=4, mlp_dim=8)`.

### Min code for custom (H,W,B)+labels

1. Build `TR`/`TE` as H×W class maps from **our** train/test block masks (not random pixels).
2. Either write MAT or bypass loaders: feed `x_train_band` tensors shaped `[N, band*band_patches, patch*patch]` as in `demo.py`.
3. Instantiate same `ViT(...)` with `num_patches=B` (or B′ after band subset), `num_classes=C`.

Rough adapter (~40–80 lines):

```python
# sketch — not drop-in
from vit_pytorch import ViT
# train_idx / test_idx from spatial_eval.SpatialSplit + pure GT
# patches = extract_patches(cube, coords, p=7)
# band tokens via gain_neighborhood_band(...)
model = ViT(image_size=7, near_band=3, num_patches=B_prime,
            num_classes=n_cls, dim=64, depth=5, heads=4, mlp_dim=8, mode="CAF")
```

### Fit

| Criterion | Assessment |
|-----------|------------|
| Installability | **Easy** (tiny repo) |
| License | GPL — **wrap model weights API, don’t vendor as product core** without dual-license path |
| Custom cube | Medium — MAT/TR/TE boilerplate |
| Spatial blocks | **Doable**: replace TR/TE construction with block masks |
| 8 GB | **Yes** for pixel-wise; patch-wise 7×7 with B=200 needs care — prefer **MNF→30 bands** or SWIR-only |

**Verdict:** Strong **Phase B transformer baseline** if RF plateaus; thin-wrap `vit_pytorch.ViT` only under GPL compliance or re-express architecture.

---

## 3. HybridSN — official + PyTorch reimplementations

### 3a. Official Keras — `gokriznastic/HybridSN`

| Field | Detail |
|-------|--------|
| **Clone** | `git clone https://github.com/gokriznastic/HybridSN.git` |
| **Stars** | ~362 ★; push 2023-12-23 |
| **License** | **MIT** ✓ |
| **Quality** | Paper-faithful notebooks; TF 1.3 / Keras 2.0 era — **not installable on modern stacks without port** |
| **Split** | Random % train (Indian Pines OA 99.8% style) — **not spatial** |

### 3b. PyTorch — `purbayankar/HybridSN-pytorch` (recommended among reimpls)

| Field | Detail |
|-------|--------|
| **Clone** | `git clone https://github.com/purbayankar/HybridSN-pytorch.git` |
| **Stars** | ~45 ★; last push **2021-05** (stale) |
| **License** | **MIT** ✓ |
| **Quality** | **Medium.** Has real `.py` modules (`HybridSN.py`, `geniter.py`, `Utils.py`, `environment.yml`). Class `HybridSN_network`: 3× Conv3d → reshape → Conv2d → FC. Also carries unused MHSA code (commented). README training command still mentions `A2S2KResNet.py` (copy-paste error). Hardcodes `.cuda()`, PCA to K bands, **pixel-random `sampling()`**. Dense layer sizes (`18496`) tied to fixed patch/band — **must recompute for Cuprite**. |
| **Install** | `conda env create -f environment.yml` — pin-sensitive |

### 3c. PyTorch notebook — `Pancakerr/HybridSN`

| Field | Detail |
|-------|--------|
| **Clone** | `git clone https://github.com/Pancakerr/HybridSN.git` |
| **Stars** | ~49 ★; push 2022-03 |
| **License** | **MIT** ✓ |
| **Quality** | **Medium-low for engineering.** Single Jupyter notebook; good results plots for IP/PU/SA; harder to CI/import. Same random-split culture. |

### HybridSN VRAM / protocol

- Typical: PCA→30, patch 25×25 or 9–11, batch 16–32 → **fits 8 GB**.
- Full 219-band 3D without PCA: **risky** on 8 GB.
- **All public HybridSN codes use random pixel splits** → must inject our block masks.

**Verdict:** Prefer **extract `HybridSN_network` from purbayankar (MIT)** into our tree with dynamic flatten size + spatial DataLoader; do not run notebooks as production path.

---

## 4. LightGBM / XGBoost for HSI mineral or rock classification

### Libraries (prefer as dependencies, not “repos to wrap”)

| Package | Clone / install | License | Notes |
|---------|-----------------|---------|-------|
| **LightGBM** | `pip install lightgbm` · https://github.com/lightgbm-org/LightGBM (~18.6k ★) | **MIT** | Fast histogram GBDT; sklearn API |
| **XGBoost** | `pip install xgboost` · https://github.com/dmlc/xgboost (~28.6k ★) | **Apache-2.0** | Maturity; GPU hist optional |

### Domain examples (thin, often not mineral-specific)

| Repo | ★ | License | Relevance |
|------|---|---------|-----------|
| [onurkaraca87/ML-Hyperspectral-TSS](https://github.com/onurkaraca87/ML-Hyperspectral-TSS) | 3 | MIT | LightGBM + XGB + RF on **spectra** (water TSS, not minerals) — good **sklearn-style loop** |
| [AnkurDeria/HSI-Traditional-to-Deep-Models](https://github.com/AnkurDeria/HSI-Traditional-to-Deep-Models) | ~163 | none | Survey code: **`RandomForest/`**, SVM, HybridSN, etc. — pattern only |
| Papers (no strong OSS mineral GBDT) | — | — | Cuprite RF two-class expansion (MDPI minerals 2023); SMMA decision trees — not reusable packages |

**Honest finding:** There is **no high-star, MIT mineral-mapping LightGBM toolkit**. Practical path is **extend our `ml_rf.py`**:

```python
# Drop-in beside RandomForestClassifier
from lightgbm import LGBMClassifier
# or: from xgboost import XGBClassifier
clf = LGBMClassifier(
    n_estimators=500, num_leaves=63, learning_rate=0.05,
    class_weight="balanced", n_jobs=-1,
)
clf.fit(X_train, y_train)  # X from FEATURE_SETS in ml_rf
pred = clf.predict(X_all)
# → class_map → evaluate_maps(..., ignore_index=255)
```

| Criterion | LightGBM / XGB via our features |
|-----------|----------------------------------|
| Install | **Trivial** |
| License | MIT / Apache ✓ |
| Custom cube | **Already solved** in `ml_rf` |
| Spatial blocks | **Already solved** |
| 8 GB | **CPU-first**; GPU optional |

**Verdict:** Highest ROI next baseline after RF — **no third-party mineral repo needed**.

---

## 5. torchgeo / rasterio training patterns (spatial split)

### torchgeo

| Field | Detail |
|-------|--------|
| **Repo** | https://github.com/torchgeo/torchgeo |
| **Clone** | `git clone https://github.com/torchgeo/torchgeo.git` · `pip install torchgeo` |
| **Stars** | ~4115 ★; **very active** (push 2026-07-25) |
| **License** | **MIT** ✓ |
| **Role** | GeoDataset, **RandomGeoSampler / GridGeoSampler / RandomBatchGeoSampler**, Lightning tasks, multi-band chips — **not** a Hyperspectral Indian Pines zoo |

**Spatial patterns relevant to us:**

1. **ROI-scoped sampling:** pass train/val/test **polygons** as `roi=` on samplers so chips never cross block boundaries (matches block protocol in CRS space).
2. **GridGeoSampler** for non-overlapping eval inference (stitch class maps).
3. **Intersection** `image & labels` for aligned multi-file GeoTIFFs.
4. For **in-memory Cuprite** (no georef required), torchgeo is **optional heavy**; our `make_spatial_split` already implements block protocol in array space.

**Min pattern (georeferenced scenes later):**

```python
from torchgeo.datasets import RasterDataset
from torchgeo.samplers import RandomGeoSampler, GridGeoSampler
# train_roi / test_roi from block polygons in scene CRS
train_ds = RasterDataset(paths="scene/")  # multi-band GeoTIFF
sampler = RandomGeoSampler(train_ds, size=7, length=5000, roi=train_roi)
# eval: GridGeoSampler(..., size=7, stride=7, roi=test_roi)
```

### rasterio

| Field | Detail |
|-------|--------|
| **Repo** | https://github.com/rasterio/rasterio · `pip install rasterio` |
| **Stars** | ~2552 ★; active |
| **License** | **BSD-style** (Mapbox copyright; permissive redistribution) |
| **Role** | Windowed read of large GeoTIFF chips; CRS; write prediction GeoTIFF |

Pattern: `rasterio.windows.Window` + `dataset.read(window=...)` for train chips; write class map with same transform/profile. Complements torchgeo; we already use `tifffile` for Cuprite package.

| Criterion | Assessment |
|-----------|------------|
| Install | Excellent (PyPI) |
| Spatial blocks | **Native** via ROI / windows |
| HSI mineral models | **None** — I/O + sampling only |
| 8 GB | N/A (CPU I/O) |

**Verdict:** Use **torchgeo later** for multi-scene GeoTIFF training; keep **array-level spatial_eval** for Cuprite research. Don’t block ML on torchgeo.

---

## 6. Mineral-mapping–specific open repos

| Repo | ★ | Last push | License | Notes |
|------|---|-----------|---------|-------|
| [hifexplo/tinto](https://github.com/hifexplo/tinto) | 6 | 2024-05 | none clear (dataset site) | **Rio Tinto HSI mineral benchmark** (2D/3D hypercloud, XRD-backed labels). Dataset + paper, **not a trainer**. Gold for **external validation** later. |
| [jabarhabashi1/Deep-Learning](https://github.com/jabarhabashi1/Deep-Learning) (“Hyperspectral Mineral Mapping Toolbox”) | 6 | 2025-11 | none | VCA + 3D CNN mineral maps (EMIT/EnMAP). Young, sparse stars, **no SPDX** — inspect before wrap. |
| [Abdallah-M-Ali/Mineral-Prospectivity-Mapping-ML](https://github.com/Abdallah-M-Ali/Mineral-Prospectivity-Mapping-ML) | 38 | 2023-02 | none | RF/SVM/ANN/CNN **prospectivity** (GIS layers), not AVIRIS pixel minerals. |
| [decastrodg/EMIT-Lake-Salda-Mineral-Mapping](https://github.com/decastrodg/EMIT-Lake-Salda-Mineral-Mapping) | 0 | 2026-01 | **MIT** | EMIT + noise-aug **SVM** carbonate facies — small but clean MIT example. |
| [WUTCM-Lab/SSPNet](https://github.com/WUTCM-Lab/SSPNet) | 2 | 2026-01 | none | Mineral HSI CNN paper code. |
| [EleftheriaTtl/enmap-mineral-classification](https://github.com/EleftheriaTtl/enmap-mineral-classification) | 0 | 2026-07 | none | EnMAP chipping + OSM masks pipeline. |
| [Nrevyw/awesome-hyperspectral](https://github.com/Nrevyw/awesome-hyperspectral) | 72 | 2025-12 | Apache-2.0 | Curated list (mining focus) — index only. |

**Finding:** Mineral-specific **supervised trainers** are sparse, low-star, and often unlicensed. Prefer **land-cover HSI codebases + our labels** over fragile mineral-only repos. Tinto is the best **dataset** lead; toolbox repos need license cleanup.

---

## Cross-cutting comparison

| Implementation | License | Install | Custom (H,W,B) | Spatial blocks | 8 GB | Wrap priority |
|----------------|---------|---------|----------------|----------------|------|---------------|
| DeepHyperX | GPL dual | med | easy | rewrite | yes (1D/small 3D) | low (license) |
| SpectralFormer | GPL | easy | med | rewrite TR/TE | yes | med (model only) |
| HybridSN Keras | MIT | hard (TF1) | notebook | rewrite | yes | low |
| HybridSN-pytorch | MIT | med | med | rewrite | yes | **high** |
| LightGBM/XGB | MIT/Apache | easy | via `ml_rf` | **done** | CPU | **highest** |
| torchgeo | MIT | easy | GeoTIFF-first | ROI native | N/A | med (I/O later) |
| Tinto | dataset | data-only | N/A | N/A | N/A | later benchmark |
| eecn Hyperspectral-Classification | GPL (DeepHyperX fork, ~585★) | med | like DeepHyperX | rewrite | yes | same as DHX |

---

## Top 5 repos to wrap first

Ranked for **our** stack (spatial_eval + evaluate_maps + Cuprite + 8 GB + license hygiene).

### 1. LightGBM (library) — extend `ml_rf`, not a model zoo

| | |
|--|--|
| **Clone / install** | `pip install lightgbm` · https://github.com/lightgbm-org/LightGBM.git |
| **Why first** | Same protocol as RF (already winning OA≈0.79); minutes to A/B; MIT; no VRAM. |
| **Integration sketch** | |

```text
ml_rf.py
  FEATURE_SETS unchanged (reflectance | mnf | mtmf_scores | …)
  + train_lgbm(...)  # mirror train_rf
  + predict → (H,W) class_map (UNKNOWN outside valid)
spatial_eval / scripts/ml_spatial_rf_baseline.py
  --model {rf,lgbm,xgb}
  seed loop → evaluate_maps(class_map, ref_test, names, ignore_index=255)
  write_evaluation_artifacts → outputs/research_ml_lgbm/
```

Optional: `xgboost` same adapter (Apache-2.0).

---

### 2. HybridSN-pytorch (MIT) — first spatial DL

| | |
|--|--|
| **Clone** | `git clone https://github.com/purbayankar/HybridSN-pytorch.git` |
| **Why** | MIT; explicit HybridSN 3D→2D; extractable class; paper baseline for “CNN vs RF”. |
| **Integration sketch** | |

```text
Vendor or re-copy HybridSN_network into src/open_ore_mapper/models/hybridsn.py
  - Fix flatten size from (patch, B_prime)
  - PCA/MNF fit on TRAIN blocks only (reuse ml_rf.mnf_transform)

Data:
  split = make_spatial_split(H, W, seed=...)
  train_coords = pure GT ∩ train mask
  Dataset: crop padded cube → (1, B', p, p) tensor + label

Train: CE + class weights; early stop on VAL blocks
Infer: sliding window over full scene → class_map
Score: evaluate_maps(class_map, mask_reference_to_split(ref, split, TEST), ...)

Suggested defaults: B'=30 MNF, p=7 or 9, batch=32, epochs=50–100 on chomp
```

---

### 3. SpectralFormer official (GPL model file)

| | |
|--|--|
| **Clone** | `git clone https://github.com/danfenghong/IEEE_TGRS_SpectralFormer.git` |
| **Why** | Compact spectral transformer; pixel-wise mode is light; literature-backed SWIR grouping. |
| **License note** | Keep as **optional plugin** / research script under GPL, or reimplement CAF under our license. |
| **Integration sketch** | |

```text
scripts/ml_spatial_spectralformer.py
  load_cuprite_benchmark()
  split = make_spatial_split(...)
  Build TR/TE-equivalent from split masks (not MAT)
  Prefer: patches=1, band_patches=3, mode=CAF on SWIR or MNF bands
  Full-scene argmax → evaluate_maps on test

Do NOT merge vit_pytorch.py into Apache/MIT package without compliance plan.
```

---

### 4. DeepHyperX — 1D CNN (`HuEtAl`) as architecture reference

| | |
|--|--|
| **Clone** | `git clone https://github.com/nshaud/DeepHyperX.git` |
| **Why** | Cleanest **1D spectral CNN** for mineral spectra; lowest DL risk after RF/LGBM. |
| **License note** | **GPLv3 research** — reimplement `HuEtAl` (simple Conv1d) under our license; cite Audebert et al. 2019. |
| **Integration sketch** | |

```text
src/open_ore_mapper/models/spectral_1d_cnn.py  # reimplemented, not copied
scripts/ml_spatial_1dcnn.py
  X_train = cube[train_pure]  # (N, B) or CR spectra
  model: Conv1d → pool → FC → C classes
  predict all valid pixels → class_map
  evaluate_maps on test blocks

Optional: compare to DeepHyperX main.py only in research sandbox (GPL tree).
```

---

### 5. torchgeo (+ rasterio) — geospatial I/O / future multi-scene

| | |
|--|--|
| **Clone** | `git clone https://github.com/torchgeo/torchgeo.git` · `pip install torchgeo rasterio` |
| **Why** | Production path for EnMAP/EMIT multi-tile; ROI samplers encode **spatial non-overlap**; MIT. |
| **Integration sketch** | |

```text
Near-term Cuprite: keep tifffile + spatial_eval (no torchgeo required).

Mid-term:
  Write scene.tif + reference.tif with CRS
  train_roi / test_roi from block polygons
  RandomGeoSampler(roi=train_roi) for patch CNN training
  GridGeoSampler(roi=full) for stitched inference GeoTIFF
  Feed stitched class map into evaluate_maps (array path unchanged)

Does not replace classifiers — wraps HybridSN/1D/SF data loading.
```

**Honorable mentions:**  
- **Tinto** dataset (https://github.com/hifexplo/tinto) for second-site mineral GT.  
- **gokriznastic/HybridSN** paper reference only.  
- **eecn/Hyperspectral-Classification** (~585★) = DeepHyperX lineage, same GPL issues.

---

## Recommended sequence (engineering)

```text
1. LGBM/XGB in ml_rf  →  multi-seed OA vs RF-MNF (CPU, 1 day)
2. If need DL: 1D CNN reimpl (Hu-style) on CR/SWIR  →  spatial protocol
3. HybridSN-pytorch extract on MNF patches  →  8GB chomp
4. SpectralFormer pixel CAF only if (2)–(3) competitive
5. torchgeo when leaving single-array Cuprite for multi-scene GeoTIFF
```

**Hard win criteria** (from `ML_RESEARCH_DIRECTION.md`):  
`mean_OA(ML) > mean_OA(best classical) + 0.02` **and** kaolinite recall not worse — all under **spatial block** `evaluate_maps`.

---

## Sources (scraped 2026-07-26)

- GitHub: nshaud/DeepHyperX, danfenghong/IEEE_TGRS_SpectralFormer, gokriznastic/HybridSN, purbayankar/HybridSN-pytorch, Pancakerr/HybridSN, eecn/Hyperspectral-Classification, torchgeo/torchgeo, lightgbm-org/LightGBM, dmlc/xgboost, rasterio/rasterio, hifexplo/tinto, AnkurDeria/HSI-Traditional-to-Deep-Models, mineral search API results  
- Docs: https://docs.torchgeo.org/en/stable/api/samplers.html  
- Internal: `docs/ML_RESEARCH_DIRECTION.md`, `docs/RESEARCH_PROTOCOL.md`, `src/open_ore_mapper/ml_rf.py`
