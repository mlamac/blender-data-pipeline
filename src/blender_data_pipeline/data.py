from __future__ import annotations

from dataclasses import dataclass
from glob import glob
from pathlib import Path
from typing import Any

import numpy as np

from .config import resolve_path


@dataclass
class Frame:
    path: Path
    field: np.ndarray
    x: np.ndarray
    y: np.ndarray
    z: np.ndarray
    time: float | None


def resolve_inputs(cfg: dict[str, Any]) -> list[Path]:
    spec = cfg["input"]
    base = Path(cfg["_base_dir"])
    if "files" in spec:
        paths = [resolve_path(str(item), base) for item in spec["files"]]
    elif "glob" in spec:
        pattern = str(resolve_path(str(spec["glob"]), base))
        paths = [Path(item).resolve() for item in sorted(glob(pattern))]
    else:
        raise ValueError("input must define either 'files' or 'glob'")
    if not paths:
        raise ValueError("Input selection matched no .npz files")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"Input files do not exist: {', '.join(missing)}")
    return paths


def _axis(name: str, raw: np.ndarray) -> tuple[np.ndarray, bool]:
    values = np.asarray(raw, dtype=np.float64)
    if values.ndim != 1 or len(values) < 2 or not np.all(np.isfinite(values)):
        raise ValueError(f"Axis '{name}' must be a finite 1D array with at least two values")
    delta = np.diff(values)
    ascending = bool(np.all(delta > 0))
    descending = bool(np.all(delta < 0))
    if not (ascending or descending):
        raise ValueError(f"Axis '{name}' must be strictly monotonic")
    if not np.allclose(np.abs(delta), abs(delta[0]), rtol=1e-6, atol=max(abs(delta[0]), 1.0) * 1e-10):
        raise ValueError(f"Axis '{name}' is nonuniform; resample it to a uniform Cartesian grid")
    return values, descending


def load_frame(path: Path, field_key: str = "field") -> Frame:
    try:
        with np.load(path, allow_pickle=False) as data:
            required = {field_key, "x", "y", "z"}
            missing = required.difference(data.files)
            if missing:
                raise ValueError(f"{path}: missing NPZ keys {sorted(missing)}")
            field = np.asarray(data[field_key], dtype=np.float32)
            axes = [_axis(name, data[name]) for name in ("x", "y", "z")]
            time = float(np.asarray(data["time"]).reshape(())) if "time" in data.files else None
    except (OSError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(str(path)):
            raise
        raise ValueError(f"Cannot read {path}: {exc}") from exc
    x, y, z = (item[0] for item in axes)
    expected = (len(x), len(y), len(z))
    if field.shape != expected:
        raise ValueError(f"{path}: field shape {field.shape} does not match coordinates {expected}")
    if not np.all(np.isfinite(field)):
        raise ValueError(f"{path}: field contains NaN or infinite values")
    if np.min(field) < 0:
        raise ValueError(f"{path}: v1 expects a non-negative density field")
    for axis_index, (_, descending) in enumerate(axes):
        if descending:
            field = np.flip(field, axis=axis_index).copy()
    x, y, z = (values[::-1].copy() if desc else values for values, desc in axes)
    return Frame(path, field, x, y, z, time)


def load_series(cfg: dict[str, Any]) -> list[Frame]:
    frames = [load_frame(path, cfg["input"].get("field_key", "field")) for path in resolve_inputs(cfg)]
    first = frames[0]
    for frame in frames[1:]:
        if frame.field.shape != first.field.shape or any(
            not np.allclose(getattr(frame, axis), getattr(first, axis), rtol=1e-7, atol=1e-12)
            for axis in ("x", "y", "z")
        ):
            raise ValueError(f"{frame.path}: all series frames must share shape and coordinates")
    if len(frames) > 1 and any(frame.time is None for frame in frames):
        raise ValueError("Every frame in a time series must contain scalar key 'time'")
    if len(frames) > 1 and any(frames[i].time >= frames[i + 1].time for i in range(len(frames) - 1)):
        raise ValueError("Time values must be strictly increasing in input order")
    return frames
