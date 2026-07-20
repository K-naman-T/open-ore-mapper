import numpy as np

from open_ore_mapper.sam import angles_to_strength, compute_sam_angles, compute_sam_cube


def test_identical_spectra_have_zero_angle() -> None:
    pixels = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    refs = np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    angles = compute_sam_angles(pixels, refs)
    assert float(angles[0, 0]) == np.float32(0.0)


def test_orthogonal_spectra_have_ninety_degree_angle() -> None:
    pixels = np.array([[1.0, 0.0]], dtype=np.float32)
    refs = np.array([[0.0, 1.0]], dtype=np.float32)
    angles = compute_sam_angles(pixels, refs)
    assert float(angles[0, 0]) == np.float32(90.0)


def test_strength_decreases_with_angle() -> None:
    strength = angles_to_strength(np.array([[0.0, 45.0, 90.0]], dtype=np.float32))
    assert float(strength[0, 0]) > float(strength[0, 1])
    assert float(strength[0, 1]) > float(strength[0, 2])
    assert float(strength[0, 0]) == np.float32(1.0)
    assert float(strength[0, 2]) == np.float32(0.0)


def test_cube_sam_returns_angle_cube_and_labels() -> None:
    cube = np.array([[[1.0, 0.0], [0.0, 1.0]]], dtype=np.float32)
    refs = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    angles, labels = compute_sam_cube(cube, refs)
    assert angles.shape == (1, 2, 2)
    assert labels.tolist() == [[0, 1]]
