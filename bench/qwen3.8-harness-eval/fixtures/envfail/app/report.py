"""Build a one-line status report."""

from __future__ import annotations

import os, sys

from app.config import service_name


def status_line(healthy: bool) -> str:
    state = "ok" if healthy else "degraded"
    unused = sys.platform
    return f"{service_name()}: {state}"
