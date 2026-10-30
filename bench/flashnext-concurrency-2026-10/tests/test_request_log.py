import json
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import request_log as RL

EVENTS = [("message_start", {"type": "message_start",
                             "message": {"usage": {"input_tokens": 3265, "cache_read_input_tokens": 16032}}}),
          ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking"}}),
          ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                   "delta": {"type": "thinking_delta", "thinking": "x"}}),
          ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "y"}}),
          ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 110}}),
          ("message_stop", {"type": "message_stop"})]


def test_parse_sse_ttft_is_first_content_delta_not_message_start():
    times = [100.1, 100.2, 123.7, 123.8, 125.0, 125.0]
    rec = RL.parse_sse(EVENTS, t_start=100.0, times=times, t0=90.0, stream="c", status=200)
    assert rec["t_start_s"] == 10.0 and rec["ttft_s"] == 23.7 and rec["t_end_s"] == 35.0
    assert rec["input_tokens"] == 19297 and rec["cached_tokens"] == 16032 and rec["output_tokens"] == 110
    assert abs(rec["tps"] - 110 / (125.0 - 123.7)) < 0.1 and rec["status"] == 200 and rec["stream"] == "c"


def test_parse_sse_input_tokens_is_the_whole_prompt_like_the_splash_log():
    # The API's usage.input_tokens excludes the cached part; the schema (claude_requests.py) wants the total.
    ev = [("message_start", {"type": "message_start", "message": {"usage": {
        "input_tokens": 359, "cache_read_input_tokens": 19264, "cache_creation_input_tokens": 100}}})] + EVENTS[1:]
    rec = RL.parse_sse(ev, 0.0, [0.0, 0.1, 1.0, 1.1, 2.0, 2.0], t0=0.0, stream="c", status=200)
    assert rec["input_tokens"] == 19723 and rec["cached_tokens"] == 19264


def test_parse_sse_without_cache_field_writes_null_cached():
    ev = [("message_start", {"type": "message_start", "message": {"usage": {"input_tokens": 500}}})] + EVENTS[1:]
    rec = RL.parse_sse(ev, 0.0, [0.0, 0.1, 1.0, 1.1, 2.0, 2.0], t0=0.0, stream="c", status=200)
    assert rec["cached_tokens"] is None and rec["input_tokens"] == 500


def test_parse_sse_without_content_delta_has_null_ttft():
    ev = [EVENTS[0], EVENTS[4], EVENTS[5]]
    rec = RL.parse_sse(ev, 0.0, [0.0, 1.0, 1.0], t0=0.0, stream="c", status=529)
    assert rec["ttft_s"] is None and rec["tps"] is None and rec["status"] == 529 and rec["output_tokens"] == 110


class FakeUpstream(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for name, data in EVENTS:  # one event every 0.1 s: the first content delta is the third, at ~0.2 s
            self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode())
            self.wfile.flush()
            time.sleep(0.1)

    def log_message(self, *a):
        pass


def test_proxy_forwards_stream_and_writes_one_record(tmp_path):
    up = ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    out = tmp_path / "req.jsonl"
    px = RL.make_server("127.0.0.1", 0, f"http://127.0.0.1:{up.server_port}", out, stream="d", t0=time.time())
    threading.Thread(target=px.serve_forever, daemon=True).start()
    req = urllib.request.Request(f"http://127.0.0.1:{px.server_port}/v1/messages", data=b'{"stream":true}',
                                 headers={"Content-Type": "application/json", "anthropic-version": "2023-06-01"})
    body = urllib.request.urlopen(req).read().decode()
    assert "event: message_stop" in body  # the client gets the whole stream, unchanged
    px.shutdown()
    up.shutdown()
    recs = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(recs) == 1 and recs[0]["stream"] == "d" and recs[0]["input_tokens"] == 19297
    assert recs[0]["status"] == 200 and recs[0]["cached_tokens"] == 16032
    # The proxy must pass events on as they arrive, not after a buffer fills: TTFT is the third event's time.
    assert 0.15 < recs[0]["ttft_s"] < 0.35 and recs[0]["t_end_s"] - recs[0]["t_start_s"] > 0.5


def test_parse_sse_ttft_counts_a_tool_use_json_delta_as_the_first_token():
    # A turn that is only a tool call has no text/thinking delta; the model still started generating.
    ev = [EVENTS[0], ("content_block_start", {"type": "content_block_start", "index": 0,
                                               "content_block": {"type": "tool_use", "name": "Read"}}),
          ("content_block_delta", {"type": "content_block_delta", "index": 0,
                                   "delta": {"type": "input_json_delta", "partial_json": "{"}}),
          EVENTS[4], EVENTS[5]]
    rec = RL.parse_sse(ev, 0.0, [0.1, 0.2, 2.5, 4.0, 4.0], t0=0.0, stream="c", status=200)
    assert rec["ttft_s"] == 2.5 and abs(rec["tps"] - 110 / 1.5) < 0.1


def test_proxy_raw_dir_keeps_the_whole_response(tmp_path):
    up = ThreadingHTTPServer(("127.0.0.1", 0), FakeUpstream)
    threading.Thread(target=up.serve_forever, daemon=True).start()
    raw = tmp_path / "raw"
    px = RL.make_server("127.0.0.1", 0, f"http://127.0.0.1:{up.server_port}", tmp_path / "req.jsonl", stream="d",
                        t0=time.time(), raw_dir=raw)
    threading.Thread(target=px.serve_forever, daemon=True).start()
    req = urllib.request.Request(f"http://127.0.0.1:{px.server_port}/v1/messages", data=b'{"stream":true}',
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req).read()
    px.shutdown()
    up.shutdown()
    files = sorted(raw.glob("d-*.sse"))
    assert len(files) == 1 and "event: message_stop" in files[0].read_text() and "input_tokens" in files[0].read_text()
