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
    if len(sys.argv) != 4:
        raise SystemExit("usage: write_vdb.py DENSITY.npy COLOR.npy OUTPUT.vdb")
    density_source, color_source, destination = map(Path, sys.argv[1:])
    density_array = np.ascontiguousarray(np.load(density_source, allow_pickle=False), dtype=np.float32)
    color_array = np.ascontiguousarray(np.load(color_source, allow_pickle=False), dtype=np.float32)
    if color_array.shape != density_array.shape + (3,):
        raise SystemExit(f"color shape {color_array.shape} does not match density shape {density_array.shape} + (3,)")
    density = openvdb.FloatGrid()
    density.name = "density"
    density.copyFromArray(density_array)
    color = openvdb.Vec3SGrid()
    color.name = "color"
    color.copyFromArray(color_array)
    for grid in (density, color):
        if hasattr(grid, "pruneGrid"):
            grid.pruneGrid(0.0)
    openvdb.write(str(destination), grids=[density, color])


if __name__ == "__main__":
    main()
