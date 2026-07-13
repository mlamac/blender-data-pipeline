from pathlib import Path

import numpy as np
import pytest

from blender_data_pipeline.data import load_frame, load_series


def write_frame(path: Path, field, x, y, z, time=0.0):
    np.savez(path, field=field, x=x, y=y, z=z, time=np.array(time))


def test_load_descending_axis_reorients_field(tmp_path):
    x = np.array([2.0, 1.0, 0.0])
    y = np.array([0.0, 1.0])
    z = np.array([0.0, 1.0])
    field = np.arange(12).reshape(3, 2, 2)
    path = tmp_path / "frame.npz"
    write_frame(path, field, x, y, z)
    frame = load_frame(path)
    assert np.array_equal(frame.x, [0, 1, 2])
    assert np.array_equal(frame.field, field[::-1])


@pytest.mark.parametrize("bad", [np.array([0.0, 1.0, 2.2]), np.array([0.0, 1.0, 0.5])])
def test_rejects_nonuniform_or_nonmonotonic_axis(tmp_path, bad):
    path = tmp_path / "frame.npz"
    write_frame(path, np.ones((3, 2, 2)), bad, [0, 1], [0, 1])
    with pytest.raises(ValueError):
        load_frame(path)


def test_series_requires_matching_coordinates(tmp_path):
    for i, x in enumerate(([0, 1], [0, 2])):
        write_frame(tmp_path / f"f{i}.npz", np.ones((2, 2, 2)), x, [0, 1], [0, 1], i)
    cfg = {"_base_dir": str(tmp_path), "input": {"files": ["f0.npz", "f1.npz"], "field_key": "field"}}
    with pytest.raises(ValueError, match="share shape and coordinates"):
        load_series(cfg)
