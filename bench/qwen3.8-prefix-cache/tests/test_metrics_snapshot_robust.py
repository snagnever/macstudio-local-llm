import sys
import urllib.error
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cache_probe
from cache_probe import _metrics_snapshot


def test_connection_reset_returns_empty(monkeypatch):
    def _raise(*args, **kwargs):
        raise ConnectionResetError(54, "reset")

    monkeypatch.setattr(cache_probe, "urlopen", _raise)

    assert _metrics_snapshot("http://x/metrics", "mlx-serve") == {}


def test_url_error_returns_empty(monkeypatch):
    def _raise(*args, **kwargs):
        raise urllib.error.URLError("boom")

    monkeypatch.setattr(cache_probe, "urlopen", _raise)

    assert _metrics_snapshot("http://x/metrics", "mlx-serve") == {}


def test_none_url_returns_empty():
    assert _metrics_snapshot(None, "mlx-serve") == {}
