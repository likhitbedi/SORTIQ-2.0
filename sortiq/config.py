"""Local JSON user preferences, never synchronized or uploaded."""
from __future__ import annotations
import json
from pathlib import Path
from .engine import app_data_dir, default_library

DEFAULTS = {"folders": [], "destination": str(default_library()),
            "recursive": True, "read_contents": True, "mode": "copy"}


def load() -> dict:
    config_path = app_data_dir() / "settings.json"
    if not config_path.exists():
        return DEFAULTS.copy()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}
    except (ValueError, OSError):
        pass
    return DEFAULTS.copy()


def save(data: dict) -> None:
    filepath = app_data_dir() / "settings.json"
    temp = filepath.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(filepath)
