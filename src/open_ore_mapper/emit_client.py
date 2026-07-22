from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Iterator

import numpy as np
from numpy.typing import NDArray

COLLECTION_ID = "EMITL2ARFL"


class EmitError(Exception):
    pass


class EmitAuthError(EmitError):
    pass


class EmitHTTPError(EmitError):
    pass


class EmitTimeoutError(EmitError):
    pass


class EmitMalformedFileError(EmitError):
    pass


class EmitNetworkError(EmitError):
    pass


def _extract_bbox(g: Any) -> list[float]:
    try:
        rects = (
            g.umm.get("SpatialExtent", {})
            .get("HorizontalSpatialDomain", {})
            .get("Geometry", {})
            .get("BoundingRectangles", [])
        )
        if rects:
            r = rects[0]
            return [
                float(r.get("WestBoundingCoordinate", 0)),
                float(r.get("SouthBoundingCoordinate", 0)),
                float(r.get("EastBoundingCoordinate", 0)),
                float(r.get("NorthBoundingCoordinate", 0)),
            ]
    except Exception:
        pass
    return [0, 0, 0, 0]


def _extract_datetime(g: Any) -> str:
    try:
        return str(
            g.umm.get("TemporalExtent", {})
            .get("RangeDateTime", {})
            .get("BeginningDateTime", "")
        )
    except Exception:
        return ""


def _extract_cloud_cover(g: Any) -> float | None:
    try:
        dq = g.umm.get("DataQuality", {})
        cc = dq.get("CloudCover", None)
        if cc is not None:
            return float(cc)
    except Exception:
        pass
    return None


def search_emit_granules(
    bbox: tuple[float, float, float, float],
    cloud_max: float = 10.0,
    max_results: int = 5,
    date_range: tuple[str, str] | None = None,
) -> list[dict[str, Any]]:
    import earthaccess

    temporal = None
    if date_range is not None:
        temporal = (date_range[0], date_range[1])

    results = earthaccess.search_data(
        short_name=COLLECTION_ID,
        bounding_box=bbox,
        count=max_results,
        temporal=temporal,
    )

    granules: list[dict[str, Any]] = []
    for g in results:
        try:
            hrefs = [
                str(link)
                for link in g.data_links()
                if ".nc" in str(link)
                and "MASK" not in str(link)
                and "RFLUNCERT" not in str(link)
            ]
            href = hrefs[0] if hrefs else ""
        except Exception:
            href = ""

        raw_id = str(g) if not hasattr(g, "umm") else g.umm.get("GranuleUR", str(g))
        bbox_extracted = _extract_bbox(g)
        dt = _extract_datetime(g)
        cloud = _extract_cloud_cover(g)

        granules.append({
            "id": raw_id,
            "bbox": bbox_extracted,
            "datetime": dt,
            "cloud_cover": cloud,
            "asset_href": href,
        })

    return granules


def extract_bbox(granule: dict[str, Any]) -> tuple[float, float, float, float]:
    bbox = granule["bbox"]
    return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))


def select_best_granule(
    granules: list[dict[str, Any]], cloud_max: float = 10.0
) -> dict[str, Any] | None:
    valid = [g for g in granules if g.get("asset_href")]

    def sort_key(g: dict[str, Any]) -> tuple[int, float]:
        cc = g.get("cloud_cover")
        if cc is None:
            return (1, 0.0)
        if cc <= cloud_max:
            return (0, cc)
        return (2, cc)

    valid.sort(key=sort_key)

    best = valid[0] if valid else None
    if best is not None:
        cc = best.get("cloud_cover")
        if cc is not None and cc > cloud_max:
            return None
    return best


def _download_granule_to_file(href: str, dst: Path) -> None:
    import earthaccess

    try:
        auth = earthaccess.login(strategy="environment", persist=False)
    except Exception as exc:
        raise EmitAuthError(f"Earthdata auth failed: {exc}") from exc

    session = auth.get_session()
    try:
        resp = session.get(href, timeout=300, stream=True)
    except Exception as exc:
        raise EmitTimeoutError(f"HTTP request timed out or failed: {exc}") from exc

    if resp.status_code in (401, 403):
        raise EmitAuthError(f"Earthdata auth rejected (HTTP {resp.status_code})")
    try:
        resp.raise_for_status()
    except Exception as exc:
        raise EmitHTTPError(f"HTTP {resp.status_code}: {exc}") from exc

    try:
        with open(dst, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
    except Exception as exc:
        dst.unlink(missing_ok=True)
        raise EmitNetworkError(f"Download failed: {exc}") from exc


class EmitScene:
    def __init__(
        self,
        reflectance: NDArray[np.float32],
        wavelengths: NDArray[np.float32],
        glt_x: NDArray[np.float32],
        glt_y: NDArray[np.float32],
        good_wavelengths: NDArray[Any] | None = None,
    ) -> None:
        self.reflectance = reflectance
        self.wavelengths = wavelengths
        self.glt_x = glt_x
        self.glt_y = glt_y
        self.good_wavelengths = good_wavelengths

    @classmethod
    def from_file(cls, path: str | Path) -> EmitScene:
        from netCDF4 import Dataset

        with Dataset(str(path), "r") as ds:
            reflect_arr = np.array(ds.variables["reflectance"][:], dtype=np.float32)

            glt_x: NDArray[np.float32] = np.zeros((1, 1), dtype=np.float32)
            glt_y: NDArray[np.float32] = np.zeros((1, 1), dtype=np.float32)
            if "location" in ds.groups:
                loc = ds.groups["location"]
                for name, out_varname in [
                    ("glt_x", "glt_x"),
                    ("ortho_x", "glt_x"),
                    ("glt_y", "glt_y"),
                    ("ortho_y", "glt_y"),
                ]:
                    if name in loc.variables and out_varname == "glt_x":
                        glt_x = np.asarray(loc.variables[name][:], dtype=np.float32)
                    if name in loc.variables and out_varname == "glt_y":
                        glt_y = np.asarray(loc.variables[name][:], dtype=np.float32)

            wavelengths: NDArray[np.float32]
            if (
                "sensor_band_parameters" in ds.groups
                and "wavelengths" in ds.groups["sensor_band_parameters"].variables
            ):
                wavelengths = np.asarray(
                    ds.groups["sensor_band_parameters"].variables["wavelengths"][:],
                    dtype=np.float32,
                )
            elif "wavelengths" in ds.variables:
                wavelengths = np.asarray(
                    ds.variables["wavelengths"][:], dtype=np.float32
                )
            else:
                wavelengths = np.linspace(381, 2493, 285, dtype=np.float32)

            if reflect_arr.ndim == 3:
                n_bands = wavelengths.shape[0]
                band_axis = next(
                    (i for i, s in enumerate(reflect_arr.shape) if s == n_bands),
                    None,
                )
                if band_axis is not None and band_axis != 2:
                    reflect_arr = np.moveaxis(reflect_arr, band_axis, -1)

            good_wavelengths = None
            if "sensor_band_parameters" in ds.groups:
                sbp = ds.groups["sensor_band_parameters"]
                if "good_wavelengths" in sbp.variables:
                    gw = np.array(sbp.variables["good_wavelengths"][:])
                    good_wavelengths = (
                        gw.astype(bool) if gw.dtype.kind in ("u", "i") else gw
                    )

        return cls(reflect_arr, wavelengths, glt_x, glt_y, good_wavelengths)

    @classmethod
    def from_granule(cls, granule: dict[str, Any]) -> EmitScene:
        href = granule.get("asset_href", "")
        if not href:
            raise ValueError("No asset_href in granule")

        tmp = tempfile.NamedTemporaryFile(suffix=".nc", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()

        try:
            _download_granule_to_file(href, tmp_path)
            return cls.from_file(tmp_path)
        except EmitError:
            raise
        except Exception as exc:
            raise EmitMalformedFileError(
                f"Failed to read downloaded EMIT file: {exc}"
            ) from exc
        finally:
            tmp_path.unlink(missing_ok=True)

    def get_effective_band_indices(self) -> list[int]:
        if self.good_wavelengths is not None:
            gw = np.asarray(self.good_wavelengths)
            return [int(i) for i, v in enumerate(gw) if v]
        return list(range(self.wavelengths.shape[0]))

    def orthorectify(
        self, tile_size: int = 256
    ) -> Iterator[tuple[int, int, int, int, NDArray[np.float32]]]:
        if self.glt_x.size <= 1 or self.glt_y.size <= 1:
            return

        glt_x = self.glt_x
        glt_y = self.glt_y
        s_h, s_w = self.reflectance.shape[0], self.reflectance.shape[1]
        o_h, o_w = glt_x.shape[0], glt_x.shape[1]
        b = self.reflectance.shape[2]

        valid = (
            np.isfinite(glt_x)
            & np.isfinite(glt_y)
            & (glt_x >= 0)
            & (glt_x < s_w)
            & (glt_y >= 0)
            & (glt_y < s_h)
        )

        if not np.any(valid):
            return

        vrows, vcols = np.where(valid)
        min_y, max_y = int(np.min(vrows)), int(np.max(vrows))
        min_x, max_x = int(np.min(vcols)), int(np.max(vcols))

        for y0 in range(min_y, max_y + 1, tile_size):
            y1 = min(y0 + tile_size, max_y + 1)
            for x0 in range(min_x, max_x + 1, tile_size):
                x1 = min(x0 + tile_size, max_x + 1)
                t_h, t_w = y1 - y0, x1 - x0

                mask = (
                    (np.arange(o_h)[:, None] >= y0)
                    & (np.arange(o_h)[:, None] < y1)
                    & (np.arange(o_w)[None, :] >= x0)
                    & (np.arange(o_w)[None, :] < x1)
                    & valid
                )

                if not np.any(mask):
                    continue

                tile = np.full((t_h, t_w, b), np.nan, dtype=np.float32)
                rows, cols = np.where(mask)
                sx = glt_x[rows, cols].astype(np.int32)
                sy = glt_y[rows, cols].astype(np.int32)
                ty = rows - y0
                tx = cols - x0
                tile[ty, tx, :] = self.reflectance[sy, sx, :]

                yield (y0, y1, x0, x1, tile)

    def get_bbox(self) -> tuple[float, float, float, float]:
        h, w = self.glt_x.shape
        ys: list[int] = []
        xs: list[int] = []
        for r, c in [(0, 0), (0, w - 1), (h - 1, 0), (h - 1, w - 1)]:
            if np.isfinite(self.glt_y[r, c]) and np.isfinite(self.glt_x[r, c]):
                ys.append(int(self.glt_y[r, c]))
                xs.append(int(self.glt_x[r, c]))
        if not ys:
            return (0.0, 0.0, 0.0, 0.0)
        return (float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys)))
