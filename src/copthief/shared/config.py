"""Configuration manager: loads versioned config from files and environment.

All tunable parameters are read here so nothing is hardcoded in business logic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

from copthief.constants import DEFAULT_CONFIG_PATH, RATE_LIMITS_PATH
from copthief.shared.version import assert_config_version


def _project_root() -> Path:
    """Resolve the project root from env override or the package location."""
    override = os.environ.get("COPTHIEF_ROOT")
    if override:
        return Path(override)
    return Path(__file__).resolve().parents[3]


class Config:
    """Read-only access to merged YAML config with dotted-key lookups."""

    def __init__(self, data: dict[str, Any], root: Path):
        self._data = data
        self.root = root

    @classmethod
    def load(cls, path: str | None = None) -> Config:
        """Load config.yaml, validate its version, and return a Config."""
        root = _project_root()
        cfg_path = root / (path or DEFAULT_CONFIG_PATH)
        with cfg_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        assert_config_version(data.get("version", "0.0"))
        return cls(data, root)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Fetch a value by dotted path, e.g. 'game.grid_size'."""
        node: Any = self._data
        for part in dotted_key.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def section(self, key: str) -> dict[str, Any]:
        """Return a whole top-level section as a dict (empty if missing)."""
        value = self._data.get(key, {})
        return dict(value) if isinstance(value, dict) else {}

    def rate_limits(self) -> dict[str, Any]:
        """Load the separate, versioned rate-limit configuration file."""
        with (self.root / RATE_LIMITS_PATH).open(encoding="utf-8") as handle:
            return json.load(handle)
