import pytest

from open_ore_mapper.tiling import iter_tiles


def test_iter_tiles_covers_full_raster() -> None:
    tiles = list(iter_tiles(height=5, width=6, tile_size=4))
    covered = set()
    for row0, row1, col0, col1 in tiles:
        for row in range(row0, row1):
            for col in range(col0, col1):
                covered.add((row, col))
    assert len(covered) == 30
    assert (4, 5) in covered


def test_bad_tile_size_fails() -> None:
    with pytest.raises(ValueError):
        list(iter_tiles(height=5, width=5, tile_size=0))
