from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from .rendering import CLASS_COLORS, UNKNOWN_COLOR

TILE_SIZE = 256
TILES_DIR = Path("data/tiles")

# Conservative identifier alphabet for map_uuid:
# Must start with an alphanumeric character, followed by
# alphanumeric, hyphens, or underscores.  Max 64 chars.
# Generated IDs are short hex (uuid4.hex[:12]) but legacy maps
# may contain hyphens and underscores.
_VALID_MAP_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")

# Sanity cap on zoom level (far beyond any practical mineral tile set).
MAX_ZOOM = 30


def validate_map_uuid(map_uuid: str) -> None:
    """Raise ValueError if map_uuid contains path-traversal or invalid characters."""
    if not _VALID_MAP_ID_RE.match(map_uuid):
        raise ValueError(f"Invalid map_uuid: {map_uuid!r}")


def validate_tile_coords(z: int, x: int, y: int) -> None:
    """Raise ValueError if tile coordinates are negative or zoom exceeds MAX_ZOOM."""
    if z < 0 or x < 0 or y < 0:
        raise ValueError(f"Negative tile coordinates: ({z}, {x}, {y})")
    if z > MAX_ZOOM:
        raise ValueError(f"Zoom level {z} exceeds maximum {MAX_ZOOM}")


def write_tiles(
    class_map: NDArray[np.uint8],
    confidence: NDArray[np.float32],
    minerals: list[str],
    map_uuid: str,
    bbox: tuple[float, float, float, float],
    tiles_dir: Path | None = None,
) -> Path:
    tiles_dir = tiles_dir or TILES_DIR
    validate_map_uuid(map_uuid)
    tile_root = tiles_dir / map_uuid

    H, W = class_map.shape[:2]
    nx = int(np.ceil(W / TILE_SIZE))
    ny = int(np.ceil(H / TILE_SIZE))
    max_zoom = 0
    if nx > 1 or ny > 1:
        max_zoom = int(np.ceil(np.log2(max(nx, ny))))

    metadata: dict[str, Any] = {
        "map_uuid": map_uuid,
        "bbox": list(bbox),
        "bounds": [0, 0, W, H],
        "min_zoom": 0,
        "max_zoom": max_zoom,
        "tile_size": TILE_SIZE,
        "minerals": minerals,
        "scene_shape": [H, W],
    }

    for z in range(max_zoom + 1):
        z_dir = tile_root / str(z)
        z_dir.mkdir(parents=True, exist_ok=True)

        scale_factor = 2 ** (max_zoom - z)
        tiles_x = int(np.ceil(W / (TILE_SIZE * scale_factor)))
        tiles_y = int(np.ceil(H / (TILE_SIZE * scale_factor)))

        for tx in range(tiles_x):
            x_dir = z_dir / str(tx)
            x_dir.mkdir(parents=True, exist_ok=True)

            for ty in range(tiles_y):
                x_start = tx * TILE_SIZE * scale_factor
                x_end = min(W, (tx + 1) * TILE_SIZE * scale_factor)
                y_start = ty * TILE_SIZE * scale_factor
                y_end = min(H, (ty + 1) * TILE_SIZE * scale_factor)

                cm_slice = class_map[y_start:y_end, x_start:x_end]
                conf_slice = confidence[y_start:y_end, x_start:x_end]

                tile = _render_tile(cm_slice, conf_slice, minerals)
                tile.save(str(x_dir / f"{ty}.png"))

    meta_path = tile_root / "metadata.json"
    meta_path.write_text(json.dumps(metadata))

    return tile_root


def _safe_tile_path(tiles_dir: Path, map_uuid: str, z: int, x: int, y: int) -> Path:
    """Build a resolved tile path, raising ValueError on traversal / invalid input."""
    validate_map_uuid(map_uuid)
    validate_tile_coords(z, x, y)
    root = tiles_dir.resolve()
    candidate = root / map_uuid / str(z) / str(x) / f"{y}.png"
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Resolved tile path {candidate} is not under tile root {root}"
        )
    return candidate


def get_tile_path(
    map_uuid: str, z: int, x: int, y: int, tiles_dir: Path | None = None
) -> Path | None:
    tiles_dir = tiles_dir or TILES_DIR
    try:
        path = _safe_tile_path(tiles_dir, map_uuid, z, x, y)
    except ValueError:
        return None
    if path.exists():
        return path
    return None


def get_tile_metadata(map_uuid: str, tiles_dir: Path | None = None) -> dict[str, Any] | None:
    tiles_dir = tiles_dir or TILES_DIR
    validate_map_uuid(map_uuid)
    meta_path = tiles_dir / map_uuid / "metadata.json"
    if meta_path.exists():
        return cast(dict[str, Any], json.loads(meta_path.read_text()))
    return None


def _render_tile(
    class_map_slice: NDArray[np.uint8],
    confidence_slice: NDArray[np.float32],
    minerals: list[str],
) -> Image.Image:
    h, w = class_map_slice.shape[:2]
    rgb = np.full((h, w, 3), UNKNOWN_COLOR, dtype=np.uint8)
    for idx in range(len(minerals)):
        mask = class_map_slice == idx
        rgb[mask] = CLASS_COLORS[idx % len(CLASS_COLORS)]

    if h != TILE_SIZE or w != TILE_SIZE:
        rgb_img = Image.fromarray(rgb, mode="RGB")
        rgb_img = rgb_img.resize((TILE_SIZE, TILE_SIZE), Image.NEAREST)
        return rgb_img

    return Image.fromarray(rgb, mode="RGB")
