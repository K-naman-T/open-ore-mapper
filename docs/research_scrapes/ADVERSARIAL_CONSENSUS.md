# Adversarial consensus — open-ore-mapper

**Role:** Debate moderator / research director  
**Date:** 2026-07-26  
**Inputs (all read in full):**

| # | Adversary | Path |
|---|-----------|------|
| 1 | Metrics skeptic | `docs/research_scrapes/ADVERSARIAL_METRICS_SKEPTIC.md` |
| 2 | Product realist | `docs/research_scrapes/ADVERSARIAL_PRODUCT_REALIST.md` |
| 3 | ML researcher | `docs/research_scrapes/ADVERSARIAL_ML_RESEARCHER.md` |
| 4 | Classical RS | `docs/research_scrapes/ADVERSARIAL_CLASSICAL_RS.md` |
| — | Current claims | `docs/BEST_NUMBERS.md` |

**Rule of this document:** Consensus is **stricter than any single defender**. Where adversaries conflict on *ambition*, the project **may** keep optional research tracks; where they conflict on *what may be claimed*, the **weaker honest claim wins**. No mushy “both sides are valid” on marketing language.

---

## A. Claims currently implied by `BEST_NUMBERS.md` / recent work

| ID | Implied claim (current wording / framing) |
|----|-------------------------------------------|
| C1 | **HistGB · refl+MNF+MTMF mean OA 0.816 “leads supervised” / is best supervised spatial science** |
| C2 | **Gate pass: HistGB beats RF by +0.028** (RF-MNF 0.788 vs HistGB rich 0.816) |
| C3 | **Boosting with rich features is the current supervised leader** under honest spatial protocol |
| C4 | **1D-CNN ≈ RF on MNF; “no free win from a small net alone”** |
| C5 | **fuse_classical full-scene OA 0.713 is best unsupervised engine** (rank-1 full-scene table) |
| C6 | **fuse multi-seed 0.664 ± 0.092 is the leakage-safer classical reference** |
| C7 | **Product default for unlabeled scenes remains `fuse_classical`** |
| C8 | **Supervised path is for when train regions / GT patches exist** |
| C9 | **“0.82 HistGB rich” = best supervised spatial OA so far** (how-to-read table) |
| C10 | **Full-scene ladder (SAM 0.34 → CR 0.58 → MTMF 0.67 → fuse 0.71) is a single comparable scoreboard** |
| C11 | **Kaolinite R 0.53±0.30 is “noisy, not clearly worse” than RF** (gate secondary) |
| C12 | **Multi-seed 4×4 spatial protocol + 5 seeds is enough for science ranking** |
| C13 | **OA (and κ) is the right primary ranking key** across classical and ML |
| C14 | **All numbers are “real AVIRIS + Tetracorder” science numbers** (vs planted fixture) |
| C15 | **RF/boost/CNN comparison is a fair model bake-off** (implied by ranked supervised table) |
| C16 | **Supervised 0.82 and unsupervised 0.66/0.71 can sit on one “best numbers” ladder without track separation** |

---

## B. Claim-by-claim adjudication

Legend: **M** = metrics skeptic · **P** = product realist · **L** = ML researcher · **C** = classical RS  
Statuses: **CONFIRMED** | **REVISED** | **REJECTED**

### C1 — HistGB 0.816 “leads supervised science”

| Adversary | Stance |
|-----------|--------|
| M | **REJECT** as science win; accept only as Tetracorder-reproduction under closed-set + rich features |
| P | **REJECT** for product/science hero; research artifact only |
| L | **REVISE** → “best **tabular fusion** so far,” not spectral SOTA / not “enough” |
| C | **REJECT** as science; accept only as map-emulator OA |

**Consensus: REVISED → demoted**  
Allowed: *“Under 5-seed spatial blocks, HistGB on train-block pure Tetracorder labels + refl+MNF+MTMF achieved mean OA 0.816±0.025 vs held-out Tetracorder hard labels (closed-set).”*  
Forbidden: “wins science,” “best mineral mapping,” “supervised spatial leader for minerals” without the full clause in the same sentence.

### C2 — Gate pass +0.028 vs RF

| Adversary | Stance |
|-----------|--------|
| M | **REJECT** — feature mismatch (rich vs MNF); paired *t* fails α=0.05; not pre-registered fair comparison |
| P | Irrelevant to product; **REJECT** as demo claim |
| L | **REJECT** as fair model win — deck stacked by MTMF columns for trees |
| C | **REJECT** as scientific victory; competition rule on weak labels |

**Consensus: REJECTED** as a “gate pass.”  
May report **matched-feature** deltas only (e.g. HistGB rich − RF rich mean Δ≈+0.037, n=5 seeds, **no significance claimed** until CI/bootstrap). Must never headline “+0.028 vs RF” without saying RF was MNF-only.

### C3 — Boosting + rich features = supervised leader

| Adversary | Stance |
|-----------|--------|
| M | Accept only with unfair-comparison footnote; on MNF alone ranking flips |
| P | Accept as research note only |
| L | Accept **if labeled fusion / systems track**, not spectral learning |
| C | Accept only as emulator ranking within Track C |

**Consensus: REVISED**  
“Leader” only inside **Track C (supervised map imitation / systems fusion)** with explicit feature set. Dual scoreboard mandatory (see F). On **matched MNF**, no booster crown: CNN 0.793 ≳ RF 0.788 ≳ HistGB 0.780 (all ± large seed noise).

### C4 — 1D-CNN ≈ RF; no free win from small net

| Adversary | Stance |
|-----------|--------|
| M | **REVISE** — comparison incomplete; CNN never got rich stack; MNF-30 vs RF MNF-20 |
| P | Defer further neural work for product; claim is product-irrelevant |
| L | **REJECT** as neural ceiling — 15-ep, no val early-stop, no rich features, no patches |
| C | Neutral/secondary; does not defend “CNN failed” |

**Consensus: REVISED → preliminary only**  
Allowed: *“Under-trained 1D-CNN (15 epochs, MNF-only, no val early-stop) scored mean OA 0.793±0.046, roughly tied with RF-MNF under the same seeds.”*  
Forbidden: “CNN not required,” “neural methods don’t help,” “no free win from nets” as research conclusion.

### C5 — fuse full-scene 0.713 best unsupervised engine

| Adversary | Stance |
|-----------|--------|
| M | Serious issue: semi-leaked messaging; OK as diagnostic with scream footnotes |
| P | **Oversold** if called “71% accuracy”; prefer multi-seed for external Path A |
| L | Accept as classical bar with caveats |
| C | **Valid engineering** of matchers **if labeled semi-dependent**; not library science |

**Consensus: REVISED**  
Internal/diagnostic: full-scene fuse OA **0.713** with **all-pure-GT endmembers** (semi-dependent).  
External / Path A headline: prefer **multi-seed 0.664±0.092**. Never “our accuracy is 71%” without protocol in the same sentence.

### C6 — fuse multi-seed 0.664 leakage-safer classical

| Adversary | Stance |
|-----------|--------|
| M | Accept as unsup reference; not commensurate with supervised OA |
| P | Prefer this over 0.71 for product scorecard |
| L | Accept as fair classical bar |
| C | Honesty rank high among current numbers (still GT-endmember, not independent library) |

**Consensus: CONFIRMED with labels**  
Primary **unsupervised semi-dependent** number under spatial protocol. Still **not** independent library transfer. Still often always-assign for OA (classical/open-set honesty incomplete).

### C7 — Product default = fuse_classical (unlabeled)

| Adversary | Stance |
|-----------|--------|
| M | Accept product separation |
| P | **Strong confirm** — and strengthen library-first hourglass, not ML default |
| L | Accept product default; research must not stop |
| C | **Strong confirm** — industry spine |

**Consensus: CONFIRMED** (binding product rule). Supervised models **must not** become default for bbox/upload/EMIT.

### C8 — Supervised path when train ROIs / GT exist

| Adversary | Stance |
|-----------|--------|
| M | Accept as engineering task (map reproduction) |
| P | **Confirm** — behind a door; optional power feature |
| L | Accept as one track among several |
| C | Confirm as **map emulator / label propagation**, not discovery |

**Consensus: CONFIRMED with language lock**  
Document as: *optional ROI / pure-label map imitation*, never “mineral discovery mode.”

### C9 — “0.82 best supervised spatial OA so far”

| Adversary | Stance |
|-----------|--------|
| M | Reject trophy framing; internal leaderboard only |
| P | Reject user-facing |
| L | Middling floor for pure-pixel closed-set; not solved |
| C | Emulator number only |

**Consensus: REVISED**  
“Highest **closed-set Tetracorder-agreement OA** among supervised runs tried under this protocol (HistGB rich 0.816±0.025).” Not “best science,” not product SLA, not saturated ceiling.

### C10 — Full-scene classical ladder as one scoreboard

| Adversary | Stance |
|-----------|--------|
| M | OK as engine ablation with leakage flags |
| P | Confuses demos if mixed with multi-seed/supervised |
| L | Accept classical progress story |
| C | **Defend ladder as real work** if semi-dependent labeled |

**Consensus: REVISED**  
Keep ladder as **Track B (semi-dependent classical engine ablation)** only. Separate tables from supervised and from independent-library track. Weights 0.7/0.2/0.1 = Cuprite-OA-tuned — state that.

### C11 — Kaolinite R “noisy, not clearly worse”

| Adversary | Stance |
|-----------|--------|
| M | **REJECT** mean that includes seed-42 support=1; statistical malpractice |
| P | Prefer key-mineral reliability with support floors |
| L | Rare-class instability shows method not saturated |
| C | OA-up / diagnostic instability = wrong aggregate |

**Consensus: REJECTED** as gate language.  
Must report **support-aware** kaolinite metrics (exclude seeds with support < N_min, e.g. 50, **or** pool pixels). Seed-42 HistGB rich kao support=1, R=0 → do not average as science.

### C12 — Multi-seed 4×4 / 5 seeds “enough” for science ranking

| Adversary | Stance |
|-----------|--------|
| M | **REJECT** “enough”; better than random pixels only |
| P | Keep as honesty tool for classical claims |
| L | Keep protocol spine; upgrade val use, dual tracks |
| C | Necessary, not sufficient for independence |

**Consensus: REVISED**  
Protocol is **mandatory minimum for relative ranking** on this cube. It is **not** sufficient for absolute mineral accuracy, transfer, or publication-grade method dominance. Treat seed means as fragile geographic lottery (4 test blocks; class absence).

### C13 — OA primary ranking metric

| Adversary | Stance |
|-----------|--------|
| M | **REJECT as primary** for mineral mapping |
| P | One Path A agreement number OK; plus key-mineral + coverage confidence |
| L | Need macro-F1 + rare-class; dual objectives |
| C | OA vs Tetracorder wrong game if sole primary; open-set ops metrics |

**Consensus: REVISED**  
OA remains **one** reported number. Ranking / “win” language requires **also**: macro-F1 (or balanced accuracy), rare/target class recalls with support floors, and for unsupervised: **coverage / unknown rate / precision-on-calls**. Closed-set OA alone cannot declare science winners.

### C14 — “Real AVIRIS + Tetracorder” = science numbers

| Adversary | Stance |
|-----------|--------|
| M | Real data yes; science ceiling no — agreement with algorithm |
| P | Benchmark agreement only |
| L | Real under honest split; incomplete baselines |
| C | Map-to-map agreement genre, not field truth |

**Consensus: REVISED**  
Confirmed: not planted fixture OA=1.0.  
Required framing: **map-to-map agreement with Tetracorder 4.4 fd-max hard labels**, not mineral ground truth.

### C15 — Fair RF / boost / CNN bake-off

| Adversary | Stance |
|-----------|--------|
| M | **REJECT** |
| P | N/A product |
| L | **REJECT** |
| C | Comparison is residual fitting on classical features; fairness secondary |

**Consensus: REJECTED**  
Current supervised ranking is **not** a fair multi-model bake-off. Incomplete factorial (features, MNF *k*, train budget, val selection).

### C16 — One mixed “best numbers” ladder

| Adversary | Stance |
|-----------|--------|
| M | Fatal messaging |
| P | Critical demo risk |
| L | Demands dual/multi track |
| C | Demands split A/B/C scoreboard |

**Consensus: REJECTED**  
`BEST_NUMBERS.md` must **split tracks**. No single rank-1 across unsupervised open/closed, full-scene, and supervised closed-set.

---

## C. Unanimous agreements (4/4)

These are **binding**. No dissent among adversaries on the core substance.

1. **Tetracorder fd-max hard labels are not independent mineral / field / XRD truth.** All OA is map-to-map agreement with an expert-system product (unless later re-labeled).
2. **Nested circularity / semi-dependence:** pure-pixel train labels, often GT-derived endmembers, and MTMF/MNF features in the same spectroscopic family as the teacher → supervised “wins” are largely **teacher imitation / classical-score fusion**, not discovery.
3. **HistGB 0.816 must not be sold as absolute mineral-mapping accuracy, product SLA, or “best science” crown.**
4. **Product default for unlabeled scenes = classical unsupervised path** (`fuse_classical` / library-first hourglass), never HistGB/RF/CNN.
5. **Spatial multi-seed + train-only transforms is real engineering progress** relative to random-pixel and full-scene pure-GT library leakage — keep the spine.
6. **Full-scene fuse 0.713 is semi-dependent**; multi-seed fuse **0.664±0.092** is the more honest classical unsupervised spatial number for external claims.
7. **Language ban:** “detects ore,” “finds deposits,” “82% accurate minerals,” “ML beats classical spectroscopy for ore mapping,” Indian Pines 99% as comparable.
8. **Supervised OA is valid only as:** *how well we reproduce this map product when pure/ROI labels exist in train blocks* — not open exploration success.
9. **Independent external library (USGS/lab) transfer scoring is missing** from the primary science story and is required for integrity (unanimous on need; intensity of “primary metric” varies but no adversary defends GT-only forever).
10. **Do not surface supervised 0.82 or bare 0.71 in UI/README hero without full protocol in the same breath**; Path B (no GT) shows **no OA**.

---

## D. Majority agreements (3/4)

| Agreement | Yes | Soft / partial no |
|-----------|-----|-------------------|
| **+0.028 gate is invalid / unfair** | M, L, C | P: irrelevant rather than statistically litigated |
| **OA alone is wrong sole ranking key** | M, L, C | P: allow one Path A OA + two other product metrics |
| **Closed-set always-assign inflates supervised vs gated classical** | M, C, P | L: notes task difference; prioritizes feature parity |
| **CNN baseline is under-cooked; cannot conclude neural failure** | M, L, (C secondary) | P: **defer** neural polish for product opportunity cost |
| **Split scoreboards (library / semi-dep classical / supervised)** | M, C, P, L all lean yes | L splits further (spectral vs fusion vs patch vs SSL) |
| **Rare-class / support-aware metrics required** | M, L, C | P: 4–6 exploration-critical classes as product metric #2 |
| **Stop further pure horse-race for +0.01 OA past HistGB** | M (multiplicity), P (kill), C (vanity) | L: replace horse-race with **fair** community baselines, not more boosters |
| **Classical ladder (SAM→CR→MTMF→fuse) was the real spectroscopy progress** | C, P, M | L: agrees classical is strong; rejects stopping research there |
| **Cap-2000 / dead val split / multiplicity are serious issues** | M primary; L (val, budget); C (weights OA-tuned) | P less detailed |
| **Seed-42 kao n=1 must not poison means** | M; L/C/P accept once stated | — |

---

## E. Live tensions (unresolved — explicit)

| Tension | Pole A | Pole B | Moderator resolution (binding until new evidence) |
|---------|--------|--------|-----------------------------------------------------|
| **Next dollar of effort** | **P:** library packs + EMIT Path B + one unsupervised preset | **L:** fair CNN + HybridSN + SSL under spatial protocol | **Product P0 first** (library, default preset, Path A one number, EMIT land). **Research P0** after or in parallel only if free: feature-parity CNN + scoreboard split — **not** HybridSN before library ships. HybridSN/SpectralFormer = **research optional**, never product blocker. |
| **Is 0.816 “good” or “low”?** | L: middling floor; expect ≥0.88 if solved | M: internal leaderboard; C: wrong game | **Neither trophy nor shame number.** Report as emulator agreement; do not use “solved” or “SOTA mineral OA.” |
| **Must community DL be run?** | L: yes or cannot claim DL unnecessary | P: kill/defer; C: not science primary | **May not claim “DL unnecessary / CNN fails.”** **Need not** implement HybridSN to ship product. Fair 1D-CNN (val early-stop, ≥50 ep, feature parity) is the **minimum** if any neural claim remains in docs. |
| **Primary science metric** | C: independent library + open-set | M: stats + macro/rare + independent labels | **Both required for “science integrity.”** Independent library track is **primary unsupervised science**; spatial Tetracorder OA is **engine ablation / emulator**. |
| **fuse always-assign for OA** | C/M: geologically dishonest | Scoreboard culture wants high OA | **Ops/product maps:** restore unknown gates as default QA. **Research OA rows:** may report always-assign **only if labeled** and paired with open-set operating point. |
| **SSL / pseudo-labels** | L: high value on 82% unlabeled | P: only if improves unlabeled maps | Allowed if it improves **hold-out** or **library-transfer** maps; forbidden if it only pumps Tetracorder OA with test leakage. |

---

## F. Binding consensus decisions

### F1. What we **may** claim

| Claim class | Allowed wording pattern |
|-------------|-------------------------|
| Supervised HistGB | “Mean OA **0.816±0.025** (5 seeds, 4×4 blocks) reproducing **Tetracorder fd-max hard labels** on test blocks, trained on **train-block pure GT** with **refl+MNF+MTMF**, **closed-set**.” |
| Matched MNF trees/CNN | “On **MNF-only**, RF / HistGB / under-trained 1D-CNN are **within ~0.01–0.02 mean OA**; no method dominates.” |
| Classical multi-seed | “Unsupervised **fuse_classical** mean OA **0.664±0.092** with **train-block GT-conditioned endmembers** (semi-dependent map agreement).” |
| Classical full-scene | “Full-scene fuse OA **0.713** using **all pure-GT endmembers** — diagnostic / semi-dependent, not transfer.” |
| Product | “Default unlabeled mapping is classical fusion / library matching; supervised models require user labels.” |
| Progress | “Classical ladder improved Tetracorder agreement from SAM ~0.34 to fuse ~0.71 (full-scene semi-dependent).” |

### F2. What we **must stop claiming**

| Stop | Why |
|------|-----|
| “HistGB **wins science** / supervised spatial **leader** for mineral mapping” | Unanimous overclaim |
| “**Gate pass +0.028** vs RF” without feature mismatch + no significance | Invalid comparison |
| “**0.82 accurate** minerals / product accuracy” | Labels + closed-set + one site |
| “**71% accuracy**” without semi-dependent + endmember clause | Oversell |
| “**1D-CNN fails** / CNN not required / nets don’t help” | Under-trained, under-featured baseline |
| “**ML beats classical** for exploration mapping” | Different tasks (labels vs no labels); circular teacher |
| Single ladder ranking **HistGB #1** over **fuse #1u** as better mapper for unlabeled scenes | Incommensurable |
| Kaolinite means that **include n=1 seeds** as gate evidence | Malpractice |
| Any OA on **EMIT/upload without GT** | No reference |
| Fixture **OA=1.0** as science proof | Poison |

### F3. Scoreboard structure (mandatory rewrite of `BEST_NUMBERS` framing)

| Track | Name | What is allowed | Headline metric |
|------:|------|-----------------|-----------------|
| **A** | **Library science** (primary unsupervised science) | Fixed USGS/lab CSV; **no** GT pure endmembers; open-set preferred | Transfer agreement + precision-on-calls + coverage |
| **B** | **Semi-dependent classical** | Train-block or full-scene GT endmembers; SAM/CR/MTMF/fuse | Multi-seed OA±std **and** open-set ops point |
| **C** | **Supervised map imitation** | Train pure GT labels; RF/HistGB/CNN; feature set stated | OA±std **and** macro-F1 / support-aware rare-class |
| **D** (optional research) | **Spectral / SSL / patch** | Fair neural parity; no MTMF columns for spectral-only subtrack | Same seeds; never averaged into C as “DL failed” |

**Never average tracks. Never one rank column across A–C.**

### F4. What to do next (priority order)

| Pri | Action | Satisfies |
|----:|--------|-----------|
| **1** | **Rewrite claims** in `BEST_NUMBERS.md` / research summaries per claim diff (below); strip gate-pass language; split tracks | All 4 |
| **2** | **Curated real library packs** + fail closed without demo spectra; freeze **one** unsupervised product preset | P, C |
| **3** | **Path A demo:** one agreement number (prefer multi-seed classical) + provenance; **Path B:** no OA; EMIT progress/georef | P |
| **4** | **Independent library Cuprite score** (Track A) for fuse/SAM/MTMF — even if OA drops | C, M, P |
| **5** | **Metrics package:** support-aware rare-class; macro-F1; open-set coverage; exclude/flag low-support seeds | M, L, C |
| **6** | **If neural rows remain in docs:** val early-stop, ≥50 ep max, feature parity (`refl_mnf_mtmf` or mark fusion-only) | M, L |
| **7** | **Optional research:** HybridSN / SpectralFormer / SSL **only after** 1–5; no product dependency | L (scoped), P (defer) |
| **8** | **Do not:** more booster horse races for +0.01 OA; HistGB as default classifier; GPL DeepHyperX in core | P, M, C |

### F5. Statistical / protocol hygiene (minimum)

- Pre-register **primary comparison** before new model families (matched features).
- Report **paired seed-wise Δ** with **95% CI or bootstrap**; no “pass” without it.
- Val blocks used for early-stop / hyperparams; test once.
- Document `max_train_samples_per_class=2000` as conditional.
- Provenance fields: `label_source`, `library_source`, `closed_set`, `feature_set`.

---

## G. One-paragraph truth (binding)

> open-ore-mapper has a **real classical mineral-mapping stack** (continuum/region SAM, MTMF, MNF geometry, `fuse_classical`) that raises **map-to-map agreement with Tetracorder 4.4 hard labels** on AVIRIS Cuprite from weak full-library SAM (~0.34) to **~0.71 full-scene** and **~0.66±0.09 under spatial multi-seed hold-out** with train-block GT-conditioned endmembers—progress that is **engineering of spectral matchers**, still **semi-dependent** on Tetracorder purity, and **not** independent USGS-library transfer or field-validated discovery. The supervised ladder (RF / LightGBM / HistGB / under-trained 1D-CNN) shows that, **when pure Tetracorder labels exist in train blocks**, closed-set tabular models can **reproduce that same map** at mean OA up to **~0.82** (HistGB on reflectance+MNF+MTMF); that number is a **map-emulator / classical-score fusion** result under a fragile 4×4 block lottery—not a fair neural bake-off, not a statistically gated win over RF, not product accuracy, and not proof that boosting “solved” mineral mapping. **Unlabeled exploration** (the actual product) must default to **library-first classical mapping with honest unknowns and no OA theater**; research integrity requires a **split scoreboard**, **support-aware mineral metrics**, and an **independent library track** before any further model crowns.

---

## H. Claim diff — OLD (`BEST_NUMBERS`) → CONSENSUS wording

| Location / OLD wording | CONSENSUS wording |
|------------------------|-------------------|
| Supervised table **Rank 1** HistGB … **leads** | **Track C only:** HistGB · refl+MNF+MTMF **0.816±0.025** — highest **closed-set Tetracorder-agreement OA** among supervised runs tried; **not** science crown across tracks |
| “**HistGradientBoosting … leads** (mean OA **0.816**), beating RF-MNF (**0.788**) by ~0.03” | “HistGB **rich features** reaches **0.816±0.025**. **Do not** compare to RF-MNF as a model win. On **matched MNF**, HistGB **0.780**, RF **0.788**, 1D-CNN **0.793** — **tied within noise**.” |
| Gate: vs RF +0.02 → **pass (+0.028)** | **Gate retired.** Optional note: “Unmatched feature stacks; paired test vs RF-MNF was **not** significant at α=0.05 on 5 seeds; not a valid pass.” |
| “**boosting with rich features** is the current **supervised leader**” | “Best **tabular fusion emulator** under Track C so far (rich classical features + labels).” |
| “**1D-CNN ≈ RF**; no free win from a small net alone without richer features/more train” | “**Preliminary:** 15-epoch MNF-only 1D-CNN **0.793±0.046** ≈ RF-MNF. **Not** a neural ceiling; rich features / val early-stop / patches **not** evaluated.” |
| How-to-read: “**0.82 HistGB rich** = **Best supervised spatial OA so far**” | “**0.816 HistGB rich** = highest **Track C** Tetracorder-agreement OA under this protocol (closed-set, pure-GT train, refl+MNF+MTMF).” |
| How-to-read: “**0.71 fuse full-scene** = Best **unsupervised engine** mapping OA” | “**0.713 fuse full-scene** = best **Track B diagnostic** full-scene OA with **all pure-GT endmembers** (semi-dependent).” |
| How-to-read: “**0.66 fuse multi-seed** = Fuse under spatial hold-out” | “**0.664±0.092 fuse multi-seed** = primary **Track B** unsupervised spatial agreement (train-block endmembers).” |
| “Product default … remains `fuse_classical`” | **Keep / strengthen:** product default unlabeled = classical fusion; **never** surface HistGB OA as the product accuracy. |
| “Supervised path is for when train regions / GT patches exist” | **Keep + lock:** optional **map imitation / ROI labels** mode — not discovery. |
| Kaolinite gate: “**noisy, not clearly worse**” | “Kaolinite recall **unstable** (e.g. seed 42 support=**1**); **do not** use unfiltered seed-mean R as a gate.” |
| Single full-scene + supervised rank tables without track labels | **Split** Track A (library — TBD) / B (semi-dep classical) / C (supervised emulator); **no cross-track rank**. |
| Conclusion mixing “HistGB leads supervised” with product fuse default without screaming separation | Open with: “**Three incommensurable regimes:** library transfer (missing), semi-dependent classical, supervised map imitation. Numbers below are **not** one ladder.” |

### Minimal replacement “Interpretation” block (paste-ready)

```markdown
**Interpretation (adversarial consensus 2026-07-26)**

- All OAs are **agreement with Tetracorder 4.4 fd-max hard labels**, not field-validated mineral truth.
- **Track B:** unsupervised `fuse_classical` multi-seed **0.664±0.092** is the honest spatial classical reference (GT-conditioned endmembers). Full-scene **0.713** is semi-dependent diagnostic only.
- **Track C:** HistGB · refl+MNF+MTMF **0.816±0.025** is the best **closed-set map-emulator / classical-score fusion** result so far when train-block pure labels exist — **not** a fair win over RF, **not** product accuracy, **not** proof spectral DL failed.
- On **matched MNF features**, RF / HistGB / under-trained 1D-CNN are **tied within seed noise**.
- **Product default** for unlabeled cubes remains classical unsupervised mapping; supervised models stay optional behind labels.
- **Missing Track A:** independent USGS/lab library transfer + open-set metrics — required before any “science complete” claim.
```

---

## I. Severity summary (moderator)

| Severity | Items locked |
|----------|----------------|
| **Fatal overclaims (remove now)** | HistGB “wins science”; +0.028 gate pass; 0.82 as mineral/product accuracy; mixed single ladder |
| **Serious (fix framing)** | Feature-unfair supervised rank; OA-only ranking; seed-42 rare-class means; always-assign vs open-set scoreboard; full-scene 0.71 external use |
| **Keep as strengths** | Spatial multi-seed protocol; train-only MNF/MTMF; classical ladder implementation; product fuse default sentence; “not fixture OA=1.0” |
| **Ambition split** | Product ships library/EMIT; research may later fair-CNN/HybridSN/SSL **without** changing product claims |

---

## J. Sign-off rule

Any future PR that adds a higher OA to `BEST_NUMBERS.md` must:

1. Name the **track** (A/B/C/D),  
2. State **label_source** and **library_source**,  
3. Use **matched features** for model comparisons,  
4. Report **support-aware** secondary metrics,  
5. **Not** change product default without product review.

Until then, treat **0.816** and **0.713** as **protocol-conditioned Tetracorder agreement**, not truth.

---

*End of adversarial consensus. Stricter than any single brief: weaker claims, split scoreboards, product library-first, research honesty before crowns.*
