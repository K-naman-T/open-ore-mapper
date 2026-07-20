# FastAPI-Served Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a polished local web app to Open Ore Mapper so users can upload a raster, run QC, run prediction, inspect warnings/results, and understand product limitations through the browser.

**Architecture:** Serve static HTML, CSS, and JavaScript from the existing optional FastAPI app. Avoid a separate Node build toolchain for this slice; the Python package remains the source of truth and the web UI calls `/v1/qc/raster` and `/v1/predict`.

**Tech Stack:** FastAPI/Starlette static responses, vanilla HTML/CSS/JavaScript, existing Python pytest/FastAPI TestClient.

**Repository Constraint:** Do not commit unless the user explicitly authorizes commits.

---

## File Structure

- Create `src/open_ore_mapper/static/index.html` for the app shell.
- Create `src/open_ore_mapper/static/styles.css` for the visual system.
- Create `src/open_ore_mapper/static/app.js` for upload/QC/predict interactions.
- Modify `src/open_ore_mapper/api.py` to serve the static app and assets.
- Modify `tests/test_api.py` to cover web app routes.
- Modify `README.md` to document launching the web app.

---

### Task 1: Serve Static Web App

**Files:**
- Create: `src/open_ore_mapper/static/index.html`
- Create: `src/open_ore_mapper/static/styles.css`
- Create: `src/open_ore_mapper/static/app.js`
- Modify: `src/open_ore_mapper/api.py`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Write failing API route tests**

Add tests asserting:

- `GET /` returns `200`, `text/html`, and contains `Open Ore Mapper`.
- `GET /app.js` returns JavaScript content.
- `GET /styles.css` returns CSS content.

- [ ] **Step 2: Run API route tests and verify RED**

Run `pytest tests/test_api.py -v`. Expected: new route tests fail with 404.

- [ ] **Step 3: Add static app files**

Create a complete static UI with:

- Asymmetric hero layout.
- File upload input.
- Sensor and wavelength JSON inputs.
- Excluded band and minimum valid-fraction controls.
- QC button.
- Prediction button.
- Clear loading, error, empty, and result states.
- Result cards for QC status, retained/excluded bands, valid-pixel fraction, warnings, statistics, and returned PNG layers.
- Explicit limitation copy: spectral similarity is not confirmed ore discovery.

- [ ] **Step 4: Serve static files from FastAPI**

Add `GET /`, `GET /app.js`, and `GET /styles.css` routes using `FileResponse`. Resolve paths relative to `api.py` with `Path(__file__).with_name("static")`.

- [ ] **Step 5: Verify Task 1**

Run `pytest tests/test_api.py -v`. Expected: all API tests pass.

---

### Task 2: Document And Verify Product Web Flow

**Files:**
- Modify: `README.md`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Add smoke assertions for endpoint names in the app shell**

Extend the `GET /` test to assert the HTML references `/v1/qc/raster`, `/v1/predict`, and `spectral similarity` limitation copy.

- [ ] **Step 2: Update README**

Document launching the app with:

```bash
uvicorn open_ore_mapper.api:app --host 127.0.0.1 --port 8001
```

Document that the browser app runs locally at `http://127.0.0.1:8001/` and uses the same API endpoints as the CLI.

- [ ] **Step 3: Verify Task 2**

Run `pytest tests/test_api.py -v`. Expected: all API tests pass.

---

### Task 3: Full Verification

**Files:**
- Review all modified files.

- [ ] **Step 1: Run lint**

Run `. .venv/bin/activate && ruff check .`. Expected: `All checks passed!`.

- [ ] **Step 2: Run type check**

Run `. .venv/bin/activate && mypy src/open_ore_mapper`. Expected: `Success: no issues found`.

- [ ] **Step 3: Run test suite**

Run `. .venv/bin/activate && pytest -v`. Expected: all tests pass.

- [ ] **Step 4: Do not commit**

Leave changes uncommitted unless the user explicitly authorizes a commit.
