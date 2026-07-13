from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/bdp-matplotlib")
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib
import numpy as np
from PIL import Image

from .config import resolve_path
from .data import Frame


def mapping_limits(frames: list[Frame], mapping: dict[str, Any]) -> tuple[float, float]:
    if mapping.get("range") == "explicit":
        low, high = mapping.get("minimum"), mapping.get("maximum")
        if low is None or high is None:
            raise ValueError("Explicit mapping range requires minimum and maximum")
        low, high = float(low), float(high)
    else:
        percentiles = mapping.get("percentiles")
        if percentiles:
            if len(percentiles) != 2 or not 0 <= percentiles[0] < percentiles[1] <= 100:
                raise ValueError("mapping.percentiles must be [low, high] within 0..100")
            values = np.concatenate([frame.field.ravel() for frame in frames])
            low, high = (float(v) for v in np.percentile(values, percentiles))
        else:
            low = min(float(np.min(frame.field)) for frame in frames)
            high = max(float(np.max(frame.field)) for frame in frames)
        if mapping.get("minimum") is not None:
            low = float(mapping["minimum"])
        if mapping.get("maximum") is not None:
            high = float(mapping["maximum"])
    if not np.isfinite([low, high]).all() or high <= low:
        raise ValueError(f"Invalid mapping limits [{low}, {high}]")
    if mapping.get("mode") == "log10" and mapping.get("symmetric", False):
        raise ValueError("log10 mapping cannot use a symmetric signed range")
    if mapping.get("mode") == "log10" and high <= 0:
        raise ValueError("log10 mapping requires a positive maximum")
    if mapping.get("mode") == "log10" and low < 0:
        raise ValueError("log10 mapping does not support signed fields; use linear mapping")
    if mapping.get("symmetric", False):
        extent = max(abs(low), abs(high))
        if extent == 0:
            raise ValueError("Cannot create a symmetric range from an all-zero field")
        low, high = -extent, extent
    if mapping.get("mode") not in {"linear", "log10"}:
        raise ValueError("mapping.mode must be 'linear' or 'log10'")
    return low, high


def normalize(values: np.ndarray, low: float, high: float, mapping: dict[str, Any]) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    if mapping.get("mode") == "linear":
        result = (values - low) / (high - low)
    else:
        positive = values[values > 0]
        auto_floor = float(np.min(positive)) if positive.size else high * 1e-12
        floor = float(mapping.get("log_floor") or max(auto_floor, high * 1e-12))
        floor = max(floor, np.finfo(np.float32).tiny)
        log_low = np.log10(max(low, floor))
        log_high = np.log10(high)
        result = (np.log10(np.maximum(values, floor)) - log_low) / (log_high - log_low)
        result = np.where(values <= 0, 0.0, result)
    return np.clip(result, 0.0, 1.0).astype(np.float32)


def opacity(values: np.ndarray, low: float, high: float, mapping: dict[str, Any]) -> np.ndarray:
    values = np.asarray(values, dtype=np.float32)
    if mapping.get("mode") == "log10":
        return normalize(values, low, high, mapping)
    transparent = float(mapping.get("transparent_value", 0.0))
    scale = max(abs(low - transparent), abs(high - transparent))
    if scale <= 0:
        raise ValueError("Opacity scale is zero; adjust mapping limits or transparent_value")
    return np.clip(np.abs(values - transparent) / scale, 0.0, 1.0).astype(np.float32)


def sample_slice(field: np.ndarray, axes: tuple[np.ndarray, np.ndarray, np.ndarray], axis: str, coordinate: float) -> np.ndarray:
    index = {"x": 0, "y": 1, "z": 2}[axis]
    coordinates = axes[index]
    if coordinate < coordinates[0] or coordinate > coordinates[-1]:
        raise ValueError(f"Slice {axis}={coordinate} lies outside [{coordinates[0]}, {coordinates[-1]}]")
    upper = int(np.searchsorted(coordinates, coordinate, side="right"))
    if upper == 0:
        plane = np.take(field, 0, axis=index)
    elif upper >= len(coordinates):
        plane = np.take(field, -1, axis=index)
    else:
        lower = upper - 1
        weight = float((coordinate - coordinates[lower]) / (coordinates[upper] - coordinates[lower]))
        plane = (1.0 - weight) * np.take(field, lower, axis=index) + weight * np.take(field, upper, axis=index)
    # PIL's first image row is the top. Transpose from remaining axis order and
    # flip vertically so positive plot vertical coordinates point upward.
    return np.flipud(np.asarray(plane).T)


def rgba_image(normalized: np.ndarray, alpha: np.ndarray, colormap: str) -> Image.Image:
    try:
        cmap = matplotlib.colormaps[colormap]
    except KeyError as exc:
        raise ValueError(f"Unknown Matplotlib colormap '{colormap}'") from exc
    rgba = cmap(np.clip(normalized, 0.0, 1.0), bytes=True)
    rgba[..., 3] = np.asarray(np.clip(alpha, 0, 1) * 255, dtype=np.uint8)
    return Image.fromarray(rgba, mode="RGBA")


def colorbar_image(colormap: str, width: int = 64, height: int = 512) -> Image.Image:
    # Image row zero is the top, so high values are placed at the top.
    values = np.repeat(np.linspace(1.0, 0.0, height, dtype=np.float32)[:, None], width, axis=1)
    return rgba_image(values, np.ones_like(values), colormap)


def color_stops(colormap: str, count: int = 16) -> list[list[float]]:
    cmap = matplotlib.colormaps[colormap]
    return [[float(v), *[float(c) for c in cmap(v)[:4]]] for v in np.linspace(0, 1, count)]


def _slice_specs(cfg: dict[str, Any], frame: Frame) -> list[dict[str, Any]]:
    specs = cfg.get("slices", [])
    if not isinstance(specs, list) or len(specs) > 3:
        raise ValueError("slices must be a list containing at most three entries")
    seen: set[str] = set()
    result = []
    for raw in specs:
        axis = str(raw.get("axis", "")).lower()
        if axis not in {"x", "y", "z"} or axis in seen:
            raise ValueError("Each slice axis must be one unique value from x, y, z")
        face = str(raw.get("face", "min")).lower()
        if face not in {"min", "max"}:
            raise ValueError("Slice face must be 'min' or 'max'")
        coordinates = getattr(frame, axis)
        coordinate = float(raw.get("coordinate", (coordinates[0] + coordinates[-1]) / 2))
        result.append({"axis": axis, "coordinate": coordinate, "face": face})
        seen.add(axis)
    return result


def prepare_bundle(cfg: dict[str, Any], frames: list[Frame], output: Path, system_python: str) -> Path:
    assets = output / "assets"
    vdb_dir, slice_dir, intermediate = assets / "vdb", assets / "slices", output / ".intermediate"
    for path in (vdb_dir, slice_dir, intermediate):
        path.mkdir(parents=True, exist_ok=True)
    low, high = mapping_limits(frames, cfg["mapping"])
    cutoff = float(cfg["volume"].get("cutoff", 0.001))
    if cutoff < 0 or cutoff >= 1:
        raise ValueError("volume.cutoff must be in [0, 1)")
    specs = _slice_specs(cfg, frames[0])
    root = Path(__file__).resolve().parents[2]
    writer = root / "scripts" / "write_vdb.py"
    slice_sequences: dict[str, list[str]] = {spec["axis"]: [] for spec in specs}
    for number, frame in enumerate(frames, 1):
        mapped = normalize(frame.field, low, high, cfg["mapping"])
        alpha = opacity(frame.field, low, high, cfg["mapping"])
        alpha[alpha < cutoff] = 0.0
        cmap = matplotlib.colormaps[cfg["mapping"]["colormap"]]
        color = np.asarray(cmap(mapped)[..., :3], dtype=np.float32)
        color[alpha == 0] = 0.0
        density_path = intermediate / f"density_{number:04d}.npy"
        color_path = intermediate / f"color_{number:04d}.npy"
        np.save(density_path, alpha)
        np.save(color_path, color)
        vdb_path = vdb_dir / f"density_{number:04d}.vdb"
        subprocess.run([system_python, str(writer), str(density_path), str(color_path), str(vdb_path)], check=True)
        for spec in specs:
            raw_plane = sample_slice(frame.field, (frame.x, frame.y, frame.z), spec["axis"], spec["coordinate"])
            plane = normalize(raw_plane, low, high, cfg["mapping"])
            plane_alpha = opacity(raw_plane, low, high, cfg["mapping"])
            image_path = slice_dir / f"{spec['axis']}_{number:04d}.png"
            rgba_image(plane, plane_alpha, cfg["mapping"]["colormap"]).save(image_path)
            slice_sequences[spec["axis"]].append(str(image_path.relative_to(output)))
    colorbar_path = assets / "colorbar.png"
    colorbar_image(cfg["mapping"]["colormap"]).save(colorbar_path)
    first = frames[0]
    extents = {axis: [float(getattr(first, axis)[0]), float(getattr(first, axis)[-1])] for axis in "xyz"}
    steps = {axis: float(np.diff(getattr(first, axis))[0]) for axis in "xyz"}
    manifest = {
        "format_version": 1,
        "frame_count": len(frames),
        "times": [frame.time if frame.time is not None else float(i) for i, frame in enumerate(frames)],
        "shape": list(first.field.shape),
        "extents": extents,
        "steps": steps,
        "value_limits": [low, high],
        "mapping": cfg["mapping"],
        "volume": cfg["volume"],
        "geometry": cfg["geometry"],
        "labels": cfg["labels"],
        "scene": cfg["scene"],
        "color_stops": color_stops(cfg["mapping"]["colormap"]),
        "colorbar_file": str(colorbar_path.relative_to(output)),
        "vdb_files": [f"assets/vdb/density_{i:04d}.vdb" for i in range(1, len(frames) + 1)],
        "slices": [{**spec, "files": slice_sequences[spec["axis"]]} for spec in specs],
        "source_files": [frame.path.name for frame in frames],
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(intermediate)
    return manifest_path


def invoke_blender(blender: Path, manifest: Path, output: Path, preview: bool) -> None:
    root = Path(__file__).resolve().parents[2]
    command = [str(blender), "--background", "--factory-startup", "--python", str(root / "scripts" / "build_scene.py"), "--", "--manifest", str(manifest), "--output", str(output / "scene.blend")]
    if preview:
        command.append("--preview")
    subprocess.run(command, check=True)
    scene = output / "scene.blend"
    if not scene.is_file() or scene.stat().st_size == 0:
        raise RuntimeError("Blender exited without producing scene.blend; inspect its log above")


def finalize_bundle(output: Path, cfg: dict[str, Any]) -> Path | None:
    for backup in output.glob("*.blend[0-9]"):
        backup.unlink()
    (output / "render_windows.bat").write_text(
        "@echo off\r\nset BLENDER=blender\r\n%BLENDER% -b scene.blend -a\r\n",
        encoding="utf-8",
    )
    (output / "WINDOWS_README.txt").write_text(
        "Keep this folder intact. Open scene.blend with Blender 4.5 LTS, or put blender.exe on PATH and run render_windows.bat.\n"
        "VDB and PNG assets use paths relative to scene.blend. Configure the render device in Blender preferences if GPU rendering is desired.\n",
        encoding="utf-8",
    )
    archive = None
    if cfg["output"].get("archive", True):
        archive = output.with_suffix(".zip")
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as handle:
            for path in sorted(output.rglob("*")):
                if path.is_file() and not path.name.endswith(tuple(f".blend{i}" for i in range(1, 10))):
                    handle.write(path, Path(output.name) / path.relative_to(output))
    return archive
