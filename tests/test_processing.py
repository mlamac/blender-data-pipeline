from pathlib import Path

import numpy as np

from blender_data_pipeline.data import Frame
from blender_data_pipeline.processing import mapping_limits, normalize, sample_slice


def frame(values):
    values = np.asarray(values, dtype=np.float32)
    axes = [np.arange(n, dtype=float) for n in values.shape]
    return Frame(Path("test.npz"), values, *axes, 0.0)


def test_global_limits_and_linear_normalization():
    frames = [frame(np.array([[[0, 1]]])), frame(np.array([[[2, 4]]]))]
    mapping = {"mode": "linear", "range": "global", "minimum": None, "maximum": None, "percentiles": None}
    low, high = mapping_limits(frames, mapping)
    assert (low, high) == (0, 4)
    assert np.allclose(normalize(np.array([0, 2, 4]), low, high, mapping), [0, 0.5, 1])


def test_log_zero_stays_transparent():
    mapping = {"mode": "log10", "log_floor": 1e-2}
    result = normalize(np.array([0, 1e-2, 1]), 0, 1, mapping)
    assert np.allclose(result, [0, 0, 1])


def test_slice_interpolates_requested_coordinate_and_orientation():
    x, y, z = np.arange(2.0), np.arange(3.0), np.arange(4.0)
    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
    field = 100 * xx + 10 * yy + zz
    plane = sample_slice(field, (x, y, z), "x", 0.5)
    assert plane.shape == (4, 3)
    assert plane[0, 0] == 53  # top image row is z=max
    assert plane[-1, -1] == 70
