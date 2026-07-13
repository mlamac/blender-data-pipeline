import subprocess
from pathlib import Path

import numpy as np
import pytest


SYSTEM_PYTHON = "/usr/bin/python3"


@pytest.mark.skipif(
    subprocess.run([SYSTEM_PYTHON, "-c", "import pyopenvdb"], capture_output=True).returncode != 0,
    reason="Ubuntu python3-openvdb is not installed",
)
def test_vdb_bridge_writes_named_grid_with_expected_shape(tmp_path):
    source = tmp_path / "density.npy"
    color_source = tmp_path / "color.npy"
    positive_source = tmp_path / "positive.npy"
    negative_source = tmp_path / "negative.npy"
    destination = tmp_path / "density.vdb"
    positive_destination = tmp_path / "positive.vdb"
    negative_destination = tmp_path / "negative.vdb"
    values = np.zeros((5, 6, 7), dtype=np.float32)
    values[1:4, 2:5, 3:6] = 0.75
    np.save(source, values)
    colors = np.zeros(values.shape + (3,), dtype=np.float32)
    colors[values > 0] = (1.0, 0.0, 0.5)
    np.save(color_source, colors)
    np.save(positive_source, values)
    np.save(negative_source, values * 0.5)
    script = Path(__file__).parents[1] / "scripts" / "write_vdb.py"
    subprocess.run([
        SYSTEM_PYTHON, str(script), str(source), str(color_source), str(destination),
        "--positive", str(positive_source), str(positive_destination),
        "--negative", str(negative_source), str(negative_destination),
    ], check=True)
    probe = (
        "import pyopenvdb as v; g=v.read(%r, 'density'); c=v.read(%r, 'color'); "
        "import numpy as n; lo,hi=g.evalActiveVoxelBoundingBox(); "
        "a=n.zeros(tuple(hi[i]-lo[i]+1 for i in range(3)), dtype=n.float32); "
        "g.copyToArray(a, ijk=lo); assert g.name == 'density'; "
        "assert a.shape == (3,3,3) and float(a.max()) == 0.75; "
        "assert c.name == 'color' and c.activeVoxelCount() == 27"
    ) % (str(destination), str(destination))
    subprocess.run([SYSTEM_PYTHON, "-c", probe], check=True)
    shell_probe = (
        "import pyopenvdb as v; "
        "p=v.read(%r, 'density'); n=v.read(%r, 'density'); "
        "assert p.name == n.name == 'density'; "
        "assert p.activeVoxelCount() == n.activeVoxelCount() == 27"
    ) % (str(positive_destination), str(negative_destination))
    subprocess.run([SYSTEM_PYTHON, "-c", shell_probe], check=True)
