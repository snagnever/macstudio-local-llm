from pathlib import Path

from app.config import load_config


def test_load_config(tmp_path: Path):
    cfg = tmp_path / "svc.yaml"
    cfg.write_text("name: demo\nport: 8080\n", encoding="utf-8")
    assert load_config(cfg) == {"name": "demo", "port": 8080}
