from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULTS: dict[str, Any] = {
    "input": {"field_key": "field"},
    "output": {"directory": "build", "archive": True},
    "mapping": {
        "mode": "linear",
        "range": "global",
        "minimum": None,
        "maximum": None,
        "percentiles": None,
        "log_floor": None,
        "colormap": "viridis",
        "symmetric": False,
        "transparent_value": 0.0,
    },
    "volume": {"density_scale": 4.0, "cutoff": 0.001},
    "shells": {
        "enabled": True,
        "isovalue": 0.25,
        "positive_color": [0.9941176471, 0.0, 0.0, 1.0],
        "negative_color": [0.0039215686, 0.0039215686, 1.0, 1.0],
        "roughness": 0.28,
        "coat_weight": 0.15,
        "volume_density_multiplier": 0.5,
    },
    "geometry": {"aspect_mode": "preserve_physical_aspect", "box_size": 4.0},
    "slices": [],
    "labels": {"x": "x", "y": "y", "z": "z", "field": "density", "time": "t", "title": ""},
    "scene": {
        "resolution": [1280, 960],
        "samples": 128,
        "preview_samples": 8,
        "camera": [7.0, -8.0, 6.0],
        "lens_mm": 52.0,
        "background": [1.0, 1.0, 1.0, 1.0],
        "background_strength": 1.0,
        "wire_color": [0.0, 0.0, 0.0, 1.0],
        "annotation_color": [0.0, 0.0, 0.0, 1.0],
    },
}


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(path: str | Path) -> tuple[dict[str, Any], Path]:
    config_path = Path(path).expanduser().resolve()
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be a YAML mapping")
    cfg = _merge(DEFAULTS, raw)
    cfg["_config_path"] = str(config_path)
    cfg["_base_dir"] = str(config_path.parent)
    return cfg, config_path


def resolve_path(value: str, base: Path) -> Path:
    path = Path(value).expanduser()
    return (base / path).resolve() if not path.is_absolute() else path.resolve()
