# Product re-ground research index (2026-07-26)

**Game:** product-first first-time user (unlabeled classical), not supervised OA trophies.  
**Agent policy:** ≤2 concurrent research agents; one full-cube run; no multi-seed ML.

## Research package

| Doc | Role |
|-----|------|
| [`PRODUCT_PATH_RESEARCH_2026.md`](PRODUCT_PATH_RESEARCH_2026.md) | Code path + eval honesty |
| [`PRODUCT_UX_OPS_RESEARCH_2026.md`](PRODUCT_UX_OPS_RESEARCH_2026.md) | UX + industry ops |
| [`SUPERVISOR_GO_NOGO.md`](SUPERVISOR_GO_NOGO.md) | **GO** for deliverable |
| [`ADVERSARIAL_CONSENSUS.md`](ADVERSARIAL_CONSENSUS.md) | Prior binding claims |

## Dimensions checked (anti-sycophancy)

| Dimension | Outcome |
|-----------|---------|
| Ops industry | Library classical default; not HistGB |
| Eval honesty | Track B full-scene diagnostic 0.71; multi-seed 0.66; Track C not product |
| Product UX | Bare “accuracy %” relabeled agreement |
| Current code | `run_cuprite_real_validation.py` default `fuse_classical` |

## Delivered   command

```bash
.venv/bin/python scripts/run_cuprite_real_validation.py
# → outputs/cuprite-real-eval/comparison_panel.png + metrics.json
# classifier=fuse_classical, OA ~0.72 map-to-map (not field truth)
```
