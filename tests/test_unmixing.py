import numpy as np

from open_ore_mapper.unmixing import estimate_nnls_abundances


def test_pure_reference_maps_to_single_high_abundance() -> None:
    refs = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    pixels = np.array([[1.0, 0.0]], dtype=np.float32)
    abundances = estimate_nnls_abundances(pixels, refs)
    assert abundances.shape == (1, 2)
    assert float(abundances[0, 0]) > 0.99
    assert float(abundances[0, 1]) < 0.01


def test_mixed_pixel_abundance_is_normalized() -> None:
    refs = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    pixels = np.array([[0.25, 0.75]], dtype=np.float32)
    abundances = estimate_nnls_abundances(pixels, refs)
    assert float(abundances.sum()) == np.float32(1.0)
    assert float(abundances[0, 1]) > float(abundances[0, 0])
