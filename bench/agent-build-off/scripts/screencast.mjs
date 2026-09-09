#!/usr/bin/env node
// Capture a CDP screencast from an already-running headless Chrome and write
// the frames plus an ffmpeg concat playlist that preserves the real capture
// cadence.
//
//   node screencast.mjs --port <devtools-port> --out <dir> \
//                       [--settle 2500] [--capture 9000] [--url-hint <substr>] \
//                       [--start <spec>] [--start-at 1000] [--play <script>]
//
// Headless Chrome cannot encode video, so we drive Page.startScreencast over
// the DevTools WebSocket instead. Frames arrive at whatever rate the compositor
// produces them (irregular, usually well under 60/s), each carrying
// metadata.timestamp in seconds. We write every frame as frame-NNNNN.jpg and
// emit concat.txt with per-frame durations taken from the real inter-frame
// deltas, so the later ffmpeg pass can resample that to true CFR 60.
//
// Every frame MUST be acknowledged with Page.screencastFrameAck or Chrome
// stops sending after a few frames.
//
// These games gate their world update on a running phase, so an unattended
// capture records one still title frame forever. --start sends the game's own
// start input --start-at ms into the kept footage, so the clip opens on the
// title and then shows the world moving. Two spec forms:
//
//   key:<Enter|Space|...>   Input.dispatchKeyEvent, a real keydown/keyup pair
//   click:<css selector>    Runtime.evaluate for the element's viewport-space
//                           centre, then Input.dispatchMouseEvent there
//
// A click spec waits (up to CLICK_WAIT_MS) for the selector to exist and have a
// non-zero box, so an arm whose start button only appears once its scene is
// ready is not clicked at empty space.
//
// --play is an optional "<ms>:<Key>,..." script of control presses, offsets
// measured from the start input. It is not there to score well — it is there so
// the clip shows the avatar answering the controls, not just the track sliding
// past. All four arms accept the same arrow/space vocabulary.
//
// No dependencies: Node 22+ has a global WebSocket and fetch.
import { mkdirSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";

function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`);
  return i === -1 ? fallback : process.argv[i + 1];
}

const port = Number(arg("port"));
const outDir = arg("out");
const settleMs = Number(arg("settle", 2500));
const captureMs = Number(arg("capture", 9000));
const urlHint = arg("url-hint", "");
const startSpec = arg("start", "");
const startAtMs = Number(arg("start-at", 1000));
const playScript = (arg("play", "") || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean)
  .map((s) => {
    const [at, key] = s.split(":");
    return { at: Number(at), key };
  })
  .sort((a, b) => a.at - b.at);

if (!port || !outDir) {
  console.error(
    "usage: screencast.mjs --port <n> --out <dir> [--settle ms] [--capture ms]" +
      " [--start key:Enter|click:<selector>] [--start-at ms]",
  );
  process.exit(2);
}
if (startSpec && !/^(key|click):/.test(startSpec)) {
  console.error(`screencast: --start must be key:<Key> or click:<selector>, got ${startSpec}`);
  process.exit(2);
}

const die = (msg) => {
  console.error(`screencast: ${msg}`);
  process.exit(1);
};

// Chrome may not have opened its debugging socket the instant it was spawned.
async function findTarget() {
  const deadline = Date.now() + 20000;
  let lastErr = "no /json/list response";
  while (Date.now() < deadline) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/json/list`);
      const targets = await res.json();
      const pages = targets.filter(
        (t) => t.type === "page" && t.webSocketDebuggerUrl && !t.url.startsWith("devtools://"),
      );
      const hit = urlHint ? pages.find((t) => t.url.includes(urlHint)) : pages[0];
      if (hit) return hit;
      lastErr = `no page target yet (${targets.length} targets)`;
    } catch (e) {
      lastErr = e.message;
    }
    await new Promise((r) => setTimeout(r, 250));
  }
  die(`could not find a page target on port ${port}: ${lastErr}`);
}

const target = await findTarget();
const ws = new WebSocket(target.webSocketDebuggerUrl);

let nextId = 1;
const pending = new Map();
function send(method, params = {}) {
  const id = nextId++;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((resolve, reject) => pending.set(id, { resolve, reject }));
}

rmSync(outDir, { recursive: true, force: true });
mkdirSync(outDir, { recursive: true });

const stamps = [];
let frameCount = 0;
let collecting = false;

ws.addEventListener("message", (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id !== undefined) {
    const p = pending.get(msg.id);
    if (!p) return;
    pending.delete(msg.id);
    msg.error ? p.reject(new Error(msg.error.message)) : p.resolve(msg.result);
    return;
  }
  if (msg.method !== "Page.screencastFrame") return;
  const { data, sessionId, metadata } = msg.params;
  // Ack first and unconditionally: a dropped ack stalls the whole stream.
  ws.send(JSON.stringify({
    id: nextId++,
    method: "Page.screencastFrameAck",
    params: { sessionId },
  }));
  if (!collecting) return;
  const name = `frame-${String(frameCount).padStart(5, "0")}.jpg`;
  writeFileSync(join(outDir, name), Buffer.from(data, "base64"));
  stamps.push({ name, t: metadata?.timestamp ?? Date.now() / 1000 });
  frameCount += 1;
});

// Chrome tears the socket down as we shut down, and undici surfaces that as an
// error event. Only treat it as fatal while we still need the connection.
let done = false;
ws.addEventListener("error", () => {
  if (!done) die("devtools websocket error");
});

await new Promise((resolve, reject) => {
  ws.addEventListener("open", resolve, { once: true });
  ws.addEventListener("close", () => reject(new Error("websocket closed early")), { once: true });
  setTimeout(() => reject(new Error("websocket connect timed out")), 15000);
}).catch((e) => die(e.message));

await send("Page.enable");
await send("Page.startScreencast", {
  format: "jpeg",
  quality: 90,
  maxWidth: 1280,
  maxHeight: 800,
  everyNthFrame: 1,
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Enough of a key descriptor that a `code`-matching listener (claude-opus5
// checks event.code) and a `key`-matching one (the opencode arms check
// event.key) both see what they expect.
const KEYS = {
  Enter: { key: "Enter", code: "Enter", keyCode: 13, text: "\r" },
  Space: { key: " ", code: "Space", keyCode: 32, text: " " },
  ArrowLeft: { key: "ArrowLeft", code: "ArrowLeft", keyCode: 37 },
  ArrowUp: { key: "ArrowUp", code: "ArrowUp", keyCode: 38 },
  ArrowRight: { key: "ArrowRight", code: "ArrowRight", keyCode: 39 },
  ArrowDown: { key: "ArrowDown", code: "ArrowDown", keyCode: 40 },
};

async function pressKey(name) {
  const k = KEYS[name];
  if (!k) die(`unknown key ${name} (known: ${Object.keys(KEYS).join(", ")})`);
  const base = {
    key: k.key,
    code: k.code,
    windowsVirtualKeyCode: k.keyCode,
    nativeVirtualKeyCode: k.keyCode,
  };
  await send("Input.dispatchKeyEvent", {
    type: k.text ? "keyDown" : "rawKeyDown",
    ...base,
    ...(k.text ? { text: k.text, unmodifiedText: k.text } : {}),
  });
  await sleep(40);
  await send("Input.dispatchKeyEvent", { type: "keyUp", ...base });
}

const CLICK_WAIT_MS = 4000;

async function clickSelector(selector) {
  const probe = `(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) return null;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return null;
    return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
  })()`;
  const deadline = Date.now() + CLICK_WAIT_MS;
  let box = null;
  while (Date.now() < deadline) {
    const res = await send("Runtime.evaluate", { expression: probe, returnByValue: true });
    box = res?.result?.value ?? null;
    if (box) break;
    await sleep(100);
  }
  if (!box) die(`start selector ${selector} never became clickable within ${CLICK_WAIT_MS}ms`);
  const at = { x: Math.round(box.x), y: Math.round(box.y), button: "left", clickCount: 1 };
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: at.x, y: at.y });
  await send("Input.dispatchMouseEvent", { type: "mousePressed", ...at });
  await sleep(40);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", ...at });
  return at;
}

async function sendStart() {
  const [kind, ...rest] = startSpec.split(":");
  const value = rest.join(":");
  // A background headless tab still delivers input, but focusing first matches
  // what a viewer would do and keeps window-level keydown listeners live.
  await send("Page.bringToFront").catch(() => {});
  if (kind === "key") {
    await pressKey(value);
    console.log(`start: key ${value}`);
  } else {
    const at = await clickSelector(value);
    console.log(`start: click ${value} at ${at.x},${at.y}`);
  }
}

// Let the scene warm up (shaders compile, intro fades finish) before the first
// frame we keep, then capture longer than the target clip so we can trim.
await sleep(settleMs);
collecting = true;
if (startSpec) {
  // Hold the title for a beat of kept footage, start the game, then let the
  // rest of the capture be gameplay.
  await sleep(Math.min(startAtMs, captureMs));
  await sendStart();
  let cursor = 0; // ms since the start input
  let pressed = 0;
  for (const step of playScript) {
    if (startAtMs + step.at >= captureMs) break;
    await sleep(Math.max(0, step.at - cursor));
    cursor = step.at;
    await pressKey(step.key);
    pressed += 1;
  }
  if (pressed) console.log(`play: ${pressed} presses through +${cursor}ms`);
  await sleep(Math.max(0, captureMs - startAtMs - cursor));
} else {
  await sleep(captureMs);
}
collecting = false;

if (stamps.length < 30) die(`only ${stamps.length} frames captured — screencast did not run`);

await send("Page.stopScreencast").catch(() => {});
done = true;
ws.close();

// Real inter-frame deltas become concat durations; ffmpeg resamples to CFR.
const deltas = [];
for (let i = 0; i < stamps.length - 1; i += 1) {
  const d = stamps[i + 1].t - stamps[i].t;
  deltas.push(d > 0 && d < 1 ? d : 1 / 60);
}
const median = [...deltas].sort((a, b) => a - b)[Math.floor(deltas.length / 2)] || 1 / 60;
deltas.push(median);

const lines = stamps.map((s, i) => `file '${s.name}'\nduration ${deltas[i].toFixed(6)}`);
// The concat demuxer needs the final entry repeated for its duration to stick.
lines.push(`file '${stamps.at(-1).name}'`);
writeFileSync(join(outDir, "concat.txt"), `${lines.join("\n")}\n`);

const span = stamps.at(-1).t - stamps[0].t;
console.log(
  `frames=${stamps.length} span=${span.toFixed(2)}s effective_fps=${(stamps.length / span).toFixed(1)}`,
);
// Don't wait on a lingering socket handle keeping the event loop alive.
process.exit(0);
