import pytest

from spectral_matching.tiling import iter_tiles


def test_iter_tiles_covers_full_raster() -> None:
    tiles = list(iter_tiles(height=5, width=6, tile_size=4))
    covered = set()
    for row0, row1, col0, col1 in tiles:
        for row in range(row0, row1):
            for col in range(col0, col1):
                covered.add((row, col))
    assert len(covered) == 30
    assert (4, 5) in covered


def test_iter_tiles_exact_fit_produces_exact_tiles() -> None:
    tiles = list(iter_tiles(height=8, width=8, tile_size=4))
    assert len(tiles) == 4
    assert tiles[0] == (0, 4, 0, 4)
    assert tiles[1] == (0, 4, 4, 8)
    assert tiles[2] == (4, 8, 0, 4)
    assert tiles[3] == (4, 8, 4, 8)


def test_iter_tiles_single_pixel_raster() -> None:
    tiles = list(iter_tiles(height=1, width=1, tile_size=4))
    assert len(tiles) == 1
    assert tiles[0] == (0, 1, 0, 1)


def test_bad_tile_size_raises() -> None:
    with pytest.raises(ValueError, match="tile_size must be positive"):
        list(iter_tiles(height=5, width=5, tile_size=0))


def test_bad_tile_size_negative_raises() -> None:
    with pytest.raises(ValueError, match="tile_size must be positive"):
        list(iter_tiles(height=5, width=5, tile_size=-1))
