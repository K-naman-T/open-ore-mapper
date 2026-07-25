# Adversarial product / mining-ops realist review

**Target:** open-ore-mapper research-first path  
**POV:** first-time user + exploration product, not Kaggle leaderboard  
**Date:** 2026-07-26  
**Status:** attack doc — intentionally blunt  

Sources in-repo (not invented):  
`README.md`, `README.md`, `docs/BEST_NUMBERS.md`, `docs/DEMO_READINESS_PLAN.md`, `docs/RESEARCH_PIPELINE_RESULTS.md`, `docs/RESEARCH_PROTOCOL.md`, `docs/ML_RESEARCH_DIRECTION.md`, `docs/research_scrapes/INDUSTRY_MINERAL_BASELINE_2026.md`, `docs/research_scrapes/ROUND2_MASTER_INDEX.md`, `docs/research_scrapes/industry/EarthDaily_EnMAP_vs_SpecTIR_Cuprite_2024.md`, `frontend/src/pages/MapView.tsx`.

---

## 0. One-line verdict

You built a **Cuprite Tetracorder agreement gym** and a **supervised leaderboard** (HistGB **0.82** OA multi-seed). The product a first user actually needs is: **library map on an unlabeled cube / EMIT bbox**, with honest QA, not a model that only wins when pure GT pixels exist for training or endmember theft.

**Research is not product.** The master plan said that. The research path ignored it.

---

## 1. Supervised 0.82 OA is irrelevant to product without labels

### What the number actually is

From `docs/BEST_NUMBERS.md`:

| Claim | Protocol reality |
|-------|------------------|
| HistGB refl+MNF+MTMF **0.816 ± 0.025** | Spatial multi-seed **supervised** train on pure Tetracorder labels in train blocks |
| RF / LightGBM / 1D-CNN ~**0.79** | Same: **needs labeled pixels** |
| fuse_classical **0.664** multi-seed | Unsupervised spectral matching (no train labels) |
| fuse_classical **0.713** full-scene | Unsupervised but **endmembers from pure GT** — not “drop cube and go” |

first-time user has:

- No Tetracorder raster for their AOI  
- No train blocks  
- No pure-pixel GT  
- Often no field spectra  

So **0.82 is a research ceiling on a labeled protocol**, not a product SLA. Showing “best model 82%” next to a Map Minerals button is **bait-and-switch**.

### Product translation

| User situation | What runs | Honest accuracy story |
|----------------|-----------|------------------------|
| Try Cuprite benchmark with reference | fuse / classical + scorecard | “Agreement vs expert map under stated options” |
| Upload random cube | library / scene-endmember matching | **No OA** — confidence + “candidates only” |
| Draw EMIT bbox | same, 60 m mixing | **No OA** — coarser sensor warning |
| Has ROI / XRF / field ASD | supervised fine-tune *optional later* | Only then cite supervised OA |

Industry already said this: ops defaults are hourglass / SAM / MTMF / Tetracorder-class feature systems for **unlabeled** exploration; DL/ML is site-specific when labels exist (`INDUSTRY_MINERAL_BASELINE_2026.md` §2.1–2.3, `ROUND2_MASTER_INDEX.md` “two baselines”).

**Verdict:** Keep HistGB as a **research artifact**. Never put 0.82 on the home path. Never call it “the best model” in UI copy.

---

## 2. Too much Cuprite Tetracorder leaderboard; too little shippable EMIT path

### What the master plan promised the first-time user

`README.md` §0–1:

1. Pick a place **or drop a cube**  
2. Run mineral spectral matching  
3. Judge quality against known GT **on the benchmark path**  
4. Then expand  

Phase order: scoreboard (0) → better engine (1) → UI comparison (2) → **“Map any region” EMIT (3)**.

Demo plan Path A (Cuprite scorecard) is required; Path B (bbox → EMIT) is the **product story** (`DEMO_READINESS_PLAN.md`).

### What research actually optimized

From `BEST_NUMBERS.md` / `RESEARCH_PIPELINE_RESULTS.md`:

- Full-scene OA ladder: SAM 0.34 → CR 0.58 → MTMF 0.67 → **fuse 0.71**  
- Spatial multi-seed classical + **RF → LightGBM → HistGB → 1D-CNN** horse race  
- Artifacts: `outputs/research_ml_*`, `research_spatial_*`, cuprite-real-eval  

That is **map-to-map agreement engineering against Tetracorder 4.4 hard labels** on one AVIRIS 1995 cube. Useful science. Wrong primary allocation for an exploration product.

### What first users still hit

From `README.md` + master plan “current truth”:

| Product gap | Status |
|-------------|--------|
| Side-by-side GT scorecard as default first run | Fragile / fixture-centric (MapView scorecard exists when API returns one) |
| Real bundled library (USGS pack) | Still the real product bottleneck |
| EMIT bbox: progress UI, WGS84 georef, worker isolation | Documented **experimental** with hard limits |
| First-tile QC only on EMIT path | Honesty hole |
| Unwired UI toggles (CR default, ACE, veg, SUnSAL) | Still confuse demos |
| Demo spectra | Still toxic if anyone runs “real” minerals without library |

**You climbed the Cuprite ladder while the shippable path (curated library + one honest classical default + EMIT job that finishes and lands on the globe) stayed half-wired.**

Industry commercial story (EarthDaily 2024 Cuprite): PCA/MNF → **in-scene endmembers** → **SAM** → qualitative vs Swayze maps — **no OA leaderboard**, no HistGB (`industry/EarthDaily_EnMAP_vs_SpecTIR_Cuprite_2024.md`). That is what exploration buyers recognize.

---

## 3. Industry does not ship HistGB on pure GT; they ship library maps

### Ops stack (your own research)

`INDUSTRY_MINERAL_BASELINE_2026.md` ranks operational commonality:

1. Reflectance + bad bands  
2. **SAM**  
3. **MNF**  
4. PPI / endmembers  
5. **MTMF**  
6. **SFF / continuum**  
7. **Tetracorder**-class feature systems (EMIT mineral products lineage)  
…  
11. Deep learning — **rare as unsupervised exploration default**

Recommended product default in that same doc (§6):

- Curated USGS subset (≤30)  
- MNF + endmember extract + ID via SFF/SAM  
- **Primary map: SAM on identified endmembers**  
- **Secondary: MTMF scores + infeasibility**  
- QA layers industry understands  

**Not:** train HistGradientBoosting on pure Tetracorder pixels and paint the rest of the world.

### What “library maps” means in product language

| Deliverable | User sees |
|-------------|-----------|
| Class / best-match mineral | Colored map from library or named endmembers |
| Rule / angle / MF score | Confidence or detection strength |
| Unidentified / low confidence | Explicit “don’t pretend” class |
| Provenance | Library source, thresholds, sensor |

Mining RS vendors (SpecTIR service maps, Marigold-style cloud, EMIT mineral products) sell **alteration indicator maps**, not “we beat RF by +0.03 OA on spatial blocks.”

Your supervised path **requires the thing exploration does not have** (dense pure labels). Your unsupervised fuse path still often **cheats toward Tetracorder** by building endmembers from pure GT pixels (full-scene 0.71 protocol). Protocol doc already admits: that is **reproducibility vs Tetracorder**, not independent mineral discovery (`RESEARCH_PROTOCOL.md`).

---

## 4. “Best model” narrative confuses demos

### The scoreboard mess

| Number | Where it lives | What demos will say | What it actually is |
|--------|----------------|---------------------|---------------------|
| **0.82** HistGB | BEST_NUMBERS supervised | “Our model is 82% accurate” | Labeled spatial hold-out only |
| **0.79** RF / CNN | same | “ML works” | Same label dependency |
| **0.71** fuse full-scene | BEST_NUMBERS + scoreboard | “71% on Cuprite” | Semi-dependent endmembers from all pure GT |
| **0.66** fuse multi-seed | science protocol | Often omitted | Honest-er classical unsupervised |
| **1.00** demo fixture | scoreboard | Silent poison | Planted synthetic GT |
| **0.34** default SAM+NNLS | README still “default path” historically | “Why is my map garbage?” | Full-library / weak path |

MapView already puts a **huge overall accuracy %** in the scorecard panel (`MapView.tsx`). That is correct for Path A **if** provenance screams “vs reference labels.” It is **fatal** if the same visual language is reused for EMIT or upload without GT.

### Confusion mechanisms

1. **Multiple “best”s** — 1s HistGB vs 1u fuse in `RESEARCH_PIPELINE_RESULTS.md` teaches agents to chase OA, not ship.  
2. **Full-scene vs multi-seed** — demos quote 0.71; science papers should quote 0.66; users hear “seventy percent.”  
3. **Tetracorder as truth** — industry baseline itself warns map-to-map OA inflates when methods are same spectroscopy family (Wei 2017 94% etc. are **not** XRD grids).  
4. **Fixture OA=1.0** next to real Cuprite rows trains the team that scorecards “work” without science.  
5. **Default path drift** — README still centers SAM+NNLS as “works today”; research elevates fuse/MTMF; UI may still show Continuum Removal. Three truths → one confused demo.

**Demo rule:** One number on screen per path. Path A: multi-seed or ROI agreement vs named reference. Path B: **no OA**. Period.

---

## 5. What should have been prioritized instead

Ordered by first-time user value (not research ego):

| Pri | Work | Why |
|----:|------|-----|
| **P0** | **Curated real library packs** (USGS hydrothermal / FeOx / carbonate) + fail closed without demo spectra | Without this, every real cube is nonsense with high confidence (master plan “critical scientific failure mode”) |
| **P0** | **One unsupervised product default** = hourglass-lite: curated library **or** auto endmembers + SAM/MTMF secondary — freeze as named preset | Matches industry §6; stop algorithm buffet |
| **P0** | **Path A demo only:** Try Cuprite → Ours \| Ref \| Diff → **one** OA with caveats | project plan / DEMO_READINESS already correct |
| **P1** | **Ship EMIT bbox Path B:** real progress, worker, WGS84 overlay, “no GT” UI | This *is* the product story for non-experts |
| **P1** | **EMIT over Cuprite** secondary score (expect drop at 60 m) | T3 on ground-truth ladder — proves satellite path honesty |
| **P1** | Kill or hide unwired toggles; single classifier truth in API/UI/README | Demo credibility |
| **P2** | Lab-library-only Cuprite score (no scene pure-GT endmembers) | True transfer story for “library maps” |
| **P2** | QA layers: angle rule, MTMF infeasibility, mask, endmember plots | What ops geologists trust more than OA |
| **P3** | Supervised mode **behind a door**: “I have training ROIs” | Only then HistGB/RF is product-relevant |
| **Defer** | HybridSN / SpectralFormer / more boosters past HistGB | Round-2 already said RF→LGBM→1D-CNN; 0.82 is enough research ceiling |

**Research that *did* help product:** wiring MTMF, MNF-SAM, continuum, fuse_classical, spatial protocol honesty.  
**Research that mostly did not:** stacking HistGB vs LightGBM vs CNN for +0.03 OA when the unlabeled default is still the only path that ships.

---

## 6. Is fuse 0.71 full-scene oversold?

**Yes — as a product claim. Partially yes — even as science marketing.**

### What 0.71 is good for

- Shows classical fusion beats raw SAM (0.34) and standalone CR (0.58) on this cube  
- Internal engine bar for unsupervised stack  
- Reasonable **upper** map-to-map agreement under favorable endmember construction  

### Why it is oversold if you say “71% accurate mineral mapping”

| Issue | Detail |
|-------|--------|
| **Label source** | Tetracorder hard labels — expert spectral system, not independent assays (`RESEARCH_PROTOCOL.md`) |
| **Endmember dependency** | Full-scene pure GT endmembers → semi-circular vs the reference family |
| **Protocol drop** | Multi-seed train-only endmembers → **0.66 ± 0.09** — that is the number to defend |
| **No transfer** | Not lab-library-only; not EMIT; not new district |
| **Class balance / hard minerals** | Hematite etc. remain weak in per-class tables; OA hides pain |
| **Always-assign culture** | High OA from forcing classes on pure-labeled pixels ≠ good exploration map with “unknown” |

Industry does not lead demos with a single OA against Tetracorder. EarthDaily’s 2024 Cuprite piece uses **qualitative GSD and species purity** language — no overall accuracy % — and stresses unsupervised discovery is harder than mapping known sites.

**Recommended language:**

- **Internal:** “fuse_classical full-scene OA 0.71 (GT-endmember, Tetracorder agreement)”  
- **External Path A:** “~0.66 mean spatial-holdout agreement with expert map using train-block endmembers; see per-mineral bars”  
- **Never:** “Our accuracy is 71%” without the protocol clause in the same sentence  

---

## Product risk ranking

| Rank | Risk | Severity | Why it kills product |
|-----:|------|----------|----------------------|
| **R1** | **Demo spectra / missing real library** as silent default | Critical | Confident garbage maps on real cubes and EMIT |
| **R2** | **Surfacing supervised 0.82 or full-scene 0.71 as “the accuracy”** | Critical | Trust collapse after first unlabeled AOI |
| **R3** | **EMIT path half-shipped** (georef, workers, progress, first-tile QC) | High | Path B is the viral product story; broken = toy |
| **R4** | **Unwired UI / three default truths** (README SAM, research fuse, UI CR) | High | First-user demo fails live |
| **R5** | **Scorecard OA UI reused without GT** | High | Fake scientific credibility |
| **R6** | **Overfitting roadmap to Cuprite Tetracorder** | Medium–High | Methods that only work with pure labels / one site |
| **R7** | **ML feature creep** (HybridSN, SpectralFormer, more seeds) | Medium | Opportunity cost vs library + EMIT + QA |
| **R8** | **Claiming discovery / ore** language anywhere | Medium | Legal / scientific blowback (docs already warn; keep rigid) |
| **R9** | **Fixture OA=1.0 mixed into human-facing scoreboards** | Medium | Team self-deception |
| **R10** | **License landmines** (ECOSTRESS bundle, GPL DeepHyperX in core) | Medium | Industry baseline already flagged |

---

## Claims that are dangerous to show users

Do **not** put these in UI, README hero, pitch, or demo script without heavy caveats **in the same breath**:

1. **“82% accurate” / “best model HistGB 0.82”** — labels required; not product default.  
2. **“71% on Cuprite”** without saying Tetracorder agreement + GT-derived endmembers / full-scene protocol.  
3. **Any OA on EMIT bbox or arbitrary upload** — no reference → no OA.  
4. **“Detects ore” / “finds deposits” / “confirms mineral presence”** — project already forbids; enforce.  
5. **UI classifier options that do nothing** (or do something different from the label).  
6. **Confidence as probability of mineral truth** — it is match score / fusion weight, not calibrated P(ore).  
7. **Abundance as grade / assay** — NNLS/MTMF scores are relative.  
8. **Demo fixture “100%”** as proof the science works.  
9. **Literature 90–95% Cuprite OA** (Wei-style map-to-map) as if it were your product SLA.  
10. **“Unsupervised 0.71 ≈ industry Tetracorder”** — different systems; circular risk.

**Safe user-facing claims:**

- “Candidate surface spectral matches; field validation required.”  
- “On the Cuprite benchmark, agreement with published expert mineral maps under [method, library, protocol].”  
- “No ground truth for this AOI — showing match confidence only.”  
- “Coarser satellite pixels mix materials; expect less pure species maps than airborne.”

---

## Recommended product scoreboard (3 metrics max)

Kill the research zoo for product. **Three metrics only.**

| # | Metric | Where used | Definition |
|---|--------|------------|------------|
| **1** | **Benchmark agreement (Path A only)** | Cuprite (or frozen site) scorecard | **Spatial multi-seed mean OA ± std** vs named reference (prefer train-only endmembers / lab library variants reported separately). Show **one** headline number + kappa. Prefer **0.66-class** honesty over full-scene 0.71. |
| **2** | **Key-mineral reliability** | Same scorecard, secondary | **Mean recall (or F1) on 4–6 exploration-critical classes** (e.g. alunite, kaolinite, muscovite/illite, calcite, chalcedony/silica, Fe-oxide pack) — not full OA-driven rare class noise. |
| **3** | **Coverage confidence (all paths)** | Every map including EMIT/upload | **% of valid pixels above match threshold** (or mean top-match score) + **% masked/unknown** — *not* accuracy. Labels: “how much of the scene we dared to paint.” |

**Explicitly not product metrics:** HistGB OA, RF OA, CNN OA, full-scene always-assign OA, fixture OA, paper Indian Pines OA.

Optional power-user fourth (never hero): lab-library-only Cuprite OA for transfer honesty.

---

## Kill / keep / defer — ML work

### KILL (stop burning cycles)

| Item | Reason |
|------|--------|
| Further **model horse races** past HistGB (more boosters, hyperparam sweeps for +0.01 OA) | Product-irrelevant without labels |
| **HybridSN / SpectralFormer / SSRN / Mamba** “because literature” | Round-2: only if beat 0.82 under *our* protocol; still label-locked; GPL risk on some code |
| **Full-scene supervised paint** using all pure GT as train then claiming map quality | Leakage theater |
| Wiring **ml_boost as default classifier** for bbox/upload | Will fail or hallucinate structure without labels |
| Scraping more DL READMEs for vanity baselines | Opportunity cost |

### KEEP (product-aligned)

| Item | Reason |
|------|--------|
| **fuse_classical / MTMF / MNF-SAM / CR** as unsupervised engine pieces | Industry-aligned; already wired |
| **Spatial multi-seed protocol** as honesty tool for *classical* claims | Prevents lying to yourselves |
| **Evaluate + Path A scorecard** (Ours/Ref/Diff) | Master-plan north star |
| **Curated library + endmember ID** research if it improves **unlabeled** maps | This *is* product |
| **RF/HistGB as optional “I have ROIs” mode** (API flag, off by default) | Legitimate power feature later |
| **Semi-supervised / pseudo-label from MTMF high-confidence** *only if* it improves unlabeled full-scene maps under hold-out | Rare case where ML helps exploration |

### DEFER (after library + EMIT ship)

| Item | Trigger to reopen |
|------|-------------------|
| 1D-CNN productization | Supervised mode exists + RF/HistGB insufficient on rare classes |
| EMIT↔AVIRIS domain adaptation | Path B works; Cuprite EMIT T3 scored |
| Active learning from field GPS/XRF | Real field workflow users |
| HybridSN-class patches | Dense labels + 0.82 still not enough for a paid supervised tier |

---

## Blunt closing

The team did real classical work and an honest spatial ML ladder. Good science hygiene (`RESEARCH_PROTOCOL.md`) exists on paper. The failure mode is **product selection**:

- **Optimized:** agreement with Tetracorder on one famous cube + supervised OA.  
- **Under-built:** library-first maps, one honest default, EMIT path that a non-expert can finish, QA language that matches industry.

Industry ships **library / endmember maps**. Academia ships **0.82 OA tables**.  
Your README still apologizes that most toggles are fake while `BEST_NUMBERS.md` celebrates HistGB.

**Next dollar of effort:** real spectra pack + freeze unsupervised preset + Path A demo one number + Path B EMIT that lands on the map.  
**Not:** another multi-seed model to beat 0.816.

If you cannot explain to a first-time user, in one sitting, **what runs on a place with no labels** and **why they should not trust a single accuracy %** — you do not have a product. You have a Cuprite lab notebook with a React shell.

---

## Appendix — claim → source map

| Claim in this attack | Source |
|----------------------|--------|
| HistGB 0.816 multi-seed; fuse 0.713 / 0.664 | `docs/BEST_NUMBERS.md` |
| Ops stack classical not DL | `docs/research_scrapes/INDUSTRY_MINERAL_BASELINE_2026.md` |
| Two baselines unsupervised vs supervised | `docs/research_scrapes/ROUND2_MASTER_INDEX.md` |
| Commercial Cuprite = SAM + in-scene endmembers, no OA% | `docs/research_scrapes/industry/EarthDaily_EnMAP_vs_SpecTIR_Cuprite_2024.md` |
| Product north star / phases / scoreboard | `README.md` |
| Path A vs B demo | `docs/DEMO_READINESS_PLAN.md` |
| EMIT experimental limits; SAM default; unwired features | `README.md` |
| Label circularity / endmember leakage | `docs/RESEARCH_PROTOCOL.md` |
| Scorecard UI big OA | `frontend/src/pages/MapView.tsx` |
| Research prioritizes HistGB as 1s | `docs/RESEARCH_PIPELINE_RESULTS.md` |
