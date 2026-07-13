#!/usr/bin/env python3
"""Small system-Python bridge: dense normalized NumPy array -> sparse OpenVDB."""

from pathlib import Path
import sys

import numpy as np

try:
    import openvdb
except ImportError:
    try:
        import pyopenvdb as openvdb
    except ImportError as exc:
        raise SystemExit("python3-openvdb is required (sudo apt install python3-openvdb python3-numpy)") from exc


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: write_vdb.py INPUT.npy OUTPUT.vdb")
    source, destination = map(Path, sys.argv[1:])
    array = np.ascontiguousarray(np.load(source, allow_pickle=False), dtype=np.float32)
    grid = openvdb.FloatGrid()
    grid.name = "density"
    grid.copyFromArray(array)
    if hasattr(grid, "pruneGrid"):
        grid.pruneGrid(0.0)
    openvdb.write(str(destination), grids=[grid])


if __name__ == "__main__":
    main()
