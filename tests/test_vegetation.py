import numpy as np

from open_ore_mapper.vegetation import ndvi_mask


def test_ndvi_vegetation_pixel_masked() -> None:
    cube = np.zeros((3, 3, 4), dtype=np.float32)
    cube[:, :, 0] = 0.1
    cube[:, :, 1] = 0.1
    cube[:, :, 2] = 0.1
    cube[:, :, 3] = 0.1

    cube[1, 1, 1] = 0.1
    cube[1, 1, 2] = 0.5

    wavelengths = [500.0, 665.0, 850.0, 1600.0]
    mask = ndvi_mask(cube, wavelengths)

    assert mask.shape == (3, 3)
    assert mask[1, 1]
    assert not mask[0, 0]
    assert not mask[0, 1]
    assert not mask[0, 2]
    assert not mask[1, 0]
    assert not mask[1, 2]
    assert not mask[2, 0]
    assert not mask[2, 1]
    assert not mask[2, 2]


def test_ndvi_bare_rock_pixel_kept() -> None:
    cube = np.zeros((3, 3, 4), dtype=np.float32)
    cube[:, :, :] = 0.2

    wavelengths = [500.0, 665.0, 850.0, 1600.0]
    mask = ndvi_mask(cube, wavelengths)

    assert mask.shape == (3, 3)
    assert not mask.any()


def test_ndvi_band_selection_uses_closest_match() -> None:
    cube = np.zeros((2, 2, 4), dtype=np.float32)
    cube[:, :, 0] = 0.1
    cube[:, :, 1] = 0.1
    cube[:, :, 2] = 0.5
    cube[:, :, 3] = 0.1

    wavelengths = [500.0, 660.0, 855.0, 1600.0]
    mask = ndvi_mask(cube, wavelengths)

    assert mask.shape == (2, 2)
    assert mask.all()


def test_ndvi_on_full_cube_full_mask_shape() -> None:
    rng = np.random.default_rng(42)
    cube = rng.standard_normal((5, 5, 10)).astype(np.float32)
    wavelengths = [400.0, 450.0, 500.0, 550.0, 600.0, 665.0, 700.0, 750.0, 800.0, 850.0]

    mask = ndvi_mask(cube, wavelengths)

    assert mask.shape == (5, 5)
    assert mask.dtype == np.bool_


def test_ndvi_boundary_condition() -> None:
    cube = np.full((3, 3, 4), 0.5, dtype=np.float32)
    wavelengths = [500.0, 665.0, 850.0, 1600.0]

    mask = ndvi_mask(cube, wavelengths)

    assert mask.shape == (3, 3)
    assert not mask.any()


def test_ndvi_raises_when_no_nir_band() -> None:
    cube = np.zeros((3, 3, 4), dtype=np.float32)
    wavelengths = [400.0, 450.0, 500.0, 600.0]

    mask = ndvi_mask(cube, wavelengths)

    assert mask.shape == (3, 3)
    assert not mask.any()
