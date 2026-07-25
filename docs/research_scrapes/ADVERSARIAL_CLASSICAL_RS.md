# Adversarial brief: library spectroscopy vs supervised OA-on-Tetracorder

**Persona:** classical remote sensing scientist (imaging spectroscopy / mineral mapping, 1990s–2020s ops lineage)  
**Stance:** defend **library-based / physics-based** mapping; treat **supervised OA against Tetracorder hard labels** as the wrong game  
**Compiled:** 2026-07-26  
**Sources:** in-repo code, scoreboards, and industry baseline only (no invented OA).  
**Primary artifacts cited:**

| Path | Why it matters |
|------|----------------|
| [`docs/BEST_NUMBERS.md`](../BEST_NUMBERS.md) | Full-scene + spatial multi-seed OA scoreboard |
| [`docs/research_scrapes/INDUSTRY_MINERAL_BASELINE_2026.md`](INDUSTRY_MINERAL_BASELINE_2026.md) | Ops stack; Cuprite OA caveats |
| [`docs/RESEARCH_PIPELINE_RESULTS.md`](../RESEARCH_PIPELINE_RESULTS.md) | Classical ladder; semi-dependence on Tetracorder |
| [`docs/ML_RESEARCH_DIRECTION.md`](../ML_RESEARCH_DIRECTION.md) | Explicit admission: Tetracorder labels are weak |
| [`src/open_ore_mapper/service.py`](../../src/open_ore_mapper/service.py) | `fuse_classical`, MTMF unknown gate, always-assign |
| [`src/open_ore_mapper/evaluate.py`](../../src/open_ore_mapper/evaluate.py) | OA = match on labeled pixels; unknown is error |
| [`src/open_ore_mapper/spatial_eval.py`](../../src/open_ore_mapper/spatial_eval.py) | Train-block pure-GT endmembers; closed-set MNF-SAM |
| [`src/open_ore_mapper/ml_rf.py`](../../src/open_ore_mapper/ml_rf.py) | Supervised RF: labels = pure GT train pixels |
| [`src/open_ore_mapper/cr_sam.py`](../../src/open_ore_mapper/cr_sam.py) | Region-gated CR-SAM (physics path) |
| [`scripts/run_cuprite_real_validation.py`](../../scripts/run_cuprite_real_validation.py) | Scene endmembers from high-purity Tetracorder pixels |

---

## Thesis (one paragraph)

Overall accuracy against **Tetracorder 4.4 fd mineral maps**, using **endmembers or labels drawn from those same maps**, is not mineral science. It is **map-to-map imitation**. The project’s real scientific progress was the classical ladder—**SAM → continuum / CR-SAM → MTMF → `fuse_classical`**—because those methods move **library and absorption physics** closer to a published expert-system product under honest spectral matching. Climbing from fuse multi-seed **~0.66** to HistGB **~0.82** by training RF/boosting/CNN on **Tetracorder pure pixels** with **MNF/MTMF features** is, under classical RS ethics, **overfitting a map product**. The honest metric for open-ore-mapper is **independent spectral-library transfer** (USGS/RELAB-class references, no GT-derived endmembers), with **open-set rejection** of unknowns, not closed-set always-assign OA.

---

## 1. Matching Tetracorder with RF/HistGB is circular

### 1.1 Three nested dependencies on the same expert system

The Cuprite scoreboard is not “sensor → geology.” It is “sensor → **algorithm A** → labels; algorithm B trained or seeded from A; score B vs A.”

| Layer | What the repo does | Why it is circular |
|-------|--------------------|--------------------|
| **Labels** | Reference = Tetracorder 4.4 fd maps (`BEST_NUMBERS.md`, validation extras: `"ground_truth": "Tetracorder 4.4 fd mineral maps"`) | Supervised truth *is* an expert-system mineral map, not XRD grid |
| **Endmembers (classical)** | Full-scene: median spectra of high-purity **GT** pixels (`scene_endmember_library_csv`); spatial protocol: median pure GT inside **train blocks** (`build_train_endmember_library`, source string: `"train-block scene endmembers (median pure GT pixels)"`) | Library is **scene-conditioned on Tetracorder purity**, not independent lab transfer |
| **Supervised ML** | RF/HistGB/LightGBM/1D-CNN: “Labels come from pure GT pixels inside train blocks” (`ml_rf.py` module docstring); features include reflectance + **MNF + MTMF** fit on train | Model learns **Tetracorder decision regions** in feature space that already encodes classical matching |

The full-scene validation script is explicit about the semi-dependence:

> *“Not independent of Tetracorder for discovery, but validates that SAM+NNLS can map real AVIRIS reflectance when the library is scene-appropriate.”*  
> — `scripts/run_cuprite_real_validation.py` → `scene_endmember_library_csv`

`RESEARCH_PIPELINE_RESULTS.md` already footnotes full-scene OA:

> *“Full scene, endmembers from all pure GT pixels (**semi-dependent on Tetracorder**).”*

That footnote is the entire case. Semi-dependence is not a minor QA note; it is a **validity threat** for any claim that higher OA means better mineral identification.

### 1.2 Supervised OA is algorithm imitation, not discovery

RF / HistGB / 1D-CNN under the spatial multi-seed protocol do **not** invent mineral physics. They:

1. Take pixels Tetracorder already called “pure mineral X.”  
2. Build features that classical spectroscopy already uses (MNF components, MTMF MF + infeasibility, reflectance).  
3. Fit a classifier to reproduce Tetracorder class IDs on held-out **blocks of the same map product**.  
4. Report OA as if geology were recovered.

That is **teacher–student distillation of Clark et al.’s expert system** through a statistical learner. Spatial block hold-out reduces *pixel* leakage; it does **not** remove *label-process* leakage. Train and test blocks still share:

- the same expert rules, continuum features, and fd-max fusion quirks;  
- the same taxonomy and purity definition;  
- the same systematic errors (mixtures forced to hard classes, under-represented rare phases, Al-content subclasses collapsed).

`ML_RESEARCH_DIRECTION.md` already concedes the point in the risk list:

> *“Tetracorder fd-max hard labels ≠ field truth; **optimizing to them can overfit an algorithm’s quirks**.”*  
> *“Mineral maps ≠ crop land-cover; **Tetracorder labels are weak**.”*

Yet the same document and `BEST_NUMBERS.md` still crown **HistGB · refl+MNF+MTMF mean OA 0.816** as “best science + OA.” Under classical ethics, that crown is **best imitation**, not best science.

### 1.3 Why “spatial multi-seed” does not rescue the circular metric

Honest spatial protocol (`spatial_eval.py`) is **necessary** and was good engineering:

- endmembers only from train blocks;  
- MNF/MTMF background stats from train;  
- metrics on test blocks only;  
- multi-seed (42, 7, 99, 123, 2024).

It answers: *“Did we leak pure pixels from the test location into the library?”*  
It does **not** answer: *“Did we identify minerals the way field geology or independent lab spectra would?”*

Industry baseline states the same structural caveat that the project still underweights in its ML ranking:

> *“‘Beat Tetracorder / USGS map’ with pixel OA → Often **agreement with another map**, not independent XRD grid.”*  
> — `INDUSTRY_MINERAL_BASELINE_2026.md` §2.2, §3.1–3.3

Wei-style **94%** Cuprite OA figures are map-to-map agreement; our **0.82** HistGB is the same genre with a spatial split. Genre does not become science because sklearn is careful.

### 1.4 Circular by construction of the scoreboard

`evaluate.py` defines success as:

```text
OA = (# pixels where pred == Tetracorder_label) / (# Tetracorder-labeled pixels)
```

Unknown predictions on labeled pixels are **errors** (no confusion column credit; still wrong for OA). So the metric **rewards** any procedure that paints the labeled support of Tetracorder—especially closed-set argmax—and **punishes** scientifically correct refusal (“I will not name this mixture / out-of-library pixel”).

Once labels, endmembers, and OA all orbit Tetracorder, RF/HistGB cannot lose the wrong game without failing to copy the teacher.

---

## 2. Independent USGS (or lab) library OA should be the real science metric

### 2.1 What library science is supposed to be

Operational mineral spectroscopy (ENVI hourglass, USGS Tetracorder itself, EMIT mineral products, EarthDaily-style Cuprite work) treats **reference spectra** as external physical knowledge:

1. Curated **USGS Spectral Library** (splib07) / field ASD / lab convolved spectra.  
2. Resample to sensor SRF; scale match reflectance.  
3. Optional continuum / feature fit (SFF, Tetracorder rules).  
4. Map with SAM / SFF / MTMF **against those references**, not against GT pixel means.  
5. Validate with field/XRD **when available**; otherwise report **map agreement** with an explicit disclaimer.

`INDUSTRY_MINERAL_BASELINE_2026.md` ranks **surface reflectance + library-aware SAM/SFF/MTMF** as the production spine and states:

> *“In-scene endmembers often beat lab libraries alone for mapping”* — as an **ops tradeoff**, not as the definition of scientific success.  
> *“Claiming Cuprite OA without documenting label source and split”* is listed under **what not to default**.

### 2.2 What the project actually scores as “best”

| Protocol | Library / labels | Scientific status |
|----------|------------------|-------------------|
| Full-scene fuse **0.713** | Scene endmembers = median pure **Tetracorder** pixels | Semi-dependent map agreement |
| Spatial classical fuse **0.664 ± 0.092** | Train-block pure **Tetracorder** endmembers | Leakage-safer **map agreement** |
| HistGB rich **0.816 ± 0.025** | Train pure **Tetracorder** labels + classical feature stack | **Supervised map imitation** |
| **Missing from BEST_NUMBERS** | **Fixed USGS/lab CSV only**; no GT-derived endmembers; optional open-set | **Independent library transfer** — the real science metric |

The service layer already knows that real minerals require an authoritative library CSV and refuses silent demo curves (`OreMapper._load_library`). That is the correct **product** posture. The **research scoreboard** then abandons it for Cuprite by rebuilding the library from Tetracorder pure pixels. Science and scoreboard disagree.

### 2.3 Definition: Independent USGS library OA (proposed primary metric)

**Independent library OA** (or better: library **transfer score**) for open-ore-mapper:

1. **Fixed external library** — e.g. USGS-derived curated hydrothermal pack (≤ ~30 spectra), convolved/resampled to the cube wavelengths; **no** median of GT pure pixels; **no** train-block GT endmembers.  
2. **Classifier** — SAM / CR-SAM / SFF / MTMF / `fuse_classical` using **only** that library (and scene background stats that do **not** use mineral labels).  
3. **Optional open-set** — thresholds for angle, MF, infeasibility; class 255 = unknown.  
4. **Reporting** —  
   - **Agreement OA** vs Tetracorder (secondary, labeled “map-to-map”).  
   - **Coverage / precision on high-confidence hits** (primary ops sense).  
   - Per-mineral producer accuracy only where support is large and pure.  
5. **Transfer** — same library weights/thresholds on a **second scene** without retraining labels.

Anything that rebuilds endmembers from Tetracorder purity is a **scene-conditioned calibration**, not library science. It may be a fair **internal ablation** of matching engines; it must not be sold as “best mineral OA.”

### 2.4 Why independent library is harder—and therefore more honest

Scene endmembers match illumination, mixing, residual ATM, and Tetracorder’s purity definition. Independent USGS spectra do **not**. Dropping OA when switching from GT endmembers to USGS is not failure; it is **truth-telling**. The project’s early full-library SAM disasters and the industry warning against “full 500-mineral brute force” are real—but the cure is **curation and thresholds**, not **GT-pure endmembers + supervised OA**.

---

## 3. fuse / MTMF / SFF progress was the real work; ML is overfitting a map product

### 3.1 The classical ladder is substantive spectroscopy

Repo scoreboard (same GT, same scene family):

| Stage | Method | Full-scene OA (approx.) | What actually improved |
|------:|--------|-------------------------:|------------------------|
| 0 | Full SAM + NNLS | **~0.34** | Angle matching alone fails on SWIR clays vs continuum / Fe |
| 1 | CR-region SAM (`continuum_removal` / `cr_sam`) | **0.58** | Continuum + **VNIR/SWIR region gating** (physics of absorptions) |
| 2 | MTMF | **0.671** | Matched filter + **infeasibility** (Boardman lineage); kaolinite R **0.686** |
| 3 | `fuse_classical` 0.7 MTMF + 0.2 CR + 0.1 MNF-SAM | **0.713** | Soft ensemble of complementary classical evidence |
| 4 | Spatial multi-seed fuse | **0.664 ± 0.092** | Same physics under leakage-safer endmembers |

This ladder is **defensible classical RS**: each step implements a known operational idea (continuum feature emphasis, noise-whitened geometry, mixture-tuned detection, multi-evidence fusion). `cr_sam.py` is explicit about the science motivation—full-spectrum SAM confuses SWIR minerals; region-gated continuum matching is the cure. MTMF in `service.py` implements the ops gate: accept only if MF and infeasibility pass; else **unknown 255**.

### 3.2 What “fuse” really is (and what it is not)

From `_classify_fuse_classical`:

- Soft scores: MTMF MF (percentile-scaled) + CR-SAM winner confidence + MNF-SAM strength.  
- Weights **0.7 / 0.2 / 0.1** — *“from Cuprite grid search maximizing labeled OA.”*  
- **“Always assigns on valid pixels (no unknown gate) for multi-class OA.”**

So fuse is:

1. **Real work:** combining complementary classical detectors.  
2. **Compromised science for the scoreboard:** weights tuned to Tetracorder OA; **unknowns disabled** so OA is not “hurt” by honesty.

Even with that compromise, fuse multi-seed **0.664** is the honest **unsupervised** ceiling under the project’s own spatial protocol. Product default remains fuse for unlabeled scenes (`BEST_NUMBERS.md`: *“Product default for unlabeled scenes remains `fuse_classical` (no train labels)”*). That sentence is correct ops. The error is ranking **0.82 supervised** above it as superior **science**.

### 3.3 ML’s jump is mostly label regression on classical features

Supervised multi-seed leaders (`BEST_NUMBERS.md`):

| Method | Mean OA ± std |
|--------|---------------|
| HistGB · refl+MNF+MTMF | **0.816 ± 0.025** |
| 1D-CNN · MNF-30 | 0.793 ± 0.046 |
| LightGBM · MNF | 0.791 ± 0.058 |
| RF · MNF | 0.788 ± 0.042 |
| fuse_classical (unsup) | **0.664 ± 0.092** |

Observe:

- The **winning features are classical products** (MNF, MTMF scores). The learner is not discovering SWIR doublets; it is **reweighting Boardman/Green-space coordinates** to Tetracorder.  
- Kaolinite recall for HistGB is **0.526 ± 0.303**—**noisier** and not a clear mineral win over classical paths that report stronger kaolinite R on full-scene MTMF (**0.686**). OA up, diagnostic mineral stability unclear: classic sign of **optimizing the wrong aggregate**.  
- Win criteria in `ML_RESEARCH_DIRECTION.md` only require `mean_OA(ML) > mean_OA(classical) + 0.02` and kaolinite recall not worse. That is a **competition rule for Tetracorder OA**, not a scientific success criterion for open mineral mapping.

**Adversarial verdict:** the real work was implementing and fusing **MTMF / CR-SAM / MNF-SAM**. The ML phase is a high-capacity **residual corrector** that absorbs Tetracorder idiosyncrasies remaining after classical soft scores. Calling that “best science” confuses **fitting a raster product** with **spectral mineralogy**.

### 3.4 Industry agrees with the classical spine

`INDUSTRY_MINERAL_BASELINE_2026.md` bottom line:

> Industry baseline 2020–2026: reflectance → **MNF** → endmembers → **SAM + (SFF or Tetracorder-style features)** and **MTMF** → expert QA.  
> Deep learning is **not** the production default for unlabeled exploration.  
> EMIT global minerals still trust **feature / expert-system** pipelines.

open-ore-mapper’s unsupervised default aligns with industry. Its **research vanity metric** does not.

---

## 4. Closed-set always-assign is geologically dishonest

### 4.1 Geology is open-set

Cuprite (and any exploration scene) contains:

- sub-pixel mixtures and alteration gradients;  
- minerals outside the active library;  
- shade, vegetation, wash, anthropogenic pixels;  
- Tetracorder “pure” masks that leave **most of the scene unlabeled** (n labeled = **84 669** vs full AVIRIS grid ~460k pixels).

A mapper that **must** assign every valid pixel to one of K library minerals is stating a false geological model: *the world is exhausted by our class list.*

### 4.2 The repo disables unknown for OA

| Location | Behavior |
|----------|----------|
| `_classify_fuse_classical` | Docstring: always assign valid pixels; **no unknown gate** for multi-class OA |
| Full-scene MTMF / fuse defaults in `run_cuprite_real_validation.py` | `mf_threshold` default **0.0**, `infeas_threshold` **50.0**, `min_confidence` **0.0**, SAM thr **90°** for scoreboard modes — gates opened so almost nothing rejects |
| `spatial_eval` MNF-SAM path | *“Closed-set hard labels: always assign nearest MNF-space endmember”* |
| `evaluate_maps` | Predicted unknown on a labeled pixel is **wrong** for OA; unknown gets **no** confusion-matrix credit |

MTMF’s implementation **does** know how to say unknown (`MF ≥ thr` and `infeas ≤ thr`; else 255). The scoreboard culture **turns that honesty off** when chasing OA. That is not a bug; it is a **metric-induced scientific error**.

### 4.3 Diff rendering still remembers the truth

`evaluate.py` colors:

- green = match,  
- red = mismatch,  
- **orange = reference labeled, we said unknown**,  
- gray = unlabeled.

Orange exists because **refusal is a first-class outcome**. Always-assign OA pretends orange should never appear. Classical target detection (ACE/MTMF) and Tetracorder itself are **not** forced closed-set land-cover classifiers; they are **detection / expert ID** systems with thresholds and multi-feature rules. Scoring them as closed-set K-way OA is category error.

### 4.4 Industry defaults include rejection

Recommended unsupervised product path in the industry baseline:

- reject endmembers if best library score below threshold → `"unidentified_endmember_N"`;  
- SAM threshold (start ~0.10 rad);  
- MTMF infeasibility mask as QA;  
- deliver confidence / rule images, not fantasy full-scene paint.

Always-assign for “multi-class OA” is **exam gaming**, not mineral mapping.

---

## 5. When supervised OA is invalid

Supervised (or semi-dependent) OA against Tetracorder is **invalid as a scientific claim of mineral correctness** when any of the following hold. Most project “best numbers” hit several at once.

| # | Condition | Project status |
|---|-----------|----------------|
| **V1** | Labels are another imaging-spectroscopy algorithm / map product, not independent field/XRD | **Always** for current Cuprite package |
| **V2** | Endmembers or training pure pixels are selected using those labels | Full-scene + spatial classical + all ML |
| **V3** | Features are classical scores (MNF/MTMF/CR) derived in the same spectroscopic family as the teacher | Especially HistGB/RF “rich” sets |
| **V4** | Metric is closed-set OA; unknowns disabled or punished | fuse always-assign; thr opened for scoreboard |
| **V5** | Thresholds / fusion weights tuned on the same site’s Tetracorder OA | fuse weights “Cuprite grid search maximizing labeled OA” |
| **V6** | Results are marketed as “best science” rather than “best agreement with Tetracorder under protocol P” | `BEST_NUMBERS.md` framing |
| **V7** | No held-out **scene**, **sensor**, or **external library** transfer test | Single-scene Cuprite AVIRIS 1995 dominance |
| **V8** | Class taxonomy / purity definition is the teacher’s fd-max fusion | Same hard labels train and test |

**Narrow validity** (still not “truth”): supervised OA can be a valid **engineering** metric for *“how well can we reproduce this map product from spectra when the user already has ROI labels?”* That is a **GIS digitization / map-transfer** tool, not open-ore mineral discovery. `BEST_NUMBERS.md` nearly says this—*“Supervised path is for when train regions / GT patches exist”*—then contradicts itself by ranking HistGB as the science leader.

**Invalid claims to ban:**

- “We achieved 82% mineral mapping accuracy at Cuprite.”  
- “ML beats classical spectroscopy for ore mapping.”  
- “fuse 0.71 is worse science than HistGB 0.82.”  

**Valid rewrites:**

- “Under spatial blocks, HistGB reproduces Tetracorder fd labels at mean OA 0.82 using MNF/MTMF features.”  
- “Unsupervised fuse agrees with Tetracorder at 0.71 full-scene / 0.66 multi-seed with GT-conditioned endmembers.”  
- “Independent USGS-library transfer OA is not yet the primary scoreboard.”

---

## 6. What re-scoring would restore scientific integrity

### 6.1 Scorecard reform (ordered)

| Priority | Metric | How to compute | Role |
|---------:|--------|----------------|------|
| **1** | **Independent library transfer agreement** | Fixed USGS (or field ASD) CSV; classical engines only; report OA/κ **and** open-set precision/coverage vs Tetracorder | Primary **science** score for unsupervised product |
| **2** | **Open-set operating points** | Sweep MF / infeas / SAM thr; plot precision vs recall of “called” pixels; report unknown rate | Honesty of detection |
| **3** | **Per-mineral diagnostic scores** | Kaolinite, alunite, calcite, buddingtonite, etc., with support floors; continuum feature depths optional | Exploration relevance > global OA |
| **4** | **Spatial multi-seed classical** (already done) | Train-block endmembers **only as ablation** of matching engines, labeled “semi-dependent” | Engine comparison under fixed circularity |
| **5** | **Supervised Tetracorder OA** | RF/HistGB spatial multi-seed | **Secondary product** metric when user labels exist; never “best science” alone |
| **6** | **Cross-scene / cross-sensor transfer** | Same library + thresholds on second district or coarser GSD (e.g. EMIT) | Anti-overfit gate |
| **7** | **Field / XRD / published assemblage check** | Where points exist: hit rate on traverses, not pixel OA | Gold standard when available |

### 6.2 Concrete protocol changes in this codebase

1. **Split the scoreboard** in `BEST_NUMBERS.md`:  
   - **A. Library science** (no GT endmembers).  
   - **B. Semi-dependent classical** (current fuse ladder).  
   - **C. Supervised map imitation** (HistGB/RF/CNN).  
2. **Re-enable unknown** for any “ops” or “science” row: restore MTMF mf/infeas gates; do not set fuse to always-assign for primary rows.  
3. **Stop counting unknown as pure OA error without a paired metric** — report  
   `agreement_on_calls`, `omit_rate`, `false_name_rate` (named wrong among calls).  
4. **Ban GT-pure endmembers** from any claim titled “library mapping.” Keep `build_train_endmember_library` only under ablation B.  
5. **Feature hygiene for ML:** if ML remains, train also on **library-only soft scores** as inputs and test whether the network still needs Tetracorder pure pixels—or admit it is a map emulator.  
6. **Weight tuning:** document fuse 0.7/0.2/0.1 as **Cuprite-OA-tuned**; freeze a **default unweighted or theory-weighted** fuse for transfer tests.  
7. **Language hygiene:** every metrics.json extra should include  
   `"label_source": "tetracorder_map_agreement"` and  
   `"library_source": "gt_pure_pixels" | "usgs_external"`.

### 6.3 What “restored integrity” looks like numerically (qualitative)

Do **not** invent numbers. Expect, honestly:

- Independent USGS library OA **lower** than 0.71/0.82.  
- Higher **unknown** fraction; higher precision on remaining calls.  
- Possibly better **geological credibility** of maps under expert review.  
- Supervised 0.82 remains a useful **emulator** number for “we have labels” workflows.

If independent library OA collapses while GT-endmember OA stays high, that is a **library/ATM/threshold problem** to fix—exactly the classical research agenda—not a reason to declare ML the science winner.

---

## 7. Ranking of classical vs ML claims for honesty

Honesty rank = how little the claim overstates independence from Tetracorder and how well it matches ops geology. **Higher is more honest.**

| Honesty rank | Claim type | Example from repo | Verdict |
|-------------:|------------|-------------------|---------|
| **1 (most honest)** | Unsupervised classical **with external library** + thresholds + unknown | Industry-recommended default; service requires real library CSV | **Science target**; under-scored today |
| **2** | Classical ladder improvement under **fixed** semi-dependent protocol | SAM 0.34 → CR 0.58 → MTMF 0.67 → fuse 0.71 | **Valid engineering science** of matchers; must stay labeled semi-dependent |
| **3** | Spatial multi-seed classical (train-only GT endmembers) | fuse **0.664 ± 0.092** | Honest **relative** ranking of unsupervised engines |
| **4** | MTMF with **working** infeasibility unknown gate | Implemented in `_classify_mtmf`; weakened for OA | Honest **detection** if gates restored |
| **5** | Product statement: fuse default when no labels | `BEST_NUMBERS.md` product default | Correct ops |
| **6** | Supervised RF/HistGB as **map emulator** given ROI labels | HistGB 0.816 multi-seed | Valid **product mode**; invalid as mineral truth |
| **7 (least honest)** | “Best science = highest Tetracorder OA” including supervised closed-set | HistGB/CNN crowned over fuse in research pipeline table | **Wrong game** |

### Classical claims — defend

- Continuum + region SAM improves clay/Fe separation for physical reasons (`cr_sam.py`).  
- MTMF is the right **sub-pixel / false-positive** tool (ENVI/Boardman; industry rank).  
- Soft fusion of independent classical evidence is legitimate (even if weights need transfer re-tuning).  
- Spatial block protocol is the minimum bar for any multi-seed claim.  
- Unlabeled exploration **must** ship classical library mapping, not RF.

### ML claims — attack (as currently framed)

- Higher OA ≠ better mineralogy when labels are Tetracorder.  
- Using MNF/MTMF features + Tetracorder pure pixels is **circular residual fitting**.  
- Closed-set multi-class CE/OA is the wrong loss for open-world alteration.  
- Kaolinite R noise under “winning” models shows aggregate OA can hide diagnostic failure.  
- Beating fuse by +0.02 OA under the same weak labels is a **competition win**, not a spectroscopy breakthrough.

---

## 8. What “success” should mean for open-ore-mapper scientifically

Success is **not** maximizing `overall_accuracy` in `evaluate_maps` against Tetracorder.

### 8.1 Scientific success (primary)

1. **Library-first mapping:** a curated, citable external spectral library produces spatially coherent alteration maps on real reflectance cubes **without** GT pure-pixel endmembers.  
2. **Open-set honesty:** substantial fractions of the scene remain unknown or low-confidence; confidence/infeasibility layers are first-class products.  
3. **Physics ladder retained:** continuum/SFF-style feature emphasis and MTMF remain inspectable (not buried only inside a black-box net).  
4. **Transfer:** same configuration works on another district/sensor at reduced but non-random agreement—without re-harvesting Tetracorder pure pixels.  
5. **Mineral-relevant diagnostics:** key exploration indicators (e.g. alunite–kaolinite–illite–chlorite–carbonate–FeOx packs) are correct in **assemblage and location**, not only global OA.  
6. **Explicit epistemology:** every published number states whether it is map-to-map agreement, library transfer, or field-validated.

### 8.2 Product success (secondary, legitimate)

1. Unsupervised path: `fuse_classical` (or successor) with **library CSV**, thresholds, QA layers.  
2. Optional supervised path: RF/HistGB when the user supplies ROIs—documented as **label propagation / map imitation**, not discovery.  
3. Demo Cuprite panel: agreement with published maps, disclaimer already in validation footer spirit: *“Candidates only — not ore proof.”*

### 8.3 Non-goals (reject)

- Chasing paper OA (90%+) on Cuprite via circular labels.  
- Replacing library mapping with DL as default for unlabeled exploration.  
- Always-assign full-scene paint to inflate OA.  
- Treating Tetracorder as ground truth while competing against it with students trained on it.

### 8.4 One-sentence success test

> **open-ore-mapper succeeds when a field spectral geologist trusts a library-driven, thresholded map on a scene they have never labeled—not when a gradient booster reproduces Clark’s raster at 82% under spatial blocks.**

---

## 9. Deliverable summary

### When supervised OA is invalid

When labels are Tetracorder (or any peer map product), training/endmembers use those labels, features recycle the same spectroscopic family, unknowns are suppressed, and the result is claimed as mineral accuracy rather than map agreement—**i.e. essentially the current ML scoreboard.**

### What re-scoring restores integrity

Primary board = **independent external library + open-set operating characteristics**; semi-dependent classical ladder as engine ablation; supervised Tetracorder OA demoted to optional “has labels” product metric; language and metrics.json provenance fields enforced.

### Honesty ranking (compressed)

**External library classical > semi-dependent classical ladder > spatial classical ablation > gated MTMF detection > supervised map emulator > “ML OA is best science.”**

### Real work vs vanity work

| Real work (keep) | Vanity work (reframe) |
|------------------|------------------------|
| CR-SAM / SFF-style feature emphasis | Closed-set HistGB OA crown |
| MTMF + infeasibility | Always-assign fuse for OA |
| Fuse of classical evidence | GT-pure endmembers sold as library science |
| Spatial multi-seed protocol | +0.02 OA gates as scientific victory |
| Authoritative library required in service | Scoreboard that rebuilds library from Tetracorder |

---

## 10. Closing adversarial statement

This project already built the hard classical path industry still ships: continuum-aware matching, MTMF, MNF geometry, and a fused unsupervised mapper. That path raised map agreement from coin-flip SAM (**~0.34**) to a serious unsupervised result (**~0.71 / ~0.66** multi-seed) on real AVIRIS. The subsequent ML campaign—**learning Tetracorder from Tetracorder-pure pixels with Tetracorder-adjacent features**—is a different sport. It is not wrong as software. It is wrong as **the** science metric for open-ore-mapper.

**Defend the library. Restore unknowns. Score transfer, not teacher imitation.**

---

*End of adversarial classical RS brief.*
