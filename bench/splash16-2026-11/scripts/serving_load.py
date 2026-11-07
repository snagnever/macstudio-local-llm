#!/usr/bin/env python3
"""Load generator of the splash16-2026-11 campaign: the #644 aging load, a churn load and a short decode probe.

aging  rounds of N new concurrent sessions with long distinct prompts; a short probe before, after each round,
       at the end and after an idle wait. It fills the KV pool with prefixes of finished sessions.
churn  clients with growing conversations for a fixed time (scenario of docs/validate.md of Splash 1.6.0).
probe  a 64-token prompt, repeated.

Every record is one JSON line in --out: kind "request", "probe", "status" or "calibration". Python 3.9 stdlib.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import statistics
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "longctx_probe", REPO / "bench/splash-longctx-2026-10/scripts/longctx_probe.py")
longctx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(longctx)

PROBE_PROMPT = ("In three short sentences, explain why a write-ahead log helps a database recover after a crash. "
                "Then name one cost of keeping that log and one way to reduce the cost. Label: ")
ASK = "\n\nQuestion: how many distinct regions appear in the log above? Answer in one short paragraph."
SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 20, "frequency_penalty": 0, "reasoning_effort": "xhigh"}


def _hay(tokens: int, seed: int, chars_per_token: float) -> str:
    context = int(tokens) + longctx.OUTPUT_ROOM + 512
    text, _ = longctx.build_case(context, seed=seed, fill=1.0, chars_per_token=chars_per_token)
    return f"Log capture {seed}.\n" + text


def build_aging_prompts(rounds: int, sessions: int, prompt_tokens: int, seed: int,
                        chars_per_token: float) -> list[list[str]]:
    """One list of distinct prompts per round. No prompt shares a useful prefix with another."""
    out, n = [], 0
    for _ in range(rounds):
        row = []
        for _ in range(sessions):
            row.append(_hay(prompt_tokens, seed * 1000 + n, chars_per_token) + ASK)
            n += 1
        out.append(row)
    return out


class Conversation:
    """A churn client's messages. Each fourth round resends the conversation unchanged."""

    def __init__(self, first_text: str, step_text):
        self.messages = [{"role": "user", "content": first_text}]
        self.step_text = step_text

    def advance(self, round_no: int, reply: str) -> None:
        if (round_no + 1) % 4 == 0:
            return
        self.messages.append({"role": "assistant", "content": reply or "ok"})
        self.messages.append({"role": "user", "content": self.step_text(round_no)})


def decode_tok_s(completion_tokens, times: list[float]):
    """Tokens per second between the first and the last chunk. A chunk can hold more than one token (DFlash)."""
    if not completion_tokens or len(times) < 2 or times[-1] <= times[0]:
        return None
    return completion_tokens / (times[-1] - times[0])


def status_record(status: dict, t: float) -> dict:
    return {"kind": "status", "t": round(t, 1), "schema_version": status.get("schema_version"),
            "kv": status.get("kv"), "state": status.get("state"), "disk": status.get("disk"),
            "memory_governor": status.get("memory_governor"), "metrics": status.get("metrics")}


def _cached(usage: dict):
    details = usage.get("prompt_tokens_details") or {}
    return details.get("cached_tokens", usage.get("cached_tokens"))


def stream_chat(base_url: str, model: str, messages: list[dict], max_tokens: int, timeout: float) -> dict:
    """One streamed request. A failure is a return value: it never raises."""
    body = dict(SAMPLING, model=model, messages=messages, max_tokens=max_tokens, stream=True,
                stream_options={"include_usage": True})
    req = urllib.request.Request(base_url + "/chat/completions", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    t0 = time.time()
    times, usage, reply, status, error = [], {}, [], None, None
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            done = False
            for raw in resp:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    done = True
                    break
                obj = json.loads(data)
                if obj.get("error"):
                    error = json.dumps(obj["error"])[:500]
                usage = obj.get("usage") or usage
                for choice in obj.get("choices") or []:
                    delta = choice.get("delta") or {}
                    text = delta.get("content") or ""
                    if text or delta.get("reasoning_content") or delta.get("reasoning") or delta.get("tool_calls"):
                        times.append(time.time())
                    reply.append(text)
            if not done and not error:
                error = "stream closed before [DONE]"
    except urllib.error.HTTPError as exc:
        status = exc.code
        error = exc.read().decode("utf-8", "replace")[:500]
    except Exception as exc:  # noqa: BLE001 - a dead connection is a measurement, not a crash of the run
        error = f"{type(exc).__name__}: {exc}"[:500]
    gaps = [round(b - a, 3) for a, b in zip(times, times[1:])]
    return {"prompt_tokens": usage.get("prompt_tokens"), "cached_tokens": _cached(usage),
            "completion_tokens": usage.get("completion_tokens"),
            "ttft_s": round(times[0] - t0, 3) if times else None,
            "decode_tok_s": decode_tok_s(usage.get("completion_tokens"), times),
            "max_gap_s": max(gaps) if gaps else None, "gaps_s": gaps, "status": status, "error": error,
            "wall_s": round(time.time() - t0, 3), "reply": "".join(reply)}


class Writer:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = path.open("a", encoding="utf-8")
        self.lock = threading.Lock()

    def write(self, rec: dict) -> None:
        with self.lock:
            self.fh.write(json.dumps(rec) + "\n")
            self.fh.flush()


class StatusSampler(threading.Thread):
    def __init__(self, url: str, writer: Writer, interval: float):
        super().__init__(daemon=True)
        self.url, self.writer, self.interval = url, writer, interval
        self.t0 = time.time()
        self.halt = threading.Event()

    def sample(self) -> None:
        try:
            with urllib.request.urlopen(self.url, timeout=10) as resp:
                self.writer.write(status_record(json.load(resp), time.time() - self.t0))
        except Exception:  # noqa: BLE001 - /status can stall during a restart; the next sample tells
            pass

    def run(self) -> None:
        while not self.halt.wait(self.interval):
            self.sample()


def run_probe(args, writer: Writer, label: str, reps: int) -> None:
    for i in range(reps):
        rec = stream_chat(args.base_url, args.model, [{"role": "user", "content": PROBE_PROMPT + f"{label}-{i}."}],
                          512, args.timeout)
        rec.pop("reply")
        writer.write(dict(rec, kind="probe", label=label, rep=i))


def _measure_chars_per_token(args, writer: Writer) -> float:
    """Characters per token of the haystack on this server, from /v1/messages/count_tokens."""
    sample = _hay(16000, 99, 4.0)
    body = {"model": args.model, "max_tokens": 1, "messages": [{"role": "user", "content": sample}]}
    req = urllib.request.Request(args.base_url + "/messages/count_tokens", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            n = int(json.load(resp)["input_tokens"])
    except Exception as exc:  # noqa: BLE001 - fall back to the estimate of longctx_probe and say so
        writer.write({"kind": "calibration", "chars_per_token": longctx.CHARS_PER_TOKEN, "error": str(exc)[:300]})
        return longctx.CHARS_PER_TOKEN
    ratio = len(sample) / max(n, 1)
    writer.write({"kind": "calibration", "chars_per_token": round(ratio, 4), "sample_tokens": n})
    return ratio


def _one(args, writer, prompt, round_no, session, max_tokens):
    rec = stream_chat(args.base_url, args.model, [{"role": "user", "content": prompt}], max_tokens, args.timeout)
    rec.pop("reply")
    writer.write(dict(rec, kind="request", round=round_no, session=session))


def cmd_aging(args, writer: Writer) -> int:
    cpt = _measure_chars_per_token(args, writer)
    prompts = build_aging_prompts(args.rounds, args.sessions, args.prompt_tokens, args.seed, cpt)
    warm = stream_chat(args.base_url, args.model, [{"role": "user", "content": "Say ok."}], 16, args.timeout)
    writer.write({"kind": "calibration", "warm_up_status": warm["status"]})
    run_probe(args, writer, "pre", args.probe_reps)
    for r, row in enumerate(prompts, 1):
        threads = [threading.Thread(target=_one, args=(args, writer, p, r, s, args.max_tokens)) for s, p in enumerate(row)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        run_probe(args, writer, f"round{r}", args.probe_reps)
    run_probe(args, writer, "fim", args.probe_reps)
    time.sleep(args.idle_minutes * 60)
    run_probe(args, writer, "ocioso", args.probe_reps)
    return 0


def _churn_client(args, writer, client: int, start_delay: float, deadline: float, cpt: float) -> None:
    time.sleep(start_delay)
    rng_seed = args.seed * 1000 + client
    conv = Conversation(_hay(args.base_tokens, rng_seed, cpt) + ASK,
                        lambda n: _hay(args.step_tokens, rng_seed + 100 * n, cpt) + ASK)
    round_no = 0
    while time.time() < deadline:
        round_no += 1
        rec = stream_chat(args.base_url, args.model, conv.messages, args.max_tokens, args.timeout)
        reply = rec.pop("reply")
        writer.write(dict(rec, kind="request", round=round_no, session=client))
        if rec["error"] or rec["status"] != 200:
            return
        conv.advance(round_no, reply)


def cmd_churn(args, writer: Writer) -> int:
    cpt = _measure_chars_per_token(args, writer)
    order = [int(x) for x in args.order.split(",")]
    deadline = time.time() + args.minutes * 60
    threads = [threading.Thread(target=_churn_client, args=(args, writer, c, i * 0.6, deadline, cpt))
               for i, c in enumerate(order[:args.clients])]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return 0


def cmd_probe(args, writer: Writer) -> int:
    run_probe(args, writer, args.label, args.reps)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, interval in (("aging", 30.0), ("churn", 5.0), ("probe", 0.0)):
        p = sub.add_parser(name)
        p.add_argument("--base-url", required=True, help="ends in /v1")
        p.add_argument("--model", required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--timeout", type=float, default=3600)
        p.add_argument("--seed", type=int, default=0)
        p.add_argument("--status-url", default="")
        p.add_argument("--status-interval", type=float, default=interval)
    a = sub.choices["aging"]
    a.add_argument("--rounds", type=int, default=6)
    a.add_argument("--sessions", type=int, default=3)
    a.add_argument("--prompt-tokens", type=int, default=190960)
    a.add_argument("--max-tokens", type=int, default=300)
    a.add_argument("--idle-minutes", type=float, default=10)
    a.add_argument("--probe-reps", type=int, default=3)
    c = sub.choices["churn"]
    c.add_argument("--minutes", type=float, default=15)
    c.add_argument("--clients", type=int, default=3)
    c.add_argument("--base-tokens", type=int, default=16000)
    c.add_argument("--step-tokens", type=int, default=2000)
    c.add_argument("--max-tokens", type=int, default=1500)
    c.add_argument("--order", default="2,0,1")
    q = sub.choices["probe"]
    q.add_argument("--label", required=True)
    q.add_argument("--reps", type=int, default=3)
    args = ap.parse_args(argv)
    args.base_url = args.base_url.rstrip("/")
    writer = Writer(args.out)
    sampler = None
    if args.status_url and args.status_interval > 0:
        sampler = StatusSampler(args.status_url, writer, args.status_interval)
        sampler.sample()
        sampler.start()
    try:
        return {"aging": cmd_aging, "churn": cmd_churn, "probe": cmd_probe}[args.cmd](args, writer)
    finally:
        if sampler:
            sampler.halt.set()
            sampler.sample()


if __name__ == "__main__":
    raise SystemExit(main())
