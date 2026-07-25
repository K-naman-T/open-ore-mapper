# Adversarial ML review — open-ore-mapper is under-ambitious

**Persona:** HSI / mineral-mapping ML reviewer who has read the community stack (Hu 1D-CNN → HybridSN → SpectralFormer / SSFTT → SSL / Mamba) and does **not** accept “HistGB won once” as a research conclusion.  
**Date:** 2026-07-26  
**Scope:** `/home/knamant/open-ore-mapper` — especially `docs/BEST_NUMBERS.md`, `docs/research_scrapes/HSI_DL_BASELINES_IMPLEMENT_2026.md`, `OPEN_IMPLEMENTATIONS_2026.md`, `ROUND2_MASTER_INDEX.md`, `src/open_ore_mapper/ml_{cnn1d,boost,rf}.py`, and multi-seed artifacts under `outputs/research_ml_*`.  
**Protocol we keep:** spatial-block multi-seed, train-only transforms, score test blocks only, **no random-pixel OA as win condition**.  
**Tone:** aggressive, but every experiment below is implementable on RTX 4060 8 GB / CPU-first paths you already use.

---

## 0. Executive indictment

You wrote a correct **anti-leakage** protocol, then used it to crown a **tabular booster on classical handcrafted features**, while shipping a **deliberately crippled neural baseline** and **skipping every community spectral–spatial model you yourselves ranked as P0**.

| Claim in `BEST_NUMBERS.md` | Adversarial reading |
|----------------------------|---------------------|
| HistGB · refl+MNF+MTMF **0.816 ± 0.025** “leads supervised” | Leads a **truncated** leaderboard: trees get physics detectors as free columns; CNN gets **MNF only**, 15 epochs, no val early-stop, **no patches**, **no HybridSN**. |
| 1D-CNN · MNF **0.793 ± 0.046** “≈ RF” | Expected when you **under-train** a small net and **deny** it the same feature stack and SWIR physics front-end you give boosting. |
| “CNN not required for OA” (`ML_RESEARCH_DIRECTION.md`) | Decision tree fires **after RF beats classical**, then freezes ambition. That is product conservatism, not scientific completeness. |
| Round-2 implement order: LGBM → 1D-CNN → **HybridSN** → **SpectralFormer** → SSL | You stopped after step 2 (barely) and declared victory. HybridSN / SpectralFormer / SSL remain **checkboxes on a scrape doc**. |

**Bottom line:** 0.816 is a **strong supervised tabular result under an honest split**. It is **not** evidence that spectral learning is “done,” that deep models “don’t help minerals,” or that the community baseline set has been engaged. Until you run **fair spectral-only**, **fair rich-feature**, and **patch / transformer / SSL** ablations under the **same** seeds, the scoreboard is **methodologically incomplete**.

---

## 1. Attack surface (mapped to code + numbers)

### 1.1 1D-CNN was under-tuned (and under-featured)

**Evidence**

| Setting | What shipped | What’s wrong |
|---------|--------------|--------------|
| Epochs | Script default **15** (`scripts/ml_spatial_cnn1d_baseline.py`); BEST_NUMBERS reproduces `--epochs 15` | Hu-style / DeepHyperX 1D nets routinely train **50–200** epochs or until val plateau. 15 is a smoke test, not a baseline. |
| Early stop | `train_cnn1d` loops fixed `epochs` only — **no val split, no patience, no LR schedule** (`ml_cnn1d.py`) | Protocol already carves **val blocks** (`val_frac=0.25`) and RESEARCH_PROTOCOL says val is for hyperparams. CNN **never uses them**. |
| Features | `feature_mode ∈ {reflectance, mnf}` only; **only MNF multi-seed reported** | Boosting’s winning set is **refl+MNF+MTMF**. CNN never saw MTMF scores or CR-SWIR. Apples-to-oranges then declared “tied.” |
| SWIR-only | **Not implemented** | Mineral physics is diagnostic in **~2000–2450 nm** (and CR). Your own classical ladder and ML direction text say this; the CNN path ignores it. |
| Capacity / optim | channels=32, Adam 1e-3, no weight decay, no mixup/noise, no cosine schedule | Fine as *minimum* model; **not** as the only neural attempt before abandoning the family. |
| Device | Artifacts show **`device: "cpu"`** for all seeds | Not a crime, but signals “run once, don’t iterate.” GPU path exists; tuning budget was zero. |
| HybridSN / SpectralFormer | **Zero code** | Round-2 and `HSI_DL_BASELINES_IMPLEMENT_2026.md` mark both **P0**. Not deferred after failure — **never attempted**. |

**Code smoking guns**

```127:142:src/open_ore_mapper/ml_cnn1d.py
    model.train()
    for ep in range(epochs):
        total = 0.0
        n = 0
        for xb, yb in loader:
            ...
            opt.step()
        if (ep + 1) % max(1, epochs // 5) == 0 or ep == 0:
            print(f"[ml_cnn1d] epoch {ep + 1}/{epochs} loss={total / max(n, 1):.4f}")
    model.eval()
    return model
```

No validation loader. No `early_stopping`. Loss is train CE only. This is **training theater**.

```179:186:src/open_ore_mapper/ml_cnn1d.py
    if mode == "reflectance":
        X = cube[rr, cc, :].astype(np.float32)
    elif mode == "mnf":
        ...
    else:
        raise ValueError(f"unknown feature_mode {feature_mode!r}; use reflectance or mnf")
```

No `cr`, no `cr_swir`, no `refl_mnf_mtmf`. Meanwhile `ml_rf.py` / `ml_boost.py` share a full `FEATURE_SETS` including the **winning** `refl_mnf_mtmf`.

**Verdict:** You did not lose with a 1D-CNN. You **never fielded a serious one**.

---

### 1.2 No spatial patches = missing the point of HSI literature

HSI classification literature (2016–2025) is overwhelmingly **spectral–spatial**:

| Model (your own P0/P1 list) | Input | Status here |
|-----------------------------|-------|-------------|
| HybridSN | 3D→2D on **patches** (7–25 px) after PCA/MNF | **Missing** |
| SSRN | 3D residual patches | **Missing** |
| SpectralFormer patch | 7×7 + spectral tokens | **Missing** |
| SSFTT | shallow CNN tokens → transformer | **Missing** |
| FreeNet | whole-map FCN | **Missing** |
| Your 1D-CNN | **per-pixel spectrum only** | Done poorly |

**Yes**, pure spectral models matter for sparse alteration and pure-pixel GT. That is an **ablation arm**, not a substitute for the community spectral–spatial suite.

**Fair concern you already raise (and should keep):** large patches under random-pixel splits leak. That is **not** an argument against patches under **block hold-out** with:

- train patches **centered only on train-block pure GT** (or labeled train pixels),
- test metrics only on **test-block labeled pixels**,
- MNF/PCA fit **train-block only** (already in `mnf_transform(..., sample_mask=train_bg)`),
- optional: forbid patches that straddle train/test block edges (center-in-block rule).

**Without that experiment, you cannot claim** “spatial context doesn’t help Cuprite minerals.” You can only claim “we didn’t try.”

---

### 1.3 HistGB win is “tabular cheating,” not spectral learning

HistGB · **refl + MNF + MTMF** at **0.816** is a **fusion of classical remote-sensing detectors with a strong tree ensemble**. That is scientifically interesting as **systems engineering**. It is **not** a demonstration that the model learned mineral absorption structure from reflectance.

| Feature block | Who invents the signal? | Who benefits most? |
|---------------|-------------------------|--------------------|
| Raw reflectance | Physics + sensor | Flexible learners (CNN/transformer *if* trained) |
| MNF (train-fit) | Linear noise-whitened PCA-like | Trees + linear + CNN equally |
| **MTMF MF + infeasibility** | **Matched filter / mixture-tuned physics** (Boardman lineage) | **Trees on low-dim scores** — almost designed for tabular GBDT |

You are effectively asking:

> Given MTMF’s per-class score vector (already a mineral detector) + MNF + reflectance, can HistGradientBoosting reweight and threshold better than RF?

**Answer: yes, slightly (+0.03 over RF-MNF).**  
That is **calibration / non-linear fusion of classical scores**, not “deep spectral representation learning.”

Compare apples properly:

| Condition | HistGB | RF | 1D-CNN | Patch HybridSN |
|-----------|--------|-----|--------|----------------|
| MNF only | 0.780 | 0.788 | 0.793 | **?** |
| refl+MNF+MTMF | **0.816** | 0.779 | **never run** | **?** |
| CR-SWIR only | **?** | **?** | **?** | N/A |
| raw reflectance only | RF 0.718 | 0.718 | **?** | **?** |

On **MNF alone**, 1D-CNN (0.793) already matches RF (0.788) **despite** 15-epoch under-training. The “HistGB is SOTA” headline is driven almost entirely by **giving the booster MTMF**, not by proving end-to-end spectral superiority.

**Name it correctly in papers:**

- OK: “Gradient boosting **fuses** reflectance, MNF, and MTMF scores under spatial hold-out (OA 0.816).”
- **Not OK:** “ML / boosting learns better mineral spectra than CNNs.”

---

### 1.4 Semi-supervised / pseudo-label path ignored despite unlabeled mass

**Label mass (full scene, Tetracorder fd-max pure labels):**

| Quantity | Value |
|----------|-------|
| Scene size | 750 × 614 ≈ **460 500** pixels |
| Labeled pure GT (full-scene scoreboard) | **84 669** (~**18%**) |
| Unlabeled / ignore 255 | ~**82%** of the scene |
| Train labeled (seed 42 example) | ~44 503 pure train pixels (before per-class cap) |
| Cap | **2000 / class** → ~12–15k train samples used |

Your own scrapes and `ML_RESEARCH_DIRECTION.md` call SSL / pseudo-labels **high value** for Cuprite. Round-2 ranks SSL as item **5**. Implementation status: **zero**.

Unlabeled pixels are not empty; they carry:

- high-confidence **MTMF** MF + low infeasibility,
- **CR-SAM / fuse_classical** decisions + confidence,
- spatial continuity of alteration zones.

Ignoring that is leaving the majority of the cube on the table while arguing that labels are “scarce” for DL.

---

### 1.5 Comparing to RF on the same handcrafted MTMF features stacks the deck for trees

Shared pipeline in `ml_rf` / `ml_boost`:

1. Train-block pure GT labels  
2. Train-only MNF  
3. Train-seeded MTMF with train endmember library  
4. Concatenate into wide table  
5. Fit RF or HistGB  

Trees are **near-optimal** for heterogeneous mixed-type columns (reflectance continuum + whitened components + detection scores). A 1D-CNN on MNF-only is **not** the same hypothesis class.

**Fair comparison matrix (what a reviewer demands):**

| Model | Input | Allowed? |
|-------|-------|----------|
| RF / HistGB / LGBM | reflectance only | yes |
| RF / HistGB / LGBM | MNF only | yes (current RF leader) |
| RF / HistGB / LGBM | MTMF scores only | yes (classical-score fusion) |
| RF / HistGB / LGBM | refl+MNF+MTMF | yes (systems fusion) |
| 1D-CNN / SpectralFormer pixel | reflectance / CR-SWIR / MNF | yes — **spectral learning** |
| 1D-CNN | concat(refl, MNF, MTMF) as multi-channel 1D or side MLP | yes — **fair rich-feature net** |
| HybridSN / SSRN | MNF patches | yes — **spatial community bar** |
| SSL student | any of the above + PL from teacher | yes |

**Unfair (current headline):** HistGB(rich classical) ≫ CNN(MNF, 15 ep) ⇒ “boosting wins.”

---

### 1.6 Is 0.816 actually low for supervised Cuprite if labels are dense pure pixels?

**Short answer: for pure-pixel, closed-set, same-scene spatial hold-out, 0.816 is middling-to-good — not a ceiling, and not “solved.”**

Context:

| Regime | Typical OA | Transferable here? |
|--------|------------|--------------------|
| HybridSN-style **random 10–30% pixel** on Indian Pines | **98–99%** | **No** (leakage; different task) |
| SpectralFormer fixed splits (IP patch ~82%) | high 70s–90s land-cover | **No** as number; yes as architecture family |
| Your **unsupervised** fuse multi-seed | **0.66** | Fair classical bar |
| Your **supervised** pure GT spatial | **0.79–0.82** | Real |
| Map-to-map agreement papers vs USGS mineral maps | often **>0.90** claimed | Different GT, often ROI / different taxonomy |

**Why pure-pixel Cuprite should not be “maxed” at 0.82:**

1. **Labels are high-purity Tetracorder hits (fd ≥ 20)** — these are the *easiest* spectra in the scene, not mixed rims.  
2. **Closed-set** over train-supported classes; ignore 255. No open-set penalty on unlabeled.  
3. **~2k samples/class** after cap — enough for strong supervised models on ~8 classes.  
4. Residual errors are dominated by **spatial seed variance** and **class imbalance** (kaolinite recall **0.53 ± 0.30** with **0.0 on seed 42** for HistGB rich). That is **not** a saturated method; that is a **brittle** one.  
5. Seed-wise OA for the “leader” still swings ~0.80–0.85; CNN MNF swings **0.72–0.84**. Large geographic sensitivity remains.

**If labels were dense pure pixels and the problem were “solved,” you would expect:**

- mean OA **≥ 0.88–0.92** under spatial blocks **or** an ablated demonstration that residual error is pure **label noise / Tetracorder circularity**,
- kaolinite recall **stable across seeds** (std ≪ 0.3),
- spectral-only models competitive with MTMF-fusion (proving spectra alone suffice).

None of those hold. **0.816 is a floor for a serious paper’s supervised track, not a trophy.**

---

## 2. Ranking of what was wrongly deferred

Ranked by **scientific damage if left undone** × **implementability** (not by academic fashion alone).

| Rank | Deferred item | Why it was wrong to stop | Effort (order) | Falsifies “HistGB is enough” if… |
|-----:|---------------|--------------------------|----------------|----------------------------------|
| **1** | **Fair feature parity for neural / spectral models** (CNN on refl, CR-SWIR, MNF, **and** rich concat; same seeds) | Current CNN vs HistGB comparison is **invalid** | 1–2 days | Tuned spectral model ≥ HistGB **without** MTMF, or rich-feature net ≥ HistGB |
| **2** | **Real 1D-CNN protocol** (val early-stop, 50–100+ ep, LR schedule, class-weighted already partly there, SWIR/CR ablations) | 15-ep fixed train is not a baseline | 1–2 days | CNN-MNF or CNN-SWIR ≥ RF-MNF / HistGB-MNF by ≥0.02 |
| **3** | **HybridSN (MNF 15–30, patch 7 then 11)** multi-seed spatial | Community **de facto** spectral–spatial bar; listed P0 twice in your scrapes | 3–5 days | HybridSN test OA ≫ pixel HistGB **or** clearly fails (either result is publishable) |
| **4** | **Semi-supervised pseudo-labels** (teacher = MTMF/RF/fuse conf on train-region unlabeled; student = 1D or HybridSN; **score true test GT only**) | ~82% of scene unused; SSL is the mineral-mapping use case | 3–5 days | SSL student > supervised-only counterpart by ≥0.02 OA or lifts rare-class recall |
| **5** | **SpectralFormer pixel (then patch-7)** | Canonical transformer HSI baseline; spectral grouping fits absorptions | 3–5 days (GPL wrap / reimpl) | Beats 1D-CNN / ties HistGB-MNF under spatial protocol |
| **6** | **Spectral-only leaderboard** (ban MTMF columns for a track) | Separates “learned spectra” from “MTMF fusion” | same as 1–2 | Paper can no longer hide behind classical detectors |
| **7** | **SSFTT / SSRN** | Only if HybridSN + SpectralFormer fail or tie | 1 week | Extra community completeness |
| **8** | **FreeNet tiled / image-level Mamba** | Map-consistency; VRAM risk | later | Only after P0/P1 |
| **9** | **Metric / few-shot for rare minerals** | Kaolinite seed-0 disasters | parallel track | Macro-F1 / rare-class R, not OA alone |

**What was *not* wrongly deferred:** rejecting random-pixel OA; keeping fuse_classical as unsupervised product default; train-only MNF/MTMF; multi-seed spatial blocks. Those are strengths. The failure is **stopping research at the first tabular win**.

---

## 3. Concrete next experiments that would falsify “HistGB is enough”

All use: seeds `{42,7,99,123,2024}`, same 4×4 blocks, train-only transforms, **test-block OA / κ / kaolinite R**, cap 2000/class (or ablate cap). **No random-pixel primary metric.**

### Experiment A — “Stop starving the CNN” (must-do, ≤2 days)

| Knob | Value |
|------|-------|
| Model | existing `SpectralCNN1D`, optional width 32→64 |
| Inputs (separate multi-seed runs) | (i) MNF-30 (ii) full reflectance (iii) **CR-SWIR 2000–2450 nm** (iv) **concat** refl+MNF+MTMF as multi-channel or flattened (fair rich) |
| Train | max 80 epochs, **val-block early stop patience 10**, AdamW + cosine or ReduceLROnPlateau |
| Val | pure GT in **val blocks only** for early stop / model select — **never test** |
| Gate vs HistGB rich | mean OA ≥ 0.816 **or** mean OA ≥ HistGB-MNF + 0.02 with better/stable kaolinite |

**Falsification:** any neural config ≥ HistGB rich under identical seeds.  
**Partial falsification:** neural **spectral-only** (no MTMF) ≥ HistGB **MNF** and ≥ RF-MNF → “trees need classical detectors; nets learn spectra.”

### Experiment B — HybridSN spatial (community bar, ~1 week)

| Knob | Value |
|------|-------|
| PCA/MNF | **30** components, fit train-block valid only |
| Patch | **7×7** first (VRAM), then **11×11** |
| Train centers | labeled pure train pixels; discard patches whose center is not train |
| Eval | predict every valid pixel (or every test labeled pixel with patch); metrics on test labels |
| Code source | MIT HybridSN-pytorch `HybridSN_network` — **recompute** dense size; do not vendor GPL DeepHyperX |
| Gate | mean OA vs HistGB rich **and** vs RF-MNF |

**Falsification:** HybridSN mean OA ≥ 0.83–0.85 **or** +0.02 over HistGB.  
**Also valuable failure:** HybridSN **loses** under spatial blocks → paper-ready claim that **Cuprite pure-pixel mineral maps do not reward spatial CNNs** (rare honest negative result).

### Experiment C — SpectralFormer pixel (spectral inductive bias)

| Knob | Value |
|------|-------|
| Mode | pixel CAF, band_patches=3, dim=64, depth=5 (paper defaults scaled to B′=MNF-30 or SWIR) |
| License | research plugin / reimpl — do not silently MIT-merge GPL |
| Gate | vs 1D-CNN and HistGB-MNF |

**Falsification:** SpectralFormer > tuned 1D-CNN by clear margin → spectral tokenization matters for minerals.

### Experiment D — Pseudo-label SSL (uses the unlabeled mass)

| Step | Spec |
|------|------|
| Teacher | RF-MNF or MTMF argmax with **confidence gate** (e.g. max proba ≥ τ or MF≥τ & infeas≤τ′) on **train-block unlabeled** pixels only (or train+val unlabeled; **never test-block PL into training**) |
| Student | tuned 1D-CNN or HybridSN |
| Iterate | 1–3 rounds progressive PL (your scrape cites progressive PL literature) |
| Score | **only** Tetracorder labels on test blocks |
| Gate | student OA ≥ supervised student + 0.02 **or** kaolinite R mean up ≥ 0.05 with std not exploding |

**Falsification:** SSL beats supervised HistGB **or** beats supervised neural twin → “HistGB on pure pixels leaves free lunch on the cube.”

### Experiment E — Spectral-only scoreboard (integrity track)

Ban MTMF (and optionally ban MNF) for one published table:

| Model | Input | Report |
|-------|-------|--------|
| HistGB | reflectance / CR-SWIR | OA±std |
| RF | same | |
| 1D-CNN | same | |
| SpectralFormer | same | |
| HybridSN | MNF patches (MNF allowed as compression, not MTMF) | |

**Falsification of “boosting is enough”:** if without MTMF, HistGB collapses toward 0.72–0.78 while a spectral net holds ≥0.80, the rich HistGB win was **classical fusion**, not general ML supremacy.

### Experiment F — Rare-class / macro metrics (stop OA-washing)

Report **macro-F1**, **kaolinite R**, **worst-seed kaolinite R**, not just OA.  
**Falsification:** method with OA 0.80 but macro-F1 and rare-class R dominating HistGB → OA leaderboard was the wrong objective.

---

## 4. Fair protocol upgrades (still no random-pixel)

These upgrades **preserve** your anti-leakage spine and make the paper review-proof.

### 4.1 Use the val blocks you already allocate

| Current | Upgrade |
|---------|---------|
| `val_frac=0.25` in split, unused by CNN/boost/RF for selection | **Mandatory** early-stop / hyperparam selection on val pure GT |
| Single fixed RF/HistGB hyperparameters | Light grid on **val only** (depth, lr, max_iter); lock before test |
| One CNN width/epoch | Select on val mean across **inner** seeds or fixed val per seed |

### 4.2 Dual track leaderboard (publish both)

| Track | Allowed features | Scientific question |
|-------|------------------|---------------------|
| **A. Systems / fusion** | refl + MNF + MTMF + classical scores | Best map given full classical stack |
| **B. Spectral learning** | reflectance and/or CR-SWIR and/or MNF only | Does the model learn spectra? |
| **C. Spectral–spatial** | MNF/PCA patches | Does neighborhood context help under block CV? |
| **D. SSL** | A–C + pseudo-labels from train unlabeled | Does unlabeled mass help? |

**Never average tracks.** Never headline Track A as “DL failed.”

### 4.3 Patch leakage rules (keep honest)

1. Center pixel ∈ train for training patches.  
2. Optional hard rule: entire patch ⊂ train block (stricter; report if used).  
3. MNF/PCA: train-block samples only.  
4. No test pixels in pseudo-labels.  
5. Multi-seed mean±std **primary**; full-scene pure-GT OA only as secondary “map agreement” with clear leakage caveats if library is scene-derived.

### 4.4 Feature parity law

> Any feature set offered to RF/HistGB must be offerable to at least one neural baseline in the same release of the scoreboard, **or** explicitly marked **fusion-only**.

### 4.5 Training budget law

> Neural baselines must use **val early-stopping** with a max epoch budget **≥ 50** (unless val plateaus earlier). Fixed 15-epoch runs are **smoke tests**, not scoreboard rows.

### 4.6 Metrics package (paper table minimum)

Per method × seed: OA, κ, macro-F1, per-class R (at least kaolinite, alunite, muscovite), n_test, n_train.  
Aggregates: mean±std.  
Optional: McNemar or paired seed-wise ΔOA vs HistGB rich (report #seeds win/lose).

### 4.7 Still forbidden

- Random % pixel train/test as primary claim  
- Full-scene endmember library for “discovery” language  
- Citing HybridSN 99% IP OA as comparable to Cuprite 0.82  
- Claiming CNN failure from MNF-only 15-epoch CPU run  

---

## 5. Acceptable paper-style claims **after** upgrades

### 5.1 Claims you can already almost make (with careful wording)

| Claim | Acceptable? | Caveat |
|-------|-------------|--------|
| Spatial-block multi-seed protocol for Cuprite Tetracorder hard labels | **Yes** | Strength of the work |
| Unsupervised fuse_classical ≈ 0.66 multi-seed / 0.71 full-scene | **Yes** | Report as agreement with Tetracorder, not ore discovery |
| Supervised RF-MNF ≈ 0.79 beats classical spatial | **Yes** | |
| HistGB on refl+MNF+MTMF ≈ 0.82 best **tabular fusion** so far | **Yes if labeled as fusion** | Not “learned spectral SOTA” |
| 1D-CNN MNF ≈ 0.79 under **under-trained** protocol | **Only as preliminary** | Must not imply neural ceiling |

### 5.2 Claims that become acceptable **after** Experiments A–E

| Claim | Requires |
|-------|----------|
| “We evaluate community HSI baselines (1D-CNN, HybridSN, SpectralFormer) under **geographic block CV** on AVIRIS Cuprite multi-class mineral maps.” | B + C actually run |
| “Under spatial hold-out, random-pixel literature OA is **not** reproduced; HybridSN drops to X±Y.” | HybridSN multi-seed |
| “Gradient boosting **fuses** MTMF scores more effectively than RF (+ΔOA).” | Track A as-is + ablations |
| “End-to-end spectral models **without** MTMF achieve OA Z, closing / not closing the gap to fusion.” | Track B |
| “Pseudo-labeling unlabeled pixels improves test-block OA / rare-class recall by …” | Experiment D |
| “Spatial patches **do / do not** improve pure-pixel mineral OA under block CV.” | Experiment B with clear sign |
| “Best supervised system is …; best **spectral-only** system is …” | Dual scoreboard |

### 5.3 Claims that remain **unacceptable** even after upgrades

- “Our model discovers minerals at OA=0.9” with train-block **scene** pure-pixel libraries (still Tetracorder-circular).  
- Any primary comparison to Indian Pines 99% tables.  
- “DL is unnecessary for mineral HSI” if HybridSN/SpectralFormer/SSL were not run **or** only run under starved settings.  
- Product-default replacement of unsupervised fuse by supervised HistGB for unlabeled exploration scenes.

### 5.4 Recommended abstract skeleton (post-upgrade)

> We map AVIRIS Cuprite minerals against Tetracorder hard labels using **spatial block cross-validation**. Unsupervised spectral matching reaches OA≈0.66 multi-seed. Supervised **tabular fusion** of reflectance, MNF, and MTMF with HistGradientBoosting reaches OA≈0.82. We further benchmark **1D-CNN, HybridSN, and SpectralFormer** under the **same** protocol, with a **spectral-only** track that disables MTMF features and an optional **pseudo-label** track on unlabeled pixels. [Insert real outcomes.] These results separate classical-score fusion from spectral representation learning and show that community HSI models must be re-evaluated under geographic hold-out for mineral mapping.

---

## 6. Implementation checklist (aggressive but finite)

| # | Deliverable | Owner path | Done when |
|---|-------------|------------|-----------|
| 1 | Val early-stop + ≥50 ep max in `ml_cnn1d.train_cnn1d` | `ml_cnn1d.py` | val loss curve in artifacts |
| 2 | Feature modes: `cr_swir`, `refl_mnf_mtmf` for CNN | `ml_cnn1d.py` + script | multi-seed summaries |
| 3 | Spectral-only vs fusion tables in `BEST_NUMBERS.md` | docs | two tracks |
| 4 | `ml_hybridsn.py` + `scripts/ml_spatial_hybridsn_baseline.py` | new | 5-seed OA |
| 5 | SpectralFormer research runner (plugin ok) | scripts/ | 5-seed OA |
| 6 | `ml_pseudolabel.py` teacher→student | new | ΔOA vs supervised twin |
| 7 | macro-F1 + worst-seed rare-class in all summaries | evaluate / scripts | report.md columns |
| 8 | Re-rank `BEST_NUMBERS` only after (1–4) | docs | no more “CNN ≈ RF” from 15-ep MNF-only |

**Do not** expand scope to Mamba/FreeNet until HybridSN + tuned 1D + SSL are on disk.

---

## 7. Closing verdict

| Dimension | Grade | Comment |
|-----------|-------|---------|
| Leakage control / spatial protocol | **A** | Best part of the project |
| Classical mineral stack | **A−** | fuse / MTMF / CR are real |
| Tabular supervised fusion | **B+** | HistGB 0.816 is real and useful |
| Community DL engagement | **D** | P0 HybridSN/SpectralFormer absent; 1D-CNN starved |
| Semi-supervised use of unlabeled cube | **F** | ~82% ignore mass unused |
| Fair neural vs tree comparison | **D** | MTMF for trees, MNF-only 15-ep for CNN |
| Ambition vs 2024–2026 HSI field | **Under** | Stopped at “RF/HistGB good enough for product” |

**0.816 is not proof that HistGB is enough.** It is proof that **classical detectors + boosting** work under an honest split — and that the team has **not yet run the experiments that could overthrow that narrative**.

Run the dual-track scoreboard. Feed the CNN. Add patches. Use the unlabeled pixels. Then publish.

---

## References (internal)

| Doc / code | Role in this attack |
|------------|---------------------|
| `docs/BEST_NUMBERS.md` | Headline numbers 0.816 / 0.793 / 0.788 |
| `docs/research_scrapes/HSI_DL_BASELINES_IMPLEMENT_2026.md` | P0 list the project ignored |
| `docs/research_scrapes/OPEN_IMPLEMENTATIONS_2026.md` | MIT HybridSN-pytorch path |
| `docs/research_scrapes/ROUND2_MASTER_INDEX.md` | Implement order abandoned mid-list |
| `docs/ML_RESEARCH_DIRECTION.md` | Explicit “CNN not required” after RF win |
| `docs/RESEARCH_PROTOCOL.md` | Val blocks unused by ML trainers |
| `src/open_ore_mapper/ml_cnn1d.py` | Fixed epochs, no val, no SWIR, no rich features |
| `src/open_ore_mapper/ml_boost.py` / `ml_rf.py` | Shared MTMF-rich tabular path |
| `outputs/research_ml_{cnn1d,boost,rf}/summary.json` | Multi-seed evidence |

---

*Adversarial review for open-ore-mapper research direction. Numbers cited are from local artifacts and project docs as of 2026-07-26; paper OAs from the broader HSI literature remain non-transferable under random-pixel splits.*
