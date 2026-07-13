#!/usr/bin/env python3
"""Small system-Python bridge: dense normalized NumPy array -> sparse OpenVDB."""

import argparse
from pathlib import Path

import numpy as np

try:
    import openvdb
except ImportError:
    try:
        import pyopenvdb as openvdb
    except ImportError as exc:
        raise SystemExit("python3-openvdb is required (sudo apt install python3-openvdb python3-numpy)") from exc


def scalar_grid(source: Path):
    values = np.ascontiguousarray(np.load(source, allow_pickle=False), dtype=np.float32)
    grid = openvdb.FloatGrid()
    grid.name = "density"
    grid.copyFromArray(values)
    if hasattr(grid, "pruneGrid"):
        grid.pruneGrid(0.0)
    return grid, values.shape


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("density", type=Path)
    parser.add_argument("color", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--positive", nargs=2, metavar=("ARRAY", "OUTPUT"), type=Path)
    parser.add_argument("--negative", nargs=2, metavar=("ARRAY", "OUTPUT"), type=Path)
    return parser.parse_args()


def main() -> None:
    args = arguments()
    density_source, color_source, destination = args.density, args.color, args.output
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
    for optional in (args.positive, args.negative):
        if optional:
            source, output = optional
            grid, shape = scalar_grid(source)
            if shape != density_array.shape:
                raise SystemExit(f"shell shape {shape} does not match density shape {density_array.shape}")
            openvdb.write(str(output), grids=[grid])


if __name__ == "__main__":
    main()
