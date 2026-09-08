"""Load service configuration from a YAML file."""

from __future__ import annotations

import os
from pathlib import Path

import yaml


def load_config(path: str | os.PathLike[str]) -> dict:
    """Return the parsed YAML document at ``path`` as a dict."""
    with Path(path).open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError("config root must be a mapping")
    return data


def service_name() -> str:
    """Name of this service, taken from the SERVICE_NAME environment variable."""
    return os.environ["SERVICE_NAME"]
