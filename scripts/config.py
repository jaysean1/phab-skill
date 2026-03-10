# Configuration loader for the tickets skill.
# Not for direct execution — import this module from other scripts.

from pathlib import Path
from typing import Any

import yaml

_SCRIPT_DIR = Path(__file__).resolve().parent
_CONFIG_PATH = _SCRIPT_DIR / "config.yaml"
_cache: dict[str, Any] | None = None


def _load() -> dict[str, Any]:
    """Load and cache config.yaml. Prints an error if the file is missing."""
    global _cache
    if _cache is not None:
        return _cache

    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found: {_CONFIG_PATH}\n"
            "Run 'uv run setup.py' to create one from the example template."
        )

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        _cache = yaml.safe_load(f) or {}
    return _cache


def get(key: str, default: Any = None) -> Any:
    """Get a config value by key, with an optional default."""
    return _load().get(key, default)
