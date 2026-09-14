"""Configuration loading and object graph construction.

A config is a nested mapping.  Top-level keys name components; each value is
either a registry name or a mapping with a ``type`` key.  Absent keys mean
"no such component" and the corresponding null implementation is used.

Example (TOML)::

    [recommender]
    profile = "history"
    memory  = { type = "window", size = 20 }
    planner = { type = "react", max_steps = 6 }
    tools   = ["history", "retrieve", "rank"]
    reflector = "self_critique"
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tomllib

from .registry import registry


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix == ".toml":
        return tomllib.loads(text)
    if p.suffix == ".json":
        return json.loads(text)
    if p.suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise ImportError("pip install pyyaml to load YAML configs") from e
        return yaml.safe_load(text)
    raise ValueError(f"unsupported config format: {p.suffix}")


def build(kind: str, spec: Any, **shared: Any) -> Any:
    """Build one component (or a list of them) from ``spec``.

    ``shared`` objects (``llm``, ``catalog`` ...) are forwarded to any
    constructor that declares a parameter with the same name.
    """
    if isinstance(spec, list):
        return [registry.create(kind, s, **shared) for s in spec]
    return registry.create(kind, spec, **shared)
