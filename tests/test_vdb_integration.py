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
    destination = tmp_path / "density.vdb"
    values = np.zeros((5, 6, 7), dtype=np.float32)
    values[1:4, 2:5, 3:6] = 0.75
    np.save(source, values)
    script = Path(__file__).parents[1] / "scripts" / "write_vdb.py"
    subprocess.run([SYSTEM_PYTHON, str(script), str(source), str(destination)], check=True)
    probe = (
        "import pyopenvdb as v; g=v.read(%r, 'density'); "
        "import numpy as n; lo,hi=g.evalActiveVoxelBoundingBox(); "
        "a=n.zeros(tuple(hi[i]-lo[i]+1 for i in range(3)), dtype=n.float32); "
        "g.copyToArray(a, ijk=lo); assert g.name == 'density'; "
        "assert a.shape == (3,3,3) and float(a.max()) == 0.75"
    ) % str(destination)
    subprocess.run([SYSTEM_PYTHON, "-c", probe], check=True)
