# Supervisor GO/NO-GO — first-time user deliverable

**Date:** 2026-07-26  
**Inputs:** `PRODUCT_PATH_RESEARCH_2026.md`, `PRODUCT_UX_OPS_RESEARCH_2026.md`, `ADVERSARIAL_CONSENSUS.md`, `BEST_NUMBERS.md`  
**Agents:** 2 concurrent research only (code+eval, UX+ops); no heavy multi-seed/ML.  
**RAM policy:** sequential full-cube run once; no parallel Cuprite multi-seed.

---

## Verdict: **GO** (with minimal honesty blockers fixed in this goal)

The plan **will** produce good first-time user output **if** we define that output as:

> From repo: run **one classical unsupervised** Cuprite validation → open **GT | Ours | Diff panel** + metrics with **map-to-map agreement** wording — not HistGB, not “82% truth.”

### Why GO

| Check | Status |
|-------|--------|
| Real unlabeled classical engine | **Yes** — `fuse_classical` default in `scripts/run_cuprite_real_validation.py` |
| Real Cuprite package | **Yes** — `benchmarks/cuprite_real/` |
| Maps + metrics path | **Yes** — `outputs/cuprite-real-eval/` panel + metrics.json |
| Consensus product rule | Unsupervised classical default — **aligned** |
| Track C trophies as product | **Forbidden** — docs already mostly Track B/C; UI/README need small honesty pass |

### Not required for GO (deferred)

| Item | Why deferred |
|------|----------------|
| Independent USGS library Track A multi-seed | Consensus next science track; not the   sitting |
| Full UI/EMIT Path B polish | Half-broken UI is separate; **CLI/script path is deliverable** |
| HybridSN / HistGB product mode | Explicit non-goal |
| Schema default `sam` → fuse globally | Nice-to-have; Cuprite script already overrides |

### Smallest fixes before/with deliver (this goal)

1. **Honest scorecard copy** in MapView (agreement, not bare “accuracy as truth”).  
2. **README**   Cuprite command + framing.  
3. **Validation report/metrics provenance** screams map-to-map / semi-dependent endmembers.  
4. **One real run** of `run_cuprite_real_validation.py` + tests + scratch log.

### Product accuracy claims the supervisor forbids

- HistGB / RF multi-seed OA as product accuracy or mineral truth  
- “0.82 accuracy” or retired gate language  
- Full-scene 0.71 as field-validated accuracy without protocol clause  

### Allowed external classical bar

- Prefer **fuse multi-seed 0.664 ± 0.092** (Track B spatial)  
- Full-scene fuse **0.713** only as diagnostic (all pure-GT endmembers)

---

## Dimensions checked (research package)

| Dimension | Source | Fooled by trophy OA? |
|-----------|--------|----------------------|
| Ops industry | INDUSTRY baseline + UX research | No — library classical default |
| Eval honesty | ADVERSARIAL_CONSENSUS + PRODUCT_PATH | No — Track A/B/C split |
| Product UX | PRODUCT_UX_OPS | No — flags bare OA % |
| Current code path | PRODUCT_PATH + script read | No — fuse is script default |

---

##   command (authoritative)

```bash
cd /path/to/open-ore-mapper
.venv/bin/python scripts/run_cuprite_real_validation.py
# default classifier = fuse_classical (unsupervised classical)
# open: outputs/cuprite-real-eval/comparison_panel.png
# metrics: outputs/cuprite-real-eval/metrics.json  (agreement vs Tetracorder, not field truth)
```

**Supervisor signature:** GO — proceed to deliver classical path + honesty fixes only.
