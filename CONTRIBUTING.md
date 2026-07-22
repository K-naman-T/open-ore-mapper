# Contributing

Thanks for helping improve Open Ore Mapper.

## Setup

```bash
python -m pip install -e '.[dev,api]'
```

## Running Tests & Checks

```bash
make test        # pytest -v
make lint        # ruff check .
make typecheck   # mypy src/open_ore_mapper
make check-all   # lint + typecheck + test-all
```

Or directly:

```bash
python3 -m pytest -v               # core tests (excludes emit/e2e)
make test-all                      # core + emit + e2e
ruff check .                       # zero-tolerance lint (line-length 100, py310)
mypy src/open_ore_mapper           # strict mode, must pass clean
```

All checks must pass before a pull request is merged (`make check-all`).

## Ground Rules

### Scientific-Data Provenance

Read `PROVENANCE.md` before contributing any data. This project enforces a strict provenance policy:

- **Do not commit** satellite imagery, hyperspectral cubes (HSI), spectral library files, model weights, training outputs, or any real geoscientific dataset to this repository unless its redistribution license has been **verified and documented**.
- **Allowed without review:** synthetic demo spectra (generated from analytic curves), algorithm code, tests, documentation.
- **Allowed with documented license:** public-domain spectral libraries (USGS splib07a, Frankenspectra), CC-BY data (OSSL, AusGeochem), CC0 data (NEON AOP). RELAB spectra are publicly downloadable via NASA PDS but redistribution terms require case-by-case verification. Include the exact source URL, license URL, and files/rows included in the PR description.
- **Never allowed:** proprietary exploration data, private survey cubes, credentials, institutional branding, commercial spectral libraries without written redistribution permission.
- If redistribution rights are unclear, document the source as a **user-provided input recipe** (fetch-at-runtime script or download instructions) instead of bundling.

### Algorithm & Test Expectations

- All algorithms must include corresponding tests in `tests/`.
- Tests must cover normal paths, edge cases (empty input, single-pixel rasters, missing bands), and error handling.
- No new module is considered complete without a matching `test_<module>.py` file.
- Prefer NumPy/SciPy vectorisation over Python loops in hot paths.
- Keep public API backward-compatible within a minor version.

### Credential Handling

- **Never commit** API keys, Earthdata login credentials, database passwords, or any secrets.
- Use environment variables or a `.env` file (add to `.gitignore`).
- Where the code needs credentials (e.g. NASA Earthdata login for EMIT/RELAB downloads), accept them as runtime parameters, environment variables, or a config file that is **not tracked by git**.
- If you accidentally commit a secret, rotate it immediately and open a private vulnerability report (see `SECURITY.md`).

### Research-Output Disclaimer

Open Ore Mapper produces **research-grade** mineral classification results. Outputs are:
- Dependent on input data quality, wavelength coverage, atmospheric correction, and spectral library suitability.
- **Not a substitute** for professional geoscientific interpretation, ground-truth validation, or exploration decision-making.
- Provided without warranty (see Apache-2.0 §7).

Do not represent results as definitive mineral discovery or reserve estimates.

## Pull Request Process

1. Ensure `make check-all` passes (lint, typecheck, and all test variants).
2. If adding a real spectral data source, include provenance documentation per the rules above.
3. Update or add tests for any changed logic.
4. Keep PRs focused on a single concern. Split large changes.

## Reporting Vulnerabilities

See `SECURITY.md`. Use **GitHub private vulnerability reporting** (do not file a public issue).
