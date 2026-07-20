from __future__ import annotations

import base64
import io
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray
from PIL import Image

from .schemas import MineralStatistics


CLASS_COLORS = np.array(
    [
        [177, 56, 36],
        [214, 117, 39],
        [231, 178, 57],
        [82, 84, 91],
        [136, 92, 48],
        [194, 134, 79],
        [121, 86, 45],
        [78, 126, 153],
        [78, 153, 116],
        [119, 92, 163],
        [181, 77, 122],
        [108, 111, 61],
    ],
    dtype=np.uint8,
)
UNKNOWN_COLOR = np.array([20, 20, 20], dtype=np.uint8)


def _png_data_url(rgb: NDArray[np.uint8]) -> str:
    buffer = io.BytesIO()
    Image.fromarray(rgb.astype(np.uint8)).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")


def class_map_png_data_url(class_map: NDArray[np.integer[Any]], minerals: list[str]) -> str:
    rgb = np.zeros((*class_map.shape, 3), dtype=np.uint8)
    rgb[:] = UNKNOWN_COLOR
    for idx, _name in enumerate(minerals):
        rgb[class_map == idx] = CLASS_COLORS[idx % len(CLASS_COLORS)]
    return _png_data_url(cast(NDArray[np.uint8], rgb))


def confidence_png_data_url(confidence: NDArray[np.floating[Any]]) -> str:
    scaled = np.clip(confidence, 0.0, 1.0)
    gray = (scaled * 255).astype(np.uint8)
    rgb = np.stack([gray, gray, gray], axis=2)
    return _png_data_url(cast(NDArray[np.uint8], rgb))


def mineral_statistics(
    class_map: NDArray[np.integer[Any]],
    confidence: NDArray[np.floating[Any]],
    abundances: NDArray[np.floating[Any]],
    minerals: list[str],
) -> dict[str, MineralStatistics]:
    total = int(class_map.size)
    stats: dict[str, MineralStatistics] = {}
    for idx, name in enumerate(minerals):
        mask = class_map == idx
        count = int(mask.sum())
        if count == 0:
            stats[name] = MineralStatistics(0, 0.0, 0.0, 0.0)
        else:
            stats[name] = MineralStatistics(
                count=count,
                percentage=100.0 * count / total,
                mean_confidence=float(confidence[mask].mean()),
                mean_abundance=float(abundances[:, :, idx][mask].mean()),
            )
    return stats
