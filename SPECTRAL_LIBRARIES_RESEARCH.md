# Mineral Spectral Libraries Research

## 1. USGS Spectral Library (splib07a)

**Download URL (current):** https://www.usgs.gov/centers/gmeg/science/spectral-library (redirects to ladsweb.modaps.eosdis.nasa.gov in some configurations)

Primary archive: The USGS spectral library files are served through the USGS ScienceBase and the NASA Land Processes DAAC. The original splib07a download page (speclab.cr.usgs.gov/spectral-lib.html) is deprecated.

**Direct download paths:**
- Historical: `ftp://ftpext.cr.usgs.gov/pub/cr/co/denver/speclab/` (may no longer be active)
- The ECOSTRESS Spectral Library at https://speclib.jpl.nasa.gov includes all USGS Reston spectra
- Current USGS spectral library work is at https://www.usgs.gov/spectral-lab-0

**Format:** ASD ASCII format (Analytical Spectral Devices). Wavelength units in nanometers. Reflectance values as comma-separated or space-delimited columns (wavelength, reflectance). Also available in ENVI spectral library (.sli) format for some versions.

**Statistics:**
- ~500+ minerals (splib07a: 498 mineral spectra files)
- ~1300+ total samples including rocks, soils, vegetation
- Wavelength range: 0.2-25.0 µm (VNIR through TIR)
- Spectral sampling varies: 0.002 µm in VNIR, 0.005-0.01 µm in SWIR, 0.01-0.1 µm in TIR

**License:** US Government work — public domain (no copyright restriction). **Apache-2.0 compatible for redistribution.** USGS requires attribution: "U.S. Geological Survey (USGS) Spectral Library Version 7a." No attribution required legally, but citation expected: *Kokaly, R.F., et al. (2017). USGS Spectral Library Version 7 Data. USGS Data Series 1035.*

**Redistribution:** Fully allowed. Since it's US government work, it's in the public domain. Can be bundled with Apache-2.0 projects. No per-sample license restrictions. No known additional permission requirements beyond standard USGS citation.

---

## 2. ECOSTRESS Spectral Library (formerly ASTER/JPL)

**Homepage:** https://speclib.jpl.nasa.gov

**Download:** https://speclib.jpl.nasa.gov/download (JS-based download — each category trigger sends an email or direct download)
- Minerals: 3104 files
- Rocks: 647 files
- Soils: 120 files
- Vegetation: 1966 files
- Non-photosynthetic vegetation: 162 files
- Man-made: 72 files
- Meteorites: 59 files
- Lunar: 17 files
- Water: 9 files
- **Total: 6139 files**

**Format:** Text-based format. Each file is an ASCII text file with columns (wavelength in µm, reflectance value). Not ASD format — custom JPL format. Two-column, space-separated.

**Wavelength range:** 0.3-45 µm (VSWIR through TIR). Includes JHU, JPL, and USGS (Reston) collections merged.

**License:** Copyright © 2017, California Institute of Technology. ALL RIGHTS RESERVED. "Reproduced from the ECOSTRESS Spectral Library through the courtesy of the Jet Propulsion Laboratory, California Institute of Technology."

This is **restrictive for redistribution**. The "all rights reserved" notice means you cannot freely redistribute these files in an Apache-2.0 project. However:
- You can download at runtime via wget/curl (no authentication required)
- Individual spectra can be cited/fetched one at a time from the library search
- Bulk download requires JS interaction on the website
- **Recommendation:** Fetch at runtime, do not bundle. The "all rights reserved" status is incompatible with Apache-2.0 redistribution of the library files directly.

**Citation:** Meerdink, S.K., Hook, S.J., Roberts, D.A., & Abbott, E.A. (2019). Remote Sensing of Environment, 230(111196), 1–8.

**PDS/ScienceBase:** There is also a product ID "ECOSPECLIB.001" at LP DAAC: https://lpdaac.usgs.gov/products/ecospeclibv001/ — hosted as an HDF5 format.

---

## 3. ASU Thermal Emission Spectral Library

**Homepage:** https://speclib.asu.edu (requires account registration, guest login available)

**Focus:** Thermal infrared (TIR) emissivity spectra of minerals, rocks, soils, and man-made materials. Emissivity range ~5-200 µm.

**Format:** Web-based access with spectral albums. Guest login works. Download via web interface.

**Reflectance vs emissivity:** The ASU library primarily contains **emissivity** spectra, not reflectance. Kirchhoff's Law states ε = 1 - R at thermal equilibrium for opaque materials. However, this conversion is only strictly valid for directional-hemispherical reflectance at the same temperature. For a mineral mapping tool using VSWIR reflectance, you cannot reliably convert ASU TIR emissivity to VSWIR reflectance.

**License:** Not explicitly stated. Registration required. Typically NASA/ASU with "all rights reserved" similar to JPL.

**Redistribution:** At-runtime fetch only. Do not bundle.

---

## 4. RELAB (Brown University) — Reflectance Experiment LABoratory

**Homepage:** https://sites.brown.edu/relab/ (Brown site)
**PDS hosted archive:** https://pds-geosciences.wustl.edu/spectrallibrary/default.htm

**PDS Bundle:** https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/
- **12,503 specimens** reported by the archive
- **23,606 reflectance products** in the PDS4 collection inventory as of May 27, 2025
- Full reflectance directory: https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/

**Format:** PDS4 format (XML-labeled data products with tabular spectral data). Each measurement has an XML label file and a data file. The data files are ASCII tables.

**Wavelength range:** UV to far-IR (typically 0.3-25 µm). Bidirectional reflectance at multiple phase angles.

**License:** Publicly downloadable from NASA PDS. RELAB is hosted at Brown University; while NASA-funded, the data resides at a private institution. Redistribution terms are not definitively verified as "public domain" for all contents. **Use as fetch-at-runtime input pending license verification.**

**Redistribution:** Use as fetch-at-runtime input. Do not bundle without verifying per-file redistribution terms. Attribution to RELAB/Brown and NASA expected.

**API access:** PDS Geosciences Node provides a spectral library search interface at https://pds-speclib.rsl.wustl.edu/ with search/filter/download capabilities. Bulk download via direct FTP/HTTPS from the PDS bundles.

---

## 5. PDS Geosciences Node Spectral Libraries

**Homepage:** https://pds-geosciences.wustl.edu/spectrallibrary/default.htm
**Search Interface:** https://pds-speclib.rsl.wustl.edu/

Besides RELAB, the PDS Geosciences Node hosts:

1. **Frankenspectra Database** — 27 fine-particulate terrestrial minerals, far-UV through MIR
   - Bundle: https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-frankenspectra_database/

2. **XAS Synthesized Glasses** — 25 specimens, XANES spectra
   - Bundle: https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-xas_synthesized_glasses/

3. **LIBS Reference Database** — 2,920 specimens, 304,959 spectra
   - Bundle: https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-libs_reference_database/

**License:** Public availability in a NASA PDS archive does not by itself establish public-domain or redistribution status for contributor-owned measurements. Verify each bundle's terms before redistribution.

---

## 6. GEISA (Gestion et Etude des Informations Spectroscopiques Atmosphériques)

**Homepage:** https://geisa.aeris-data.fr/
**Former:** https://eodg.atm.ox.ac.uk/GEISA/ (deprecated)

**Content:** Atmospheric molecular absorption line parameters (HITRAN-like database). H2O, CO2, O3, CH4, etc. line lists, cross-sections, and absorption coefficients. **NOT mineral spectra.**

**Relevance:** Essential for atmospheric correction of VSWIR/TIR data. Provides the gas absorption data needed to remove atmospheric effects from satellite imagery before mineral mapping.

**Format:** Standardized ascii line-by-line format. Also available as HITRAN format.

**License:** Public domain (French government/LMD/CNRS). **Apache-2.0 compatible.**

**Programmatic access:** Available via AERIS data portal. Can be fetched via wget/curl.

**Python integration:** `pyh2o`, `hitran`, `refrac` packages on PyPI work with GEISA/HITRAN data.

---

## 7. Other Spectral Libraries

### CSIRO (Australia) — HyLogging Spectral Library
- **Status:** CSIRO's HyLogger system produces a spectral library of over 200,000 drill core scans from mineral exploration. The collection is massive but **not publicly downloadable in bulk**. Data is accessible by collaboration or through AuScope/AusGeochem portals.
- **URL:** https://www.csiro.au/en/research/natural-environment/remotesensing/CSIRO-spectral-library (currently 404; the spectral library program is now under the AuScope initiative)
- **Format:** TSG (The Spectral Geologist) format, ASCII export possible
- **License:** Proprietary/restricted. Not redistributable without CSIRO agreement.

### GFZ (German Research Centre for Geosciences) — Potsdam
- **Status:** GFZ hosts specialized spectral libraries for specific research projects, including the EnMAP spectral library. GFZ developed the `enpt` (EnMAP-Box) which has spectral library tools.
- **URL:** Search: GFZ spectral library or `enmap-box`
- **License:** Research-use with varying individual project agreements.

### GA (Geoscience Australia) — HyLogger Spectral Library
- **URLs:** Formerly at https://www.ga.gov.au/spectral-data (404). The HyLogger data feeds into AuScope's AusGeochem.
- **License:** Varies by sample. Increasingly open under Creative Commons Attribution.

### Open Soil Spectral Library (OSSL)
- **Homepage:** https://soilspectroscopy.org/
- **Data:** >70,000 soil MIR spectra + >20,000 VIS-NIR spectra
- **Format:** MongoDB-backed, accessible via API at https://engine.soilspectroscopy.org/
- **GitHub:** https://github.com/soilspectroscopy/
- **License:** Creative Commons Attribution (CC-BY). **Apache-2.0 compatible** with attribution.
- **API:** REST API at https://api.soilspectroscopy.org/ (MIR + VIS-NIR + predicted properties)
- **Relevance:** Soils are mineral mixtures. Clay mineralogy (kaolinite, smectite, illite) detectable in VIS-NIR. Good for background soil mineral mapping.

### SPECCHIO Spectral Library System
- **Homepage:** http://specchio.ch/
- **Description:** A spectral information management system used by many institutions. Contains field and lab spectra.
- **License:** Open source (GPL) but the data within is provider-dependent.

### EnMAP Spectral Library (GFZ/HU Berlin)
- **URL:** https://www.enmap.org/
- **Description:** The Environmental Mapping and Analysis Program (EnMAP) produced a spectral library for their German hyperspectral satellite mission. ~400+ spectra of minerals, soils, vegetation.
- **License:** Research access, generally open.
- **Format:** ENVI spectral library format.

---

## 8. Programmatic Access & Python Packages

### Python `spectral` (SPy)
- **PyPI:** https://pypi.org/project/spectral/
- **Version:** 0.24 (April 2025)
- **License:** MIT
- **Capabilities:**
  - Read/write ENVI spectral library (.sli) and hyperspectral image formats
  - Classification (SAM, SID, MD, MLC, SVM)
  - Spectral resampling
  - Visualization
  - **Does NOT bundle any spectral library data** — only provides the tools
- **Install:** `pip install spectral`

### Other Python Tools

| Package | Purpose | License | Notes |
|---------|---------|---------|-------|
| `pysptools` | Hyperspectral classification + spectral unmixing | GPLv3 | SAM, SID, LSU, NCLS |
| `spectralresampling` | Resample spectra to sensor bands | MIT | By CSIRO |
| `rios` | Raster I/O + spectral resampling | GPL |
| `pyh2o` / `hitran` | Atmospheric absorption | Various | HITRAN/GEISA data |
| `hsdar` (R) | Hyperspectral data processing | GPL | R package |
| `prospect` (R) | Leaf optical properties | GPL-2 | |
| `gemgis` | Spectral processing for mineral mapping | Apache-2.0 | |

### Bulk Download via wget/curl

```bash
# ECOSTRESS Spectral Library - ALL (will trigger email download via JS)
# The JS-based download at speclib.jpl.nasa.gov/download cannot be directly
# wget'd. You need to interact with the form.

# RELAB via PDS (direct wget works):
wget -r -np -nH --cut-dirs=2 \
  https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/

# USGS splib07a original format (if mirrors are up):
# The original FTP was at:
# ftp://ftpext.cr.usgs.gov/pub/cr/co/denver/speclib/splib07a
# Verify with: wget --spider ftp://ftpext.cr.usgs.gov/pub/cr/co/denver/speclib/splib07a

# OSSL (Soil):
curl -L -o ossl_data.zip https://files.soilspectroscopy.org/
```

---

## 9. License Analysis Summary for Apache-2.0 Redistribution

| Library | Redistribute? | Attribution? | Fetch-at-Runtime? | Bundling Strategy |
|---------|--------------|--------------|-------------------|-------------------|
| USGS splib07a | **YES** | Requested | N/A | Can bundle directly |
| ECOSTRESS (JPL) | **NO** | Required | YES | Script at `npm install` / first run to download |
| ASU TIR | **NO** | Required | YES (guest login) | Fetch per-session or cache locally |
| RELAB (PDS) | **UNCLEAR** | Requested | YES | Fetch at runtime pending verification |
| Frankenspectra | **UNCLEAR** | Requested | YES | Verify bundle terms before bundling |
| OSSL (Soil) | **YES** (CC-BY) | Required | YES | Bundle or fetch |
| CSIRO | **NO** | - | Limited | Must negotiate |
| GFZ/EnMAP | **UC** (unknown) | - | Limited | Fetch at runtime |
| GEISA | **VERIFY** | Requested | YES | Review current data terms before redistribution |

**Recommended strategy:**
1. **Bundle** USGS splib07a directly (public domain, no legal restrictions). RELAB spectra — fetch at runtime pending redistribution verification.
2. **First-run download script** to fetch ECOSTRESS spectra from JPL (respects the "all rights reserved" notice while providing convenience).
3. **Runtime API calls** for OSSL soil data.
4. **Atmospheric correction** modules can use GEISA/HITRAN data unbundled with download instructions.

---

## 10. Spectral Resampling: Lab-to-Sensor

### Correct Method: Convolution with Spectral Response Function (SRF)

**Do NOT use simple interpolation (spline/cubic)** for resampling lab spectra to sensor bands. The correct approach:

```
ρ_band = ∫ ρ(λ) · R(λ) dλ / ∫ R(λ) dλ
```

Where:
- ρ(λ) = lab spectrum at high resolution (1 nm)
- R(λ) = sensor band's spectral response function (normalized)
- Integration bounds = band FWHM or defined cutoffs

**Implementation in Python:**

```python
import numpy as np
from scipy.interpolate import interp1d

def resample_to_sensor(lab_wl, lab_refl, sensor_srf_wl, sensor_srf_response):
    """
    Resample lab spectrum to sensor band using SRF convolution.

    Args:
        lab_wl: 1D array of lab wavelengths (nm)
        lab_refl: 1D array of lab reflectance values
        sensor_srf_wl: list/array of SRF wavelength arrays per band
        sensor_srf_response: list/array of SRF response arrays per band

    Returns:
        band_reflectances: array of resampled reflectance per band
    """
    # Interpolate lab spectrum to fine grid
    f = interp1d(lab_wl, lab_refl, kind='linear',
                 bounds_error=False, fill_value=np.nan)

    n_bands = len(sensor_srf_wl)
    band_reflectances = np.zeros(n_bands)

    for i in range(n_bands):
        wl = sensor_srf_wl[i]
        srf = sensor_srf_response[i]
        refl = f(wl)
        valid = ~np.isnan(refl)
        band_reflectances[i] = np.trapz(refl[valid] * srf[valid], wl[valid])

    return band_reflectances
```

**Python libraries that handle this:**
- `spectral` (SPy) — `spectral.io.envi.SpectralLibrary` with resampling
- `spectralresampling` (pip install) — dedicated resampling library by CSIRO
- Custom implementation with `scipy.interpolate` + `numpy.trapz` as above

**Where to get sensor SRFs:**
- **Landsat 8/9 OLI:** https://www.usgs.gov/landsat-missions/landsat-8-oli-spectral-response-data
- **Sentinel-2 MSI:** https://sentinels.copernicus.eu/web/sentinel/user-guides/sentinel-2-msi/document-library
- **ASTER:** https://asterweb.jpl.nasa.gov/documentation.asp
- **EnMAP:** https://www.enmap.org/data
- **PRISMA:** https://www.asi.it/en/earth-science/prisma/
- **EMIT:** https://earth.jpl.nasa.gov/emit/data/data-products/
- **AVIRIS-NG:** https://aviris-ng.jpl.nasa.gov/

### Why Simple Interpolation Fails

Simple interpolation assumes the sensor has a delta-function response at each band center, which is false. Real sensor bandpasses are Gaussian-like or top-hat shaped. The SRF convolution matters most:
- At absorption feature edges (where mineral features are narrow)
- For narrow bands in hyperspectral sensors
- When the feature FWHM is comparable to band FWHM
- For Sentinel-2's broad bands (10-40nm FWHM) vs 1nm lab data

---

## Quick Reference URL Summary

```
# Downloadable without login/API
USGS splib07a:       ftp://ftpext.cr.usgs.gov/pub/cr/co/denver/speclib/splib07a/ (verify)
ECOSTRESS/JPL:       https://speclib.jpl.nasa.gov/download (JS-based)
RELAB (PDS):         https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-relab/data_reflectance/
Frankenspectra:      https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-frankenspectra_database/
LIBS Database:       https://pds-geosciences.wustl.edu/speclib/urn-nasa-pds-libs_reference_database/
OSSL (Soil):         https://explorer.soilspectroscopy.org/ (API: https://api.soilspectroscopy.org/)
GEISA:               https://geisa.aeris-data.fr/

# Requires login/signup
ASU TIR Library:     https://speclib.asu.edu (guest: guest)
CSIRO HyLogger:      https://ausgeochem.com.au/ (free registration)

# Python packages
spectral (SPy):      pip install spectral (MIT license)
spectralresampling:  pip install spectralresampling (MIT)
pysptools:           pip install pysptools (GPLv3)
```
