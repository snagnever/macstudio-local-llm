import os
import subprocess
from pathlib import Path

import pytest

jinja2 = pytest.importorskip("jinja2")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
OFFICIAL = HERE / "fixtures" / "swift15-chat_template.jinja"
EFFTAIL = REPO / "fixes" / "qwen3.8-flash-next" / "swift15-effort-tail.jinja"
OVERLAY = HERE.parent / "scripts" / "make-overlay.sh"

TOOLS = [{"type": "function", "function": {"name": "ls", "description": "list files",
                                           "parameters": {"type": "object", "properties": {}}}}]
MESSAGES = [{"role": "system", "content": "You are an audit assistant."},
            {"role": "user", "content": "Which file holds the parser?"}]
XHIGH = "Reasoning effort is set to xhigh."
LOW = "Reasoning effort is set to low."


def _raise(msg):
    raise ValueError(msg)


def render(path: Path, effort: str, tools=None) -> str:
    env = jinja2.Environment(trim_blocks=True, lstrip_blocks=True)
    env.globals["raise_exception"] = _raise
    return env.from_string(path.read_text()).render(messages=MESSAGES, tools=tools, reasoning_effort=effort,
                                                     add_generation_prompt=True)


@pytest.mark.parametrize("tools", [None, TOOLS])
def test_medium_render_is_identical(tools):
    assert render(EFFTAIL, "medium", tools) == render(OFFICIAL, "medium", tools)


@pytest.mark.parametrize("tools", [None, TOOLS])
@pytest.mark.parametrize("effort,head", [("xhigh", XHIGH), ("low", LOW)])
def test_effort_block_is_the_last_block(tools, effort, head):
    out = render(EFFTAIL, effort, tools)
    tail_start = out.rindex("<|im_start|>system\n")
    assert out[tail_start:].startswith("<|im_start|>system\n" + head)
    assert out.endswith("<|im_end|>\n<|im_start|>assistant\n<think>\n")
    assert head not in out[:tail_start]
    assert head in render(OFFICIAL, effort, tools).split("<|im_start|>user")[0]


@pytest.mark.parametrize("tools", [None, TOOLS])
def test_prefix_does_not_depend_on_effort(tools):
    medium = render(EFFTAIL, "medium", tools)
    prefix = medium[: medium.rindex("<|im_start|>assistant\n")]
    for effort in ("xhigh", "low"):
        assert render(EFFTAIL, effort, tools).startswith(prefix)


def _make_src(tmp_path: Path, tokenizer_config: str = '{"eos_token": "<|im_end|>"}') -> Path:
    src = tmp_path / "src"
    src.mkdir()
    (src / "model-00001.safetensors").write_bytes(b"weights")
    (src / "config.json").write_text("{}")
    (src / "tokenizer_config.json").write_text(tokenizer_config)
    (src / "chat_template.jinja").write_text("official")
    return src


def test_overlay_does_not_touch_the_source_template(tmp_path):
    src = _make_src(tmp_path)
    dst = tmp_path / "dst"
    tpl = tmp_path / "new.jinja"
    tpl.write_text("efftail")
    subprocess.run(["bash", str(OVERLAY), str(src), str(dst), str(tpl)], check=True, capture_output=True)
    assert os.stat(dst / "model-00001.safetensors").st_ino == os.stat(src / "model-00001.safetensors").st_ino
    assert os.stat(dst / "chat_template.jinja").st_ino != os.stat(src / "chat_template.jinja").st_ino
    assert (dst / "chat_template.jinja").read_text() == "efftail"
    assert (src / "chat_template.jinja").read_text() == "official"
    assert "src" in (dst / "OVERLAY.txt").read_text()
    # A second run with the same template is a no-op.
    subprocess.run(["bash", str(OVERLAY), str(src), str(dst), str(tpl)], check=True, capture_output=True)


def test_overlay_refuses_tokenizer_chat_template(tmp_path):
    src = _make_src(tmp_path, '{"chat_template": "x"}')
    tpl = tmp_path / "new.jinja"
    tpl.write_text("efftail")
    r = subprocess.run(["bash", str(OVERLAY), str(src), str(tmp_path / "dst"), str(tpl)], capture_output=True)
    assert r.returncode == 65
