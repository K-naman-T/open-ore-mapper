# Adversarial metrics skeptic brief — open-ore-mapper

**Author role:** hostile statistician / remote-sensing evaluation skeptic  
**Date:** 2026-07-26  
**Scope:** Claims in `docs/BEST_NUMBERS.md`, `docs/RESEARCH_PIPELINE_RESULTS.md`, `docs/ML_RESEARCH_DIRECTION.md`, multi-seed outputs under `outputs/research_ml_*` and `outputs/research_spatial_*`, code in `src/open_ore_mapper/{ml_rf,ml_boost,ml_cnn1d,spatial_eval,evaluate}.py`, Tetracorder GT construction in `scripts/run_cuprite_real_validation.py` + `benchmarks/cuprite_real/`.

**Stance:** Attack the claims. No “both sides” until the final sections.

---

## Executive indictment

The headline **“HistGB 0.816 wins science”** is not an honest scientific ranking of mineral-mapping methods. It is a **closed-set supervised pixel classifier** trained on **Tetracorder-derived pure pixels**, scored against **the same Tetracorder hard labels**, with **OA** as primary metric, on a **5-seed 4×4 block lottery** whose class composition is violently unstable, then ranked by **cherry-picking feature stacks** across model families. The “+0.028 over RF” gate pass in `docs/BEST_NUMBERS.md` compares **different feature sets** and is **not statistically significant** at α=0.05 under a paired t-test on the five seeds they themselves published.

What they actually measured is closer to:

> *Can a balanced tree ensemble reproduce Tetracorder’s hard multi-class map on held-out spatial blocks when given train-block pure labels and handcrafted spectral features that already encode scene endmember MTMF scores?*

That is **reproducibility of an expert-system raster**, not independent mineral identification, not discovery, and not a fair bake-off of RF vs boosting vs CNN.

---

## 1. Fatal flaws

### F1. Label circularity with Tetracorder fd-max (task is not “truth”)

Hard labels are built in `scripts/run_cuprite_real_validation.py` `build_reference()`:

- Load Tetracorder 4.4 `*.fd.gz` fit×depth layers per mineral.
- Per-pixel **argmax** across mineral layers.
- Keep pixels with `best_score >= 20`; else ignore (255).

```130:163:scripts/run_cuprite_real_validation.py
def build_reference(class_names: list[str]) -> tuple[np.ndarray, dict[str, int]]:
    """Argmax-style: for each pixel, mineral with highest fd value if > threshold."""
    ...
    best = scores.argmax(axis=2).astype(np.uint8)
    best_score = scores.max(axis=2)
    ...
    mask = best_score >= 20  # conservative
    ref[mask] = best[mask]
```

Protocol admits this (`docs/RESEARCH_PROTOCOL.md` §2): Tetracorder is itself a spectral expert system; claims must be “vs Tetracorder,” not absolute truth. **The supervised pipelines then train on pure pixels of that same map** (`ml_rf.py` / `ml_boost.py`: `train_labeled = train_mask & (ref_remapped != ignore)`).

Consequences:

| Fact | Implication |
|------|-------------|
| Labels = Tetracorder feature rules + fd threshold | Models learn **Tetracorder’s decision surface**, including its SWIR-clay taxonomy quirks and Fe-oxide weakness |
| Train pure pixels = high-fd pixels | Training set is **not** a random sample of mixed surface materials; it is Tetracorder’s confident core |
| Scene endmembers for MTMF features also from those pure GT pixels | `refl_mnf_mtmf` feeds the model **MF/infeas vs Tetracorder-aligned endmembers** → second-order circularity |
| Only **18.4%** of scene labeled (84 669 / 460 500) | OA is computed on the **same sparse confident mask** Tetracorder already selected |

**Fatal claim failure:** Calling HistGB OA **0.816** “best supervised spatial **science**” (`BEST_NUMBERS.md`) overclaims. It is **agreement with another algorithm’s hard map**, with library/features partly derived from that map. G4 in the protocol (“discovery needs independent library”) was never satisfied for the headline number.

### F2. The published “win over RF by +0.028” is a stacked deck, not a fair model comparison

`BEST_NUMBERS.md` gate table:

| Criterion | Best RF | Best new | Result |
|-----------|---------|----------|--------|
| vs RF +0.02 | RF-**MNF** **0.788** | HistGB **rich** **0.816** | **pass (+0.028)** |

That is **not** model A vs model B under matched conditions. It is:

- **HistGradientBoosting** on `reflectance + MNF-20 + MTMF scores` (≈255 features)
- vs **RandomForest** on **MNF-20 only**

From the same artifacts:

| Method | Feature set | Mean OA ± std | Source |
|--------|-------------|---------------|--------|
| HistGB | refl+MNF+MTMF | **0.816 ± 0.025** | `outputs/research_ml_boost/summary.json` |
| HistGB | MNF | 0.780 ± 0.059 | same |
| RF | MNF | 0.788 ± 0.042 | `outputs/research_ml_rf/summary.json` |
| RF | refl+MNF+MTMF | **0.779 ± 0.035** | same |
| 1D-CNN | MNF-**30** | 0.793 ± 0.046 | `outputs/research_ml_cnn1d/summary.json` |

**On matched MNF features, HistGB does not lead** (0.780 < RF 0.788 < CNN 0.793). The “winner” is the **only** model reported with the rich stack in the final ranking narrative—CNN was never run on `refl_mnf_mtmf` (`ml_cnn1d.py` only allows `reflectance` or `mnf`).

Same-feature paired deltas (HistGB rich − RF rich), five seeds:

| Seed | HistGB rich | RF rich | Δ |
|-----:|------------:|--------:|--:|
| 42 | 0.8028 | 0.7350 | +0.068 |
| 7 | 0.8429 | 0.7966 | +0.046 |
| 99 | 0.7877 | 0.7744 | +0.013 |
| 123 | 0.8492 | 0.8352 | +0.014 |
| 2024 | 0.7992 | 0.7548 | +0.044 |

Mean Δ ≈ **+0.037** (more honest than +0.028 vs RF-MNF)—but the **public scoreboard still sells the unfair RF-MNF comparison** as the gate pass.

### F3. Seed-42 “kaolinite R = 0” is a one-pixel farce averaged into science

From `outputs/research_ml_boost/seed_42/hist_refl_mnf_mtmf/metrics.json`:

| Class | Support (test labeled) | HistGB recall |
|-------|-----------------------:|--------------:|
| kaolinite | **1** | **0.0** |
| alunite | **0** | n/a |
| hematite | **0** | n/a |
| muscovite | 7086 | 0.884 |
| montmorillonite | 7157 | 0.655 |
| calcite | 3517 | 0.976 |

**95.4%** of seed-42 test labels are calcite + muscovite + montmorillonite. Kaolinite recall of 0 is misclassification of **one pixel** (to goethite). That 0.0 is then averaged into:

- `kaolinite_recall` mean **0.526 ± 0.303** for HistGB rich  
- Gate note: “noisy, not clearly worse”

Including seed 42’s kaolinite R in a five-seed mean is statistical malpractice: one Bernoulli trial with n=1. The multi-seed “secondary” metric is **dominated by junk variance from split lottery**, not mineral physics.

Kaolinite test support across seeds (HistGB rich metrics):

| Seed | Kaolinite support | Recall |
|-----:|------------------:|-------:|
| 42 | **1** | 0.000 |
| 7 | 2439 | 0.386 |
| 99 | 7364 | 0.850 |
| 123 | 1127 | 0.683 |
| 2024 | 2814 | 0.709 |

That is not a stable estimand. It is a **geographic sampling accident**.

### F4. 4×4 blocks (~188×154 px) are not a serious spatial independence protocol for Cuprite

`make_spatial_split` default: **4×4** blocks, train 50% / val 25% / test 25% of **blocks** (`spatial_eval.py`).

Seed 42 edges (`spatial_split.json`):

- Rows: 0, 188, 375, 562, 750  
- Cols: 0, 154, 307, 460, 614  
- Test blocks: **4 of 16** (~25% of area)

Cuprite alteration units are **spatially continuous at multi-hundred-meter scales**. A ~188×154 AVIRIS block is still a large, internally correlated region. With only **4 test blocks**, mineral presence is lottery:

- Seed 42 test: kaolinite≈absent, alunite absent, hematite absent → OA becomes **clay–carbonate–oxide majority vote**.
- Seed 99 test: kaolinite support 7364 → OA and kaolinite R track different geographies.

**n_seeds = 5** with **n_test_blocks ≈ 4** yields ≤20 unique test-block realizations, heavily overlapping spatially across seeds, **not** independent replications. Treating mean±std over seeds as if it were a sampling distribution of methods is aspirational.

Protocol itself warned (`RESEARCH_PIPELINE_RESULTS.md` §3.2): seed 42 under-represents minerals; “protocol demo, not final science”—yet **BEST_NUMBERS still aggregates seed 42 into the “science” multi-seed means** without exclusion or stratified reporting.

---

## 2. Serious issues

### S1. +0.028 vs RF-MNF is not a meaningful / significant improvement under their own seed set

Paired seed-wise **HistGB rich − RF MNF**:

| Seed | Δ OA |
|-----:|-----:|
| 42 | +0.0413 |
| 7 | +0.0268 |
| 99 | +0.0634 |
| 123 | +0.0043 |
| 2024 | +0.0068 |

- mean Δ = **0.0285**, sample std of Δ ≈ **0.0247**  
- paired *t* (df=4) ≈ **2.58**  
- two-sided critical *t*(0.05, 4) ≈ **2.776**

**Fails α = 0.05.** The gate threshold “+0.02” was chosen in `ML_RESEARCH_DIRECTION.md` as a hard win rule and then declared “pass” without a significance test, confidence interval, or pre-registered primary comparison. Seed std of OA for RF-MNF alone is **0.042**—larger than the claimed gain. Cross-seed OA range for HistGB rich is **0.788–0.849** (span **0.061**). Celebrating **0.028** against that backdrop is cargo-cult precision.

### S2. OA is the wrong primary metric for multi-class mineral mapping

`evaluate_maps` (`evaluate.py`) defines:

\[
\mathrm{OA} = \frac{\#\{\mathrm{pred}=\mathrm{ref}\}}{\#\{\mathrm{ref}\neq 255\}}
\]

No class weighting. Full-scene class shares (among labeled pixels):

| Class | Count | Share |
|-------|------:|------:|
| montmorillonite | 20834 | **24.6%** |
| muscovite | 16560 | **19.6%** |
| calcite | 13888 | **16.4%** |
| goethite | 13252 | **15.7%** |
| kaolinite | 11204 | 13.2% |
| chalcedony | 3689 | 4.4% |
| alunite | 3195 | 3.8% |
| hematite | 2047 | **2.4%** |

OA is dominated by **common SWIR clays + calcite + goethite**. A method can look excellent while:

- missing alunite/hematite (exploration-relevant),
- swapping muscovite↔montmorillonite (spectrally adjacent; confusable),
- failing kaolinite on seeds where it matters.

Seed 42 macro-F1 (classes with support > 0) ≈ **0.66** while OA ≈ **0.80**—a **14-point gap** showing OA’s majority-class inflation. Protocol lists secondary per-class metrics but **all ranking tables and “win” gates use OA (and κ)**. κ still inherits the same closed-set confusion structure and does not fix class imbalance or operational false-positive cost on unlabeled ground.

For mineral mapping, **per-class F1 / producer’s–user’s accuracy on rare units, detection F1 under open-set, and false paint rate on unlabeled pixels** matter more than OA on Tetracorder-pure cores.

### S3. Closed-set always-assign systematically inflates OA vs classical open-set methods

Supervised codepaths:

```332:347:src/open_ore_mapper/ml_rf.py
    # Closed-set predict on all valid pixels
    ...
    pred_valid = clf.predict(X_all).astype(np.uint8)
    class_map = np.full((h, w), UNKNOWN_CLASS, dtype=np.uint8)
    class_map[valid_coords[:, 0], valid_coords[:, 1]] = pred_valid
```

Provenance flag: `"closed_set": True` (RF, boost, CNN).

Classical MTMF uses thresholds (`mf_threshold=0.3`, `infeas_threshold=15`) and can leave unknowns; unknowns on labeled test pixels count as **errors** in `evaluate_maps` (pred not equal ref; OOB/unknown does not fill confusion diagonal).

Assigned fraction among test-labeled pixels (from confusion sum / n_labeled):

| Seed | MTMF assigned | HistGB rich assigned | MTMF OA | HistGB OA |
|-----:|--------------:|---------------------:|--------:|----------:|
| 42 | **86.0%** | **100%** | 0.549 | 0.803 |
| 7 | 96.4% | 100% | 0.721 | 0.843 |
| 99 | 97.3% | 100% | 0.558 | 0.788 |
| 123 | 96.1% | 100% | 0.712 | 0.849 |
| 2024 | 94.8% | 100% | 0.603 | 0.799 |

On seed 42, MTMF **conditional** accuracy given a detection is **0.638**, not 0.549—still below HistGB, but the **scoreboard gap is partly protocol**, not pure spectral skill. MNF-SAM baseline is also forced closed-set (`sam_threshold_deg=180`, `min_strength=0` in `spatial_eval.py`), while SAM/CR/MTMF are not—**classical ladder is internally inconsistent**.

Comparing supervised closed-set OA to unsupervised open-set OA as “ML beats classical by ≫0.02” is an **apples-to-oranges product claim**.

### S4. Cap of 2000 samples/class distorts training priors and rare-class learning

`_cap_train_indices` / default `max_train_samples_per_class=2000` in all three ML modules. Full-scene montmorillonite has 20k+ pure pixels; after train-block filter many classes exceed 2000. Subsampling:

- equalizes class counts (with `class_weight="balanced"` / `balanced_subsample` stacked on top → **double rebalancing**),
- throws away majority-class spectral diversity,
- makes results sensitive to the cap seed (`seed + model_seed`).

No ablation of cap ∈ {500, 2000, ∞} is reported in BEST_NUMBERS. The “0.816” number is **conditional on an arbitrary 2000 cap**.

### S5. RF / boost / CNN comparison is procedurally unfair

| Dimension | RF | HistGB | 1D-CNN |
|-----------|----|--------|--------|
| Feature sets reported | reflectance, mnf, mtmf_scores, **refl_mnf_mtmf** | mnf, **refl_mnf_mtmf** | **mnf only** |
| MNF components | **20** | **20** | **30** |
| Epochs / trees | 200 trees | 200 iter | **15 epochs** (script default in BEST_NUMBERS; code default 20) |
| Early stop on val | **No** | **No** | **No** |
| `min_samples_leaf` | **2** | **20** | n/a |
| class_weight | balanced_subsample | balanced | inverse-frequency CE |
| Rich MTMF features | yes (one run) | yes (headline) | **never** |
| Spatial context | none | none | none (1D spectral only) |

CNN “≈ RF” is the only fair-ish comparison (both MNF spectral features), and **CNN is slightly ahead of RF-MNF** (0.793 vs 0.788) with **more MNF components**. Declaring “no free win from a small net” is fine; declaring **HistGB the supervised leader** while denying CNN the rich feature stack is not.

Hyperparameters were **not** selected on val blocks despite protocol §3.2 (“Val reserved for threshold / hyperparameter choices”). Val is dead weight in ML runners—train/test only.

### S6. Multiple testing and post-hoc leaderboard

Published combinations include at least:

- Classical: SAM, CR, MTMF, MNF-SAM, fuse (multi-seed)
- RF × 4 feature sets  
- HistGB × 2 feature sets  
- LightGBM × 1  
- CNN × 1  

≈ **13+ method×feature cells**, then “rank 1 = max OA”. No family-wise error control, no pre-registered single primary endpoint (protocol’s “ML must beat classical **and** RF” is gamed by swapping RF’s feature set). The win criterion in `ML_RESEARCH_DIRECTION.md` also required **kaolinite recall ≥ classical**—HistGB kao R 0.53±0.30 vs classical multi-seed is not cleanly shown, and seed 42’s zero poisons the mean.

### S7. Supervised vs unsupervised is conflated in “science” language

- Unsupervised fuse multi-seed: **0.664 ± 0.092**  
- Supervised HistGB: **0.816 ± 0.025**

These are different tasks. Fuse uses **train-block endmembers only** (no train labels at inference learning). HistGB uses **thousands of pure GT labels** (`n_train_samples` ~12k–15k per seed after capping). Claiming a single ordered scoreboard (`RESEARCH_PIPELINE_RESULTS.md` executive table ranks HistGB #1s above fuse #1u) invites readers to treat **0.816 as a better mapper** for unlabeled scenes. Product text elsewhere correctly keeps fuse as default—but the research scoreboard still sells supervised OA as the science ceiling.

### S8. Full-scene semi-leaked OA still pollutes messaging

Full-scene fuse **0.713** / MTMF **0.671** use endmembers from **all pure GT** (`run_cuprite_real_validation.py`, `benchmarks/cuprite_real/README.md`). Protocol says this is diagnostic only. Yet `BEST_NUMBERS.md` opens with that scoreboard and `RESEARCH_PIPELINE_RESULTS.md` still headlines full-scene numbers. Leakage-aware readers can separate them; **casual scoreboard consumers cannot**.

---

## 3. Mild issues

### M1. Cohen’s κ reported without caveats under extreme imbalance / missing classes

κ on seed 42 ignores that two classes have zero support; confusion is effectively 5–6 class. κ looks “healthy” (0.70) while rare-class performance is undefined.

### M2. Aggregation is unweighted mean over seeds, not weighted by n_labeled

Test n varies: 16 746 – 32 237. Unweighted mean OA for HistGB rich ≈ 0.816; n-weighted ≈ 0.818 (similar here)—but **rare-class metrics** should be pooled or reported with support, not seed-mean of recalls.

### M3. Buddingtonite dropped from legend

GT layers include buddingtonite; `legend.json` has 8 classes without it. Fine if intentional, but fd layers for dickite / multiple kaolin maps are partially merged (kaolwxl + kaolpxl max)—label taxonomy is **lossy and project-specific**, not “Tetracorder standard legend.”

### M4. Stochastic MTMF background + RF/boost model seeds fixed at 0

Only spatial seed varies. Model seed / MTMF subsample seed locked → underestimates uncertainty of a single pipeline run.

### M5. No independent lab library spatial scoreboard for supervised models

Protocol G4 remains open. All “science” supervised numbers are scene-GT-coupled.

### M6. CNN training has no learning-rate schedule, no val early stop, fixed 15 epochs

Under-trained or over-trained depending on seed; not a tuned spectral CNN baseline.

---

## 4. Attack on each requested claim

### (1) HistGB 0.816 “wins” science honestly — **REJECT**

**Why:** Circular Tetracorder labels; unfair feature stack vs RF/CNN; OA-primary; unstable splits; non-significant vs RF-MNF; closed-set; no independent library. At best: *best among tried supervised closed-set Tetracorder-reproducers under this protocol with rich features*.

### (2) RF / boost / CNN comparison is fair — **REJECT**

**Why:** Different feature sets, MNF dimensionality, hyperparameter defaults, and incomplete factorial design. On MNF-only, ranking is CNN ≳ RF ≳ HistGB—**opposite of the headline**.

### (3) Multi-seed spatial protocol is enough — **REJECT**

**Why:** 4×4 blocks too large; 4 test blocks; class absence; seed 42 kaolinite n=1; std of OA for fuse is **0.092**; five seeds with shared geography are pseudo-replicates. Protocol is **better than random pixels**, not “enough” for science claims.

### (4) OA is the right metric for mineral mapping — **REJECT as primary**

**Why:** Majority-class domination; ignores open-set paint; ignores rare targets; seed-wise macro-F1 diverges from OA. Acceptable as **one** reported number among many; fatal as **the** ranking key.

### (5) Beating RF by 0.028 is meaningful vs seed variance — **REJECT**

**Why:** Seed OA std ~0.025–0.06; paired *t* vs RF-MNF fails 5%; gain smaller than seed-to-seed swings (e.g. HistGB OA 0.788 on seed 99 vs 0.849 on seed 123). Even same-feature +0.037 is a **small-n** result without CI or multiplicity control.

### (6) Label leakage / circularity with Tetracorder fd-max — **SUSTAINED AS FATAL**

**Why:** Labels, pure-pixel training set, and MTMF endmember library all derive from the same fd-max construction. Spatial hold-out reduces **pixel reuse**, not **algorithmic circularity**.

### (7) Cap 2000 / closed-set always-assign inflate OA — **SUSTAINED (serious)**

**Why:** Cap rebalances training; closed-set guarantees a class on every valid pixel so labeled test never incurs “unknown” penalty that hurts MTMF/SAM. Magnitude of closed-set inflation vs MTMF is seed-dependent (large on seed 42’s 14% unknowns; smaller when MTMF assigns >96%).

---

## 5. What evidence would change this skeptic’s mind

I would **soften or withdraw** specific attacks if the project produced:

1. **Pre-registered primary endpoint**  
   One model family, one feature set, one metric suite, locked before looking at test seeds.

2. **Matched factorial**  
   RF = HistGB = LightGBM = CNN on **identical** features (at least `mnf` and `refl_mnf_mtmf`), identical MNF *k*, identical train caps, ≥ same compute budget for CNN (val early stop).

3. **Stratified / denser spatial design**  
   e.g. 8×8 or 10×10 blocks, or checkerboard with minimum pure pixels per class **in train and test**, or **exclude seeds** where any class support < N_min (e.g. 50). Report **leave-one-block-out** OA and per-class F1.

4. **Metrics that match mineral mapping**  
   - Macro-F1 and weighted-F1  
   - Per-class producer/user accuracy with CIs  
   - Open-set: allow abstain; report detection F1 and **false-positive rate on unlabeled (ref=255) valid pixels**  
   - Kaolinite / alunite / hematite as **co-primary** rare/target metrics  

5. **Statistics, not qualitative guesswork**  
   Paired bootstrap over blocks or seeds; 95% CI on ΔOA; multiplicity-aware ranking; significance only if pre-specified.

6. **Independent labels or library**  
   - Lab/USGS endmembers only (no scene pure GT) **and/or**  
   - Field/XRD polygons not derived from Tetracorder  
   Spatial test on those.

7. **Ablations**  
   Cap 2000 vs full train; closed-set vs confidence threshold; MTMF features on/off; train labels vs endmembers-only.

8. **Replication**  
   Second scene (not only Cuprite 1995), same protocol.

Until then, **0.816 is an internal leaderboard number**, not a scientific ceiling for mineral mapping quality.

---

## 6. Revised claim language I would accept

### Acceptable (honest)

- “Under a 5-seed 4×4 spatial-block protocol on Cuprite AVIRIS 1995, a **HistGradientBoostingClassifier** trained on **train-block Tetracorder pure pixels** with **reflectance + train-fit MNF + train-library MTMF scores** achieved **mean overall accuracy 0.816 (std 0.025)** against **held-out Tetracorder hard labels** (fd-max ≥ 20).”

- “On **matched MNF features**, RF, HistGB, and a small 1D-CNN are **within ~0.01–0.02 mean OA**; no method dominates.”

- “These results measure **agreement with Tetracorder**, not field-validated mineral discovery. Scene-derived endmembers and pure-pixel training **couple** the pipeline to Tetracorder’s feature logic.”

- “Unsupervised `fuse_classical` multi-seed mean OA **0.66 ± 0.09** remains the leakage-safer **label-free** reference; it is not commensurate with supervised OA.”

- “Seed 42 test blocks contain **1 kaolinite pixel**; kaolinite recall means/stds that include this seed are **not interpretable** without support-weighted pooling.”

### Unacceptable (current or implied)

- “HistGB **wins** science / is the supervised spatial **leader** for mineral mapping.”  
- “Beats RF by **0.028** (gate **pass**)” without stating feature mismatch and lack of significance.  
- “Best science number **0.82**” as product-ready mineral accuracy.  
- Any language implying **independent identification**, **discovery**, or **generalization beyond Tetracorder**.  
- Ranking tables that mix **full-scene leaked**, **unsupervised open-set**, and **supervised closed-set** OA as one ladder without screaming footnotes.

### Minimal corrected scoreboard row (example)

| Method | Features | Protocol | Mean OA | Notes |
|--------|----------|----------|---------|-------|
| HistGB | refl+MNF+MTMF | 5-seed spatial, closed-set, Tetracorder pure train | 0.816 ± 0.025 | Reproduces Tetracorder; not fair vs RF-MNF |
| RF | MNF-20 | same | 0.788 ± 0.042 | Matched to CNN better |
| CNN1D | MNF-30 | same | 0.793 ± 0.046 | No rich features tried |
| fuse_classical | unsup EM | same splits, open/closed hybrid | 0.664 ± 0.092 | No train labels |

---

## 7. Evidence table (absolute paths)

| Claim / fact | Path |
|--------------|------|
| Headline 0.816 | `/home/knamant/open-ore-mapper/docs/BEST_NUMBERS.md` |
| Gate +0.028 vs RF-MNF | same |
| HistGB aggregates | `/home/knamant/open-ore-mapper/outputs/research_ml_boost/summary.json` |
| RF aggregates | `/home/knamant/open-ore-mapper/outputs/research_ml_rf/summary.json` |
| CNN aggregates | `/home/knamant/open-ore-mapper/outputs/research_ml_cnn1d/summary.json` |
| Fuse multi-seed | `/home/knamant/open-ore-mapper/outputs/research_spatial_fuse_multi/all_seeds.json` |
| Seed 42 kao support=1 | `/home/knamant/open-ore-mapper/outputs/research_ml_boost/seed_42/hist_refl_mnf_mtmf/metrics.json` |
| fd-max GT | `/home/knamant/open-ore-mapper/scripts/run_cuprite_real_validation.py` |
| Cap 2000, closed-set RF | `/home/knamant/open-ore-mapper/src/open_ore_mapper/ml_rf.py` |
| HistGB defaults | `/home/knamant/open-ore-mapper/src/open_ore_mapper/ml_boost.py` |
| CNN MNF-30 only | `/home/knamant/open-ore-mapper/src/open_ore_mapper/ml_cnn1d.py` |
| OA definition | `/home/knamant/open-ore-mapper/src/open_ore_mapper/evaluate.py` |
| 4×4 split, MNF-SAM always-assign | `/home/knamant/open-ore-mapper/src/open_ore_mapper/spatial_eval.py` |
| Protocol caveats | `/home/knamant/open-ore-mapper/docs/RESEARCH_PROTOCOL.md` |

---

## 8. Bottom line (ruthless)

The repository did **real engineering**: spatial blocks beat random pixels; train-only MNF/MTMF is better than full-scene leakage; RF/boost/CNN were actually run. That does **not** redeem the **marketing of 0.816**.

**Fatal:** Tetracorder circularity + unfair feature comparison sold as “HistGB wins.”  
**Serious:** OA-primary, 4×4/5-seed fragility, closed-set vs open-set, non-significant 0.028, cap-2000, dead val split, multiplicity.  
**Mild:** κ caveats, unweighted seed means, missing lab-library supervised runs.

**Correct scientific status of HistGB 0.816:**  
*Strong Tetracorder-map reproduction under a convenient supervised closed-set protocol—not a validated mineral-mapping accuracy, not a fair ML bake-off winner, not evidence that boosting “solved” Cuprite.*

Until the evidence list in §5 exists, every sentence that treats **0.816** as a scientific ranking should be treated as **overclaim**.
