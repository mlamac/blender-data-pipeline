from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

from .config import load_config, resolve_path
from .data import load_series
from .processing import finalize_bundle, invoke_blender, mapping_limits, prepare_bundle


def generate_example(output: Path, frames: int) -> None:
    output.mkdir(parents=True, exist_ok=True)
    x = np.linspace(-2.0, 2.0, 64)
    y = np.linspace(-2.0, 2.0, 64)
    z = np.linspace(-2.0, 2.0, 64)
    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
    names = []
    envelope = np.exp(-(xx**2 / (2 * 0.9**2) + yy**2 / (2 * 0.7**2) + zz**2 / (2 * 0.55**2)))
    wavelength = 0.9
    for index in range(frames):
        t = index / frames
        carrier = np.cos(2 * np.pi * (xx / wavelength - t))
        field = (envelope * carrier).astype(np.float32)
        name = f"carrier_{index + 1:04d}.npz"
        np.savez_compressed(output / name, field=field, x=x, y=y, z=z, time=np.array(t))
        names.append(name)
    config = {
        "input": {"files": names, "field_key": "field"},
        "output": {"directory": "build", "archive": True},
        "mapping": {"mode": "linear", "range": "explicit", "minimum": -2.0, "maximum": 2.0, "colormap": "seismic"},
        "volume": {"density_scale": 1.5, "cutoff": 0.03},
        "shells": {"enabled": True, "isovalue": 0.25, "volume_density_multiplier": 0.5},
        "geometry": {"aspect_mode": "preserve_physical_aspect", "box_size": 4.0},
        "slices": [
            {"axis": "x", "coordinate": 0.0, "face": "min"},
            {"axis": "y", "coordinate": 0.0, "face": "max"},
            {"axis": "z", "coordinate": 0.0, "face": "min"},
        ],
        "labels": {"x": "x", "y": "y", "z": "z", "field": "E / E0", "time": "phase [cycles]", "title": "Gaussian-envelope carrier wave"},
    }
    (output / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=True), encoding="utf-8")


def cmd_validate(config_path: str) -> int:
    cfg, _ = load_config(config_path)
    frames = load_series(cfg)
    low, high = mapping_limits(frames, cfg["mapping"])
    first = frames[0]
    report = {
        "frames": len(frames),
        "shape": list(first.field.shape),
        "x": [float(first.x[0]), float(first.x[-1]), float(np.diff(first.x)[0])],
        "y": [float(first.y[0]), float(first.y[-1]), float(np.diff(first.y)[0])],
        "z": [float(first.z[0]), float(first.z[-1]), float(np.diff(first.z)[0])],
        "mapping_limits": [low, high],
    }
    print(json.dumps(report, indent=2))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    cfg, _ = load_config(args.config)
    base = Path(cfg["_base_dir"])
    output = resolve_path(str(cfg["output"]["directory"]), base)
    if output.exists():
        if not args.force:
            raise ValueError(f"Output exists: {output}; pass --force to replace it")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    frames = load_series(cfg)
    manifest = prepare_bundle(cfg, frames, output, args.system_python)
    blender = Path(args.blender).expanduser().resolve()
    if not blender.is_file():
        raise ValueError(f"Blender executable not found: {blender}")
    invoke_blender(blender, manifest, output, args.preview)
    archive = finalize_bundle(output, cfg)
    print(f"Scene: {output / 'scene.blend'}")
    if archive:
        print(f"Archive: {archive}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="bdp", description="Prepare volumetric NumPy data for Blender")
    sub = result.add_subparsers(dest="command", required=True)
    example = sub.add_parser("example", help="generate the Gaussian-envelope carrier-wave example")
    example.add_argument("--output", type=Path, default=Path("examples/carrier_wave"))
    example.add_argument("--frames", type=int, default=20)
    validate = sub.add_parser("validate", help="validate a dataset and configuration")
    validate.add_argument("config")
    build = sub.add_parser("build", help="build Blender scene and portable bundle")
    build.add_argument("config")
    build.add_argument("--blender", required=True)
    build.add_argument("--system-python", default="/usr/bin/python3")
    build.add_argument("--preview", action="store_true", help="also render a low-sample preview.png")
    build.add_argument("--force", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "example":
            if args.frames < 1:
                raise ValueError("--frames must be positive")
            generate_example(args.output.resolve(), args.frames)
            print(f"Example written to {args.output.resolve()}")
            return 0
        if args.command == "validate":
            return cmd_validate(args.config)
        return cmd_build(args)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
