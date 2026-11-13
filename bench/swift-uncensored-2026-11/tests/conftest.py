import importlib.util
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
SCRIPTS = HERE / "scripts"
FIXTURES = HERE / "tests" / "fixtures"


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "PARALLEL_", "SPLASH_", "QUEUE_",
                                "http_", "HTTP_"))}
    env.update(extra or {})
    return env


def run_arm(arm, ctx="32768", extra_env=None, args=()):
    return subprocess.run(["bash", str(SCRIPTS / "run-arm.sh"), arm, ctx, *args, "--print"], capture_output=True,
                          text=True, env=clean_env(extra_env))


def show_arm(arm, ctx="32768", extra_env=None, args=()):
    r = run_arm(arm, ctx, extra_env, args)
    assert r.returncode == 0, r.stderr
    return r.stdout


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeChat(BaseHTTPRequestHandler):
    """A non-streaming Chat Completions server. The answer depends on a word in the user prompt:
    "refuse" -> a refusal, "blank" -> empty content with reasoning, "boom" -> HTTP 500, else a compliant answer."""
    bodies = []

    def log_message(self, *args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        type(self).bodies.append(body)
        prompt = body["messages"][-1]["content"]
        if "boom" in prompt:
            code, obj = 500, {"error": {"message": "boom"}}
        else:
            if "refuse" in prompt:
                msg = {"content": "I can’t help with that.", "reasoning_content": "no"}
            elif "blank" in prompt:
                msg = {"content": "", "reasoning_content": "thinking " * 50}
            else:
                msg = {"content": "Sure. Step 1: do the thing.", "reasoning_content": "ok"}
            code, obj = 200, {"choices": [{"message": dict(msg, role="assistant"), "finish_reason": "stop"}]}
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@pytest.fixture
def fake_server():
    cls = type("Fake", (FakeChat,), {"bodies": []})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1", cls
    srv.shutdown()
