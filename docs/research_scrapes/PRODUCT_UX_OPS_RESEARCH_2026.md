# Product UX / Ops Research — first-time user (2026)

**POV:** adversarial product realist. No ML horse races.  
**Sources:** `README.md`, `README.md`, `docs/DEMO_READINESS_PLAN.md`, `docs/research_scrapes/ADVERSARIAL_PRODUCT_REALIST.md`, `docs/research_scrapes/INDUSTRY_MINERAL_BASELINE_2026.md`, `frontend/src/pages/Home.tsx`, `MapView.tsx`, `components/map/SettingsPanel.tsx`, `components/input/AdvancedOptions.tsx`, `components/sidebar/StatisticsTab.tsx`.

---

## 1. What the first-time user sees today

### README hero vs engine truth

| Surface claim | Reality |
|---------------|---------|
| “candidate surface mineral signature maps” + “does **not** detect buried ore” (`README.md` L3–5) | Correct; keep. |
| “CLI … Stable” / “SAM + NNLS … Default path” | True for engine. |
| “React/TypeScript frontend … In development” | Honest status. |
| README screenshot caption lists **Continuum Removal, SAM**, ACE, vegetation mask | ACE/veg still unwired; CR historically mis-defaulted (`README.md` L25–36, L162). |
| Bundled demo library “**Not safe for scientific use**” | Correct — but UI defaults still look like real Fe-oxides. |

### UI first run (Home)

Walkthrough (`Home.tsx` L139–146):

- “This tells us **where to search for minerals**.”
- “**Map Minerals**. We'll **search NASA's EMIT archive and run spectral matching**.”

CTA strings:

- **“Map Minerals”** — implies detection/confirmation, not candidates.
- **“Try demo scorecard”** — not “Try Cuprite benchmark”; softens that Path A is validation, not product AOI.
- Default minerals: `hematite, goethite, jarosite, magnetite, limonite, ferrihydrite` **without `_demo` suffix** (`Home.tsx` L22; `SettingsPanel.tsx` L5–12) → looks like real library targets.
- Progress bar is **simulated 0–90%** (`Home.tsx` L92–96) — not job truth.
- Bbox path posts once; **no durable job poll** on the happy path for async EMIT (`README.md` “Does not work as UI suggests”; `DEMO_READINESS_PLAN.md` L58).
- ACE/veg: partially honest (toast + disabled UI) but **still rendered** as product features.

### Map result (MapView / stats)

Dangerous visual language:

| String / pattern | Path | Why dangerous |
|------------------|------|----------------|
| Huge **“Overall accuracy”** `XX.X%` | `MapView.tsx` L241–243 | OK only with named reference; fatal if reused without GT. |
| `P · R` per class | L255 | Fine for Path A; not “ore grade.” |
| Soft caveat under score | L260–261: “Candidate spectral match vs reference labels — **not ore proof**. Fixture demos use planted ground truth.” | Good — but small type under big %. |
| Score title **“Scorecard”** vs non-GT **“Mineral Map”** | L212 | Split is correct; non-GT still shows **Confidence** as %. |
| Stats: **“Confidence”** / **“Abundance”** as `NN%` | `StatisticsTab.tsx` L43–48 | Reads as probability / grade. |
| `name.replace("_demo", "")` | L30 | **Hides demo provenance** on purpose. |
| Progress / empty globe | Path B | Overlay needs session bbox; georef limits documented in README. |

`AdvancedOptions.tsx` still defaults classifier to **`continuum_removal`** and live ACE/veg toggles (L10–15, L52, L88–105) — second truth next to SettingsPanel SAM/SFF honesty.

scoreboard scoreboard already lists fixture **OA=1.000** as CI Path A — team self-deception if demos quote it as science.

---

## 2. Ops industry default (library / classical — not supervised)

From `INDUSTRY_MINERAL_BASELINE_2026.md` §1–2 (ops rank, not papers):

1. Reflectance + bad bands  
2. **SAM** (default whole-pixel class map)  
3. **MNF**  
4. Endmembers (PPI / VCA…) **or curated library**  
5. **MTMF** secondary  
6. **SFF / continuum** for diagnostic features  
7. Tetracorder-class feature systems (EMIT lineage)  
…  
11. Deep learning — **rare as unsupervised exploration default**

Commercial Cuprite story (EarthDaily 2024): MNF/PCA → **in-scene endmembers** → **SAM** → qualitative vs expert maps — **no OA leaderboard**, no trained HistGB.

**Product default must be:** curated library (or scene endmembers) + classical match (SAM/MTMF/SFF), unlabeled cube OK. Supervised OA is a **door** (“I have ROIs”), never home-path hero (`ADVERSARIAL_PRODUCT_REALIST.md` §1–3).

---

## 3. Minimum honest scorecard wording (≤3 metrics)

| # | Label (user-facing) | When | One-line definition |
|---|---------------------|------|---------------------|
| **1** | **Benchmark agreement** | Path A only (named site + reference) | “% of labeled pixels matching reference map under [method, library, protocol]. Not ore proof.” Prefer spatial-holdout honesty over full-scene circular endmembers. Show kappa as secondary, same card. |
| **2** | **Key-mineral recall** | Path A only | Mean recall (or F1) on 4–6 exploration classes (e.g. alunite, kaolinite, illite/muscovite, calcite, silica, Fe-oxide pack) — not rare-class noise. |
| **3** | **Paint coverage** | **All** paths (EMIT, upload, bbox) | “% of valid pixels above match threshold” + “% unknown/masked.” **Never call this accuracy.** |

**Never product metrics:** supervised model OA, fixture OA=1.0, literature 90%+ Cuprite OA, any OA on unlabeled AOI.

**Path B mandatory copy:** “No ground truth for this area — match strength only.”

---

## 4. Is CLI-only enough for “delivered” if UI is half-broken?

**Yes for Phase 0 / science gate. No for product “delivered.”**

| Bar | CLI-only OK? | Why |
|-----|--------------|-----|
| project plan Phase 0 “product is real” scoreboard | **Yes** | Explicit: evaluate CLI, no FastAPI required (`README.md` §0.2, §9–10). Gate is a **number + provenance**, not a globe. |
| DEMO_READINESS Path A DoD | **Partial** | “Open app **or** one CLI command” — CLI can satisfy validation story; UI is optional if CLI is the demo script. |
| DEMO Path B / north-star “any non-expert” | **No** | Non-experts will not run `evaluate` + open PNG folders. Half-broken UI that **looks** like Map Minerals → EMIT is **worse than no UI** (false product). |
| External “shipped product” claim | **No** | README already marks frontend “in development”; claiming delivered with dead toggles + fake progress is marketing fraud. |

**Rule:** CLI Path A with real library + metrics = **delivered science slice**. UI Path A scorecard = **demo theater**. UI Path B = **product** — only when progress, georef, and “no OA” honesty work. Do not freeze “demo-ready product” on a pretty shell that still ships confident garbage.

---

## 5. Smallest copy / UI fixes for honesty

Ordered by impact per line of code:

1. **Rename CTAs:** “Map Minerals” → **“Map candidates”** or **“Run spectral match”**; “Try demo scorecard” → **“Try Cuprite benchmark (vs reference)”**.  
2. **Default mineral chips:** show `*_demo` or label section **“Demo spectra only — not science”**; never strip `_demo` in `StatisticsTab`.  
3. **Confidence label:** “Match score (not probability)” / “Mean match strength”; Abundance → “Relative unmixing score (not grade).”  
4. **OA only if `scorecard` + reference provenance:** banner “Agreement with [reference name], not field assay.” Path B: hard-block OA UI.  
5. **Kill or remove** dead ACE/veg from Settings *and* AdvancedOptions; default classifier **SAM only** everywhere (delete CR option until dispatched + scored).  
6. **Walkthrough:** drop “search for minerals”; say “select AOI for EMIT reflectance → **candidate** match (needs library/token).”  
7. **Progress:** real job poll or indeterminate spinner — **delete fake %**.  
8. **Fixture path:** if OA≈1.0, force badge **“Planted synthetic GT — CI only”** larger than the number.  
9. **Home default path:** primary button = benchmark Path A; bbox Map is secondary “experimental.”  
10. **README screenshot caption:** list only wired controls (SAM/SFF if true; no ACE/veg theater).

---

## Verdict

first-time user today: **pretty globe + ore-ish verbs + Fe-oxide chips + fake progress + confidence %**, with a side door “demo scorecard” that can flash **100% fixture accuracy**. Ops world ships **library/classical candidate maps**, not accuracy theater. **CLI scoreboard delivers the science product; UI without honesty delivers liability.** Ship three metrics, one classical default, real spectra, and copy that refuses to sound like a detector.
