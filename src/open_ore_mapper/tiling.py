from __future__ import annotations

from collections.abc import Iterator


def iter_tiles(height: int, width: int, tile_size: int) -> Iterator[tuple[int, int, int, int]]:
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")
    for row0 in range(0, height, tile_size):
        row1 = min(height, row0 + tile_size)
        for col0 in range(0, width, tile_size):
            col1 = min(width, col0 + tile_size)
            yield row0, row1, col0, col1
