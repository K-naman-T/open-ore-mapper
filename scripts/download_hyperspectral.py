#!/usr/bin/env python3
"""
Multi-source hyperspectral scene downloader.

Usage:
    python scripts/download_hyperspectral.py --help
    python scripts/download_hyperspectral.py emit --bbox -117.0 37.5 -116.5 38.0 --output-dir data/emit
    python scripts/download_hyperspectral.py emit list --bbox -117.0 37.5 -116.5 38.0
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Any

USER_AGENT = "open-ore-mapper/0.1.0"


# ---------------------------------------------------------------------------
# EMIT (NASA Earthdata / LP DAAC)
# ---------------------------------------------------------------------------

EMIT_STAC_URL = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD/collections/EMITL2ARFL_001"


def _earthdata_session() -> dict[str, str]:
    token = os.environ.get("EARTHDATA_TOKEN")
    user = os.environ.get("EARTHDATA_USER")
    password = os.environ.get("EARTHDATA_PASSWORD")
    if token:
        return {"Authorization": f"Bearer {token}"}
    if user and password:
        import base64
        encoded = base64.b64encode(f"{user}:{password}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    return {}


def emit_search(bbox: list[float], max_results: int = 10, date_range: str | None = None) -> list[dict[str, Any]]:
    """Search EMIT scenes by bounding box via CMR STAC (LPCLOUD provider)."""
    if len(bbox) != 4:
        raise ValueError("bbox must be [west, south, east, north]")
    params: dict[str, str] = {
        "bbox": ",".join(str(v) for v in bbox),
        "limit": str(max_results),
    }
    if date_range:
        params["datetime"] = date_range
    url = EMIT_STAC_URL + "/items?" + "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  EMIT search error: {e.code} {e.reason}", file=sys.stderr)
        if e.code == 404:
            print(f"  URL tried: {url[:120]}", file=sys.stderr)
        return []
    features = data.get("features", [])
    results = []
    for f in features:
        props = f.get("properties", {})
        assets = f.get("assets", {})
        granule_id = props.get("title") or f.get("id", "unknown")

        download_url = None
        size_mb: float | None = None
        for asset_key, asset_val in assets.items():
            href = asset_val.get("href", "")
            if not href.endswith(".nc") or "s3:" in href:
                continue
            if any(excl in href for excl in ("MASK", "UNCERT", "browse", "thumbnail")):
                continue
            download_url = href
            sz = asset_val.get("file:size", 0)
            if sz:
                size_mb = round(sz / (1024 * 1024), 1)
            break
        if not download_url:
            for asset_key, asset_val in assets.items():
                href = asset_val.get("href", "")
                if href.endswith(".nc") and "s3:" not in href:
                    download_url = href
                    break

        results.append({
            "id": granule_id,
            "datetime": props.get("datetime", ""),
            "bbox": f.get("bbox"),
            "cloud_cover": props.get("eo:cloud_cover", -1),
            "download_url": download_url,
            "size_mb": size_mb,
        })
    return results


def emit_download(scene_id: str, download_url: str | None, output_dir: str | Path) -> Path:
    """Download a single EMIT scene. Requires NASA Earthdata credentials."""
    if not download_url:
        raise ValueError(f"No download URL available for scene {scene_id}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"{scene_id}.nc"
    if dest.exists():
        print(f"  Already exists: {dest}")
        return dest
    headers = {"User-Agent": USER_AGENT}
    session = _earthdata_session()
    headers.update(session)
    if not session:
        print("  WARNING: No EARTHDATA_TOKEN or EARTHDATA_USER/PASSWORD set.", file=sys.stderr)
        print("  Attempting anonymous (may fail for download).", file=sys.stderr)
    req = urllib.request.Request(download_url, headers=headers)
    print(f"  Downloading {scene_id} ...")
    try:
        with urllib.request.urlopen(req, timeout=300) as src:
            with open(dest, "wb") as f:
                chunk = src.read(8192)
                if not chunk:
                    raise ValueError("Empty response")
                f.write(chunk)
                count = 1
                total = len(chunk)
                while True:
                    chunk = src.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)
                    count += 1
                    if count % 128 == 0:
                        sys.stdout.write(f"\r    Downloaded {total / 1024 / 1024:.1f} MB ... ")
                        sys.stdout.flush()
                print(f"\r    Done: {total / 1024 / 1024:.1f} MB")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print(f"  ERROR: Authentication failed for {scene_id}. Set EARTHDATA_TOKEN or EARTHDATA_USER/PASSWORD.", file=sys.stderr)
        elif e.code == 403:
            print(f"  ERROR: Forbidden for {scene_id}. Check credentials.", file=sys.stderr)
        elif e.code == 404:
            print(f"  ERROR: URL not found for {scene_id}: {download_url}", file=sys.stderr)
        else:
            print(f"  ERROR: HTTP {e.code} for {scene_id}: {e.reason}", file=sys.stderr)
        raise
    return dest


# ---------------------------------------------------------------------------
# EnMAP (DLR EOWEB)
# ---------------------------------------------------------------------------

ENMAP_API_URL = "https://eoweb.dlr.de/egp/odata/EnMAP_Products"


def enmap_search(bbox: list[float], max_results: int = 10) -> list[dict[str, Any]]:
    """Search EnMAP products via DLR EOWEB OData. Requires DLR EOWEB account."""
    filter_str = (
        f"OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(({bbox[0]} {bbox[1]},{bbox[2]} {bbox[1]},{bbox[2]} {bbox[3]},{bbox[0]} {bbox[3]},{bbox[0]} {bbox[1]}))')"
        and f"AcquisitionType eq 'SCENE'"
    )
    url = f"{ENMAP_API_URL}?$filter={urllib.parse.quote(filter_str)}&$top={max_results}&$format=json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  EnMAP search error: {e.code} {e.reason}", file=sys.stderr)
        return []
    results = []
    for entry in data.get("value", []):
        results.append({
            "id": entry.get("Name", "unknown"),
            "datetime": entry.get("AcquisitionDate", ""),
            "bbox": [entry.get("MinLongitude"), entry.get("MinLatitude"), entry.get("MaxLongitude"), entry.get("MaxLatitude")],
            "download_url": entry.get("DownloadLink") or entry.get("Url"),
            "size_mb": None,
            "note": "Requires DLR EOWEB account (free registration). Set EOWEB_USER/EOWEB_PASSWORD.",
        })
    return results


def enmap_download(scene_id: str, download_url: str | None, output_dir: str | Path) -> Path:
    if not download_url:
        raise ValueError(f"No download URL for EnMAP scene {scene_id}")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / f"enmap_{scene_id}.zip"
    if dest.exists():
        return dest
    user = os.environ.get("EOWEB_USER")
    password = os.environ.get("EOWEB_PASSWORD")
    if not user or not password:
        raise ValueError("Set EOWEB_USER and EOWEB_PASSWORD environment variables for EnMAP downloads")
    import base64
    encoded = base64.b64encode(f"{user}:{password}".encode()).decode()
    headers = {"User-Agent": USER_AGENT, "Authorization": f"Basic {encoded}"}
    req = urllib.request.Request(download_url, headers=headers)
    print(f"  Downloading EnMAP {scene_id} ...")
    try:
        with urllib.request.urlopen(req, timeout=300) as src, open(dest, "wb") as f:
            while True:
                chunk = src.read(8192)
                if not chunk:
                    break
                f.write(chunk)
    except urllib.error.HTTPError as e:
        print(f"  ERROR: EnMAP download failed: HTTP {e.code} {e.reason}", file=sys.stderr)
        if e.code == 401:
            print("  Set EOWEB_USER and EOWEB_PASSWORD environment variables.", file=sys.stderr)
        raise
    return dest


# ---------------------------------------------------------------------------
# PRISMA (ASI)
# ---------------------------------------------------------------------------

PRISMA_API_URL = "https://prisma.asi.it/api/v2"


def prisma_search(bbox: list[float], max_results: int = 10) -> list[dict[str, Any]]:
    """Search PRISMA scenes. Requires ASI PRISMA portal account."""
    url = f"{PRISMA_API_URL}/search"
    body = json.dumps({
        "bbox": bbox,
        "maxResults": max_results,
        "productType": "PRISMA_L2B",
    }).encode()
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    token = os.environ.get("PRISMA_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  PRISMA search error: HTTP {e.code} {e.reason}", file=sys.stderr)
        if e.code == 401:
            print("  Set PRISMA_TOKEN environment variable.", file=sys.stderr)
        return []
    results = []
    for item in data.get("results", data.get("data", [])):
        results.append({
            "id": item.get("id", "unknown"),
            "datetime": item.get("acquisitionDate", ""),
            "bbox": item.get("bbox"),
            "cloud_cover": item.get("cloudCover", -1),
            "download_url": item.get("downloadUrl"),
            "size_mb": None,
            "note": "Requires ASI PRISMA portal registration + API token. Set PRISMA_TOKEN.",
        })
    return results


# ---------------------------------------------------------------------------
# DESIS (DLR EOWEB)
# ---------------------------------------------------------------------------

DESIS_API_URL = "https://eoweb.dlr.de/egp/odata/DESIS_Products"


def desis_search(bbox: list[float], max_results: int = 10) -> list[dict[str, Any]]:
    """Search DESIS products via DLR EOWEB OData. Requires DLR EOWEB account."""
    filter_str = (
        f"OData.CSC.Intersects(area=geography'SRID=4326;POLYGON(({bbox[0]} {bbox[1]},{bbox[2]} {bbox[1]},{bbox[2]} {bbox[3]},{bbox[0]} {bbox[3]},{bbox[0]} {bbox[1]}))')"
    )
    url = f"{DESIS_API_URL}?$filter={urllib.parse.quote(filter_str)}&$top={max_results}&$format=json"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  DESIS search error: {e.code} {e.reason}", file=sys.stderr)
        return []
    results = []
    for entry in data.get("value", []):
        results.append({
            "id": entry.get("Name", "unknown"),
            "datetime": entry.get("AcquisitionDate", ""),
            "bbox": [entry.get("MinLongitude"), entry.get("MinLatitude"), entry.get("MaxLongitude"), entry.get("MaxLatitude")],
            "cloud_cover": -1,
            "download_url": entry.get("DownloadLink") or entry.get("Url"),
            "size_mb": None,
            "note": "Requires DLR EOWEB account (free registration). Set EOWEB_USER/EOWEB_PASSWORD.",
        })
    return results


# ---------------------------------------------------------------------------
# Hyperion EO-1 (USGS M2M API)
# ---------------------------------------------------------------------------

HYPERION_API_URL = "https://m2m.cr.usgs.gov/api/api/json/v2"


def hyperion_search(bbox: list[float], max_results: int = 10) -> list[dict[str, Any]]:
    """Search EO-1 Hyperion scenes via USGS M2M API. Requires USGS API key."""
    url = f"{HYPERION_API_URL}/scene-search"
    payload = {
        "datasetName": "EO1_HYP_CMP",
        "maxResults": max_results,
        "sceneFilter": {
            "spatialFilter": {
                "filterType": "mbr",
                "lowerLeft": {"latitude": bbox[1], "longitude": bbox[0]},
                "upperRight": {"latitude": bbox[3], "longitude": bbox[2]},
            }
        },
    }
    api_key = os.environ.get("USGS_API_KEY")
    if api_key:
        payload["apiKey"] = api_key
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "User-Agent": USER_AGENT}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  Hyperion search error: HTTP {e.code} {e.reason}", file=sys.stderr)
        return []
    results = []
    for item in data.get("data", {}).get("results", []):
        results.append({
            "id": item.get("entityId", "unknown"),
            "datetime": item.get("acquisitionDate", ""),
            "bbox": [
                item.get("spatialBounds", {}).get("westLongitude"),
                item.get("spatialBounds", {}).get("southLatitude"),
                item.get("spatialBounds", {}).get("eastLongitude"),
                item.get("spatialBounds", {}).get("northLatitude"),
            ],
            "cloud_cover": item.get("cloudCover", -1),
            "download_url": item.get("downloadUrl"),
            "size_mb": None,
            "note": "Requires USGS EarthExplorer registration + API key. Set USGS_API_KEY.",
        })
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _add_source_parser(sub, name: str, help_text: str):
    p = sub.add_parser(name, help=help_text)
    sp = p.add_subparsers(dest="action", required=True)

    list_p = sp.add_parser("list", help=f"Search and list available {name.upper()} scenes")
    list_p.add_argument("--bbox", type=float, nargs=4, default=[-117.0, 37.5, -116.5, 38.0],
                        metavar=("W", "S", "E", "N"), help="Bounding box: west south east north")
    list_p.add_argument("--max-results", type=int, default=10)
    list_p.add_argument("--date-range", help="e.g. 2023-01-01/2023-06-30")

    dl_p = sp.add_parser("download", help=f"Download {name.upper()} scene(s)")
    dl_p.add_argument("scene_id", help="Scene ID from list output")
    dl_p.add_argument("--download-url", help="Download URL (override)")
    dl_p.add_argument("--output-dir", default=f"data/{name}", help="Output directory")
    dl_p.add_argument("--bbox", type=float, nargs=4,
                      metavar=("W", "S", "E", "N"), help="Bounding box for search")
    return p


def _format_results(results: list[dict[str, Any]]) -> str:
    lines = [json.dumps(r, indent=2) for r in results]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="download-hyperspectral",
        description="Download hyperspectral scenes from multiple public satellite missions.",
    )
    sub = parser.add_subparsers(dest="source", required=True)

    _add_source_parser(sub, "emit", "NASA EMIT imaging spectrometer")
    _add_source_parser(sub, "enmap", "EnMAP hyperspectral satellite (DLR EOWEB)")
    _add_source_parser(sub, "prisma", "PRISMA hyperspectral (ASI)")
    _add_source_parser(sub, "desis", "DESIS hyperspectral (DLR EOWEB)")
    _add_source_parser(sub, "hyperion", "EO-1 Hyperion historical archive (USGS)")

    args = parser.parse_args()

    sources = {
        "emit": (emit_search, emit_download),
        "enmap": (enmap_search, enmap_download),
        "prisma": (prisma_search, None),
        "desis": (desis_search, None),
        "hyperion": (hyperion_search, None),
    }

    search_fn, download_fn = sources[args.source]

    if args.action == "list":
        date_range = getattr(args, "date_range", None)
        kwargs: dict = {}
        if date_range:
            kwargs["date_range"] = date_range
        results = search_fn(args.bbox, args.max_results, **kwargs)
        print(_format_results(results))
        if not results:
            print(f"No {args.source.upper()} scenes found.")
            return 0
        return 0

    if args.action == "download":
        if download_fn is None:
            print(f"Download not implemented for {args.source}. See instructions above.", file=sys.stderr)
            return 1
        dl_url = (args.download_url or "")
        if not dl_url:
            results = search_fn(args.bbox, 1) if hasattr(args, "bbox") else []
            for r in results:
                if r["id"] == args.scene_id:
                    dl_url = r.get("download_url") or ""
                    break
        if not dl_url:
            print(f"No download URL for scene {args.scene_id}. Use --download-url or search first.", file=sys.stderr)
            return 1
        dest = download_fn(args.scene_id, dl_url, args.output_dir)
        print(f"Saved to {dest}")
        return 0

    return 0


if __name__ == "__main__":
    import urllib.parse
    sys.exit(main())
