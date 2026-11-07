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


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("QWEN38_", "FLASHNEXT_", "MLX_SERVE_", "OMLX_", "PARALLEL_", "SPLASH_", "http_", "HTTP_"))}
    env.update(extra or {})
    return env


def show_arm(arm, ctx="32768", extra_env=None, args=()):
    return subprocess.run(["bash", str(SCRIPTS / "run-arm.sh"), arm, ctx, *args, "--print"], capture_output=True,
                          text=True, env=clean_env(extra_env), check=True).stdout


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class FakeChat(BaseHTTPRequestHandler):
    """A streaming Chat Completions server. `fail_on` holds 1-based request numbers answered with HTTP 500."""
    fail_on = ()
    count = 0
    lock = threading.Lock()
    bodies = []

    def log_message(self, *args):
        pass

    def _json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._json(200, {"schema_version": 8, "kv": {"pages_cache": 1}, "state": {}, "disk": {},
                         "memory_governor": {"denied_reservations": 0}, "metrics": {}})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        if self.path.endswith("count_tokens"):
            self._json(200, {"input_tokens": len(json.dumps(body.get("messages", ""))) // 4})
            return
        cls = type(self)
        with cls.lock:
            cls.count += 1
            n = cls.count
            cls.bodies.append(body)
        if n in cls.fail_on:
            self._json(500, {"error": {"message": "boom", "code": "engine_failed"}})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for piece in ("a", "b", "c"):
            chunk = {"choices": [{"delta": {"content": piece}}]}
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.flush()
        usage = {"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 3,
                                          "prompt_tokens_details": {"cached_tokens": 10}}}
        self.wfile.write(f"data: {json.dumps(usage)}\n\ndata: [DONE]\n\n".encode())


@pytest.fixture
def fake_server():
    def start(fail_on=()):
        cls = type("Fake", (FakeChat,), {"fail_on": fail_on, "count": 0, "bodies": [], "lock": threading.Lock()})
        srv = ThreadingHTTPServer(("127.0.0.1", 0), cls)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        started.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}", cls
    started = []
    yield start
    for srv in started:
        srv.shutdown()
