# Synthesis from research scrapes

**Source:** `docs/research_scrapes/index.json` + sibling HTML files.  
**Generated:** 2026-07-26. Key claims only; no paper numbers invented from bot-blocked pages.

---

## Scrape inventory

| URL | Status | Bytes | Usable content? |
|-----|--------|------:|-----------------|
| https://www.nv5geospatialsoftware.com/docs/spectralhourglasswizard.html | 200 | 37164 | **Partial** — page chrome / docs shell loaded; core hourglass body did not extract as article text (search UI “No results found” in text dump) |
| https://www.mdpi.com/2072-4292/11/18/2181 | 200 | 2234 | **No** — Akamai interstitial / bot challenge |
| https://www.mdpi.com/2072-4292/12/7/1137 | 200 | 2231 | **No** — same |
| https://www.mdpi.com/2072-4292/13/4/622 | 200 | 2225 | **No** — same |
| https://www.mdpi.com/2072-4292/14/9/2244 | 200 | 2231 | **No** — same |
| https://en.wikipedia.org/wiki/Spectral_angle_mapper | 403 | 141 | **No** — Wikimedia robot policy |
| https://en.wikipedia.org/wiki/Matched_filter | 403 | 141 | **No** — same |
| https://www.l3harrisgeospatial.com/docs/spectralhourglasswizard.html | DNS fail | — | **No** — host not resolved (legacy ENVI docs host) |
| https://www.usgs.gov/publications/imaging-spectroscopy-earth-and-planetary-remote-sensing-applications | 202 | 0 | **No** — empty body |
| https://www.usgs.gov/centers/geology-geophysics-and-geochemistry-science-center/science/imaging-spectroscopy | 202 | 0 | **No** — empty body |

**Bottom line:** automated scrapes did **not** yield peer-reviewed abstracts or quantitative OA tables. Pipeline recommendations rest on (1) this project’s Cuprite metrics, (2) in-repo algorithm code, (3) classic literature already summarized in `RESEARCH_SYNTHESIS.md`, not on MDPI/Wiki page bodies.

---

## Claims that *can* be drawn from successful scrape material

### NV5 / ENVI Spectral Hourglass wizard docs
URL: https://www.nv5geospatialsoftware.com/docs/spectralhourglasswizard.html  
File: `www.nv5geospatialsoftware.com_docs_spectralhourglasswizard.html.html`

- Confirms ENVI still documents a **Spectral Hourglass** workflow as first-class product documentation (nav: ENVI modules including Atmospheric Correction, Deep Learning, Machine Learning, Feature Extraction).
- The scrape is a live Docs Center shell (title search, IDL/ENVI TOC). It is evidence that commercial stacks treat **hourglass-style reduction + endmember ID + mapping** as the standard path — not raw full-band SAM alone.
- **Cannot extract from this scrape alone:** step order, MNF component defaults, PPI parameters, or published Cuprite accuracy numbers. Those must come from classic papers / full ENVI help when re-fetched with a browser.

### MDPI Remote Sensing papers (intended topics by URL only)
The four Remote Sensing journal URLs were requested (likely mineral mapping / hyperspectral method papers). **Bodies are challenge pages only.** Do not cite claims, tables, or OA figures from these files.

Intended URLs for a human re-open / PDF download:

1. https://www.mdpi.com/2072-4292/11/18/2181  
2. https://www.mdpi.com/2072-4292/12/7/1137  
3. https://www.mdpi.com/2072-4292/13/4/622  
4. https://www.mdpi.com/2072-4292/14/9/2244  

### Wikipedia SAM / matched filter
Blocked (403 + robot policy text). No definitions extracted.

### USGS imaging spectroscopy pages
Empty 202 responses. No Clark/Tetracorder or library text extracted from scrapes. Prefer local synthesis docs and known USGS citations instead.

---

## Cross-check with project research docs (not scrapes)

These claims are **in-repo**, not from the scrape bodies:

- **Pro workflow steps** (curate library → atmos → MNF → endmembers → classify → unmix): `RESEARCH_SYNTHESIS.md` Lane 8.
- **Published accuracy bands** (full-library SAM garbage ~20–40%; curated+MNF ~75–85%; MTMF Cuprite literature high; Tetracorder expert ~95%): same file Lane 4 — treat as literature summary, not this project’s measured OA.
- **Libraries / licenses** (USGS splib07a redistributable; ECOSTRESS runtime-only): `SPECTRAL_LIBRARIES_RESEARCH.md`.

---

## Scrape quality recommendations

1. Re-fetch MDPI with a real browser session or open-access PDF links; store **plain text abstracts**, not interstitial HTML.  
2. Use Internet Archive or NV5 docs PDF export for Spectral Hourglass step list.  
3. Prefer DOI-linked PDFs for Boardman MTMF, Green MNF, Kruse SAM/Cuprite, Clark Tetracorder rather than wiki crawls.  
4. Keep `index.json` status/bytes as the honesty layer for what was actually retrieved.


## Scrapling bulk pass (2026-07-26)

- CLI: `scrapling extract get URL OUTPUT_FILE` (positional output; not `-o`).
- System package `scrapling` 0.4.11 at `~/.local`; project venv needs `pip install scrapling` for Fetcher API.
- Markdown output requires `markdownify` (missing → use `.html` extension).
- Successful fetches: MDPI landing HTML, NV5 hourglass HTML (~37KB).
- Blocked/empty: Wikipedia 403, USGS challenge pages, some ar5iv timeouts.
