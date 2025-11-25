# src/fednestd/config/loaders.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import json

try:
    import yaml  # type: ignore
except ImportError:  # optional dependency
    yaml = None


def load_config(path: Path | str) -> Dict[str, Any]:
    """
    Load a YAML or JSON config file and return it as a plain dict.

    Later you can validate this against pydantic models in config/models.py.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")

    text = p.read_text()

    # YAML first (if available), fallback to JSON.
    if yaml is not None and p.suffix in {".yml", ".yaml"}:
        return yaml.safe_load(text) or {}

    # JSON
    if p.suffix == ".json":
        return json.loads(text)

    # If we reach here, try YAML then JSON as a last resort.
    if yaml is not None:
        try:
            return yaml.safe_load(text) or {}
        except Exception:
            pass

    try:
        return json.loads(text)
    except Exception as e:
        raise ValueError(f"Unsupported config format for {p}: {e}") from e