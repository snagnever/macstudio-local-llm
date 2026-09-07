# Design — Agent comparison benchmarks on GitHub Pages

_Dated 2026-09-07._

Three model-and-harness comparisons become a published site: the existing
SVGBench scoring, a new **Agent Build-Off**, and a new **Layout Skill Bench**.
Visitors read the numbers and then run each artifact live.

The site is in English. The repository keeps its existing conventions.

## 1. What each benchmark compares

| Benchmark | Question | Arms |
| --- | --- | --- |
| SVGBench | Can a local model draw as well as a frontier model? | 5 harness×model pairs, already scored |
| Agent Build-Off | Same brief, one session, from an empty folder — what does each agent stack deliver? | 4 built |
| Layout Skill Bench | One model, one brief, three design skills — does the skill change the result? | 3 skills × 5 pages |

SVGBench already lives in `bench/harness-matrix/` and already renders through
`reports/harness-matrix-svgbench.html`. This design adds the two new campaigns
and publishes all three.

### Agent Build-Off arms

Naming follows the `<harness>/<model>` convention in
`bench/harness-matrix/plan.md`.

| Arm | Source folder | Harness | Model | Variable |
| --- | --- | --- | --- | --- |
| `opencode-qwen38` | `~/LocalProjects/hyper-runner` | opencode | `qwen3.8-flash-next` (MLX, local) | local baseline |
| `opencode-qwen38-superpowers` | `~/LocalProjects/hyper-runner-superpowers` | opencode | `qwen3.8-flash-next` (MLX, local) | + superpowers skills |
| `claude-opus5` | `~/LocalProjects/hyper-runner-claude` | claude | `claude-opus-5` | hosted frontier |
| `codex-astra` | `~/LocalProjects/hyper-runner-astra` | codex | `gpt-6-astra` | hosted frontier |

`~/LocalProjects/hyper-runner-fable` is empty. That arm never ran, so the site
omits it rather than showing a blank column.

Three arms record the same verbatim brief in their `STATS.md`. Arm
`codex-astra` has no `STATS.md`; its brief is confirmed from the session log
during recovery. If the brief differs, the site states the difference instead
of implying a like-for-like run.

### Layout Skill Bench arms

All three ran under opencode with `qwen3.8-flash-next`. Only the design skill
differs.

| Arm | Source folder | Skill | Form |
| --- | --- | --- | --- |
| `design-skill` | `qwen38-next-layout-bench/design-skill` | to be established from the session | 5 static page directories |
| `taste-skill` | `qwen38-next-layout-bench/taste-skill` | `Leonxlnx/taste-skill` (3 skills, see lock) | Vite React app, 5 routes |
| `taste2` | `qwen38-next-layout-bench/taste2` | `Leonxlnx/taste-skill` (same lock) | 5 static HTML pages + Node server |

`taste-skill` and `taste2` carry an identical `skills-lock.json` pinning
`brandkit`, `design-taste-frontend` and `high-end-visual-design` from
`Leonxlnx/taste-skill`. `design-skill` has no lock file. Its skill configuration
is read from opencode session `ses_f87267505ffelX5pJ5rzkCs9Pl`, not guessed.
Should the two locked arms prove identical in configuration, the site says so
and presents the pair as a repeat run rather than as two skills.

## 2. Repository placement

Two new campaigns under `bench/`, matching the campaign rule in AGENTS.md.

```
bench/agent-build-off/
├── plan.md                  runbook, verbatim brief, arm table, publish rewrites
├── results/
│   ├── arms.json            every recovered metric, one record per arm
│   └── <arm>.md             per-arm STATS (3 copied, 1 recovered)
└── demos/<arm>/             vendored source: src, public, index.html,
                             package.json, package-lock.json, tsconfig, vite config

bench/layout-skill-bench/
├── plan.md
├── results/{arms.json, <arm>.md}
└── demos/<arm>/
```

Vendored source excludes `node_modules`, `dist` and `.git`. Astra's `public/`
holds 2.2 MB of licensed models and audio with an existing `ATTRIBUTION.md`,
which is copied with it, plus 1.9 MB of verification screenshots under `docs/`.

Measured payload, per arm, excluding those three directories:

| Campaign | Arm | Size |
| --- | --- | --- |
| Build-Off | `opencode-qwen38` | 153 KB |
| Build-Off | `opencode-qwen38-superpowers` | 402 KB |
| Build-Off | `claude-opus5` | 624 KB |
| Build-Off | `codex-astra` | 4.2 MB |
| Layout | `design-skill` | 60 KB |
| Layout | `taste-skill` | 256 KB |
| Layout | `taste2` | 270 KB |

Total tracked payload is 6.0 MB, of which `codex-astra` is 70 %. Its assets and
screenshots are the reason; both are cited by its verification record, so both
are kept.

Each arm gains a one-line cross-reference in its existing
`bench/harness-matrix/results/<harness>/<model>.md` verdict, so the matrix
stays the index into every artifact.

### AGENTS.md amendment

AGENTS.md currently routes every harness artifact to
`bench/harness-matrix/logs/`, which is gitignored, with a single tracked
exception for SVGs. A published, runnable demo does not fit that rule: it must
be tracked, and it is a directory rather than one file.

The amendment adds a third artifact class and states where each goes.

| Class | Example | Location | Tracked |
| --- | --- | --- | --- |
| Raw run output | transcripts, traces, `*.log`, run dirs | `bench/<campaign>/logs/` | no |
| Small artifact | model-generated SVG | `logs/` (SVG only) or `results/` | yes |
| Runnable artifact | a demo app the model wrote, published on the site | `bench/<campaign>/demos/<arm>/` | yes, source only |

The amendment states three rules for `demos/`:

- It holds **source**, never `node_modules` and never build output. The site
  builds it.
- It is the artifact as the model produced it. Fixes needed for hosting happen
  at publish time and are listed in the campaign's `plan.md`.
- A campaign gets a `demos/` directory only when its artifacts are published.

The amendment also records that `reports/` is published to the `gh-pages`
branch by a workflow, which the current AGENTS.md does not mention.

## 3. Data recovery

Two gaps. Both sources are verified present.

### Arm `codex-astra`

No `STATS.md`. Eight Codex rollout files sit under
`~/.codex/sessions/2026/09/06/`, matched by `cwd`
`/Users/vitor/LocalProjects/hyper-runner-astra`. They carry `token_count`
events with exact totals; the largest session reports 10,429,199 input tokens
(10,276,864 cached), 51,706 output and 8,482 reasoning. Tool calls, prompts,
model id `gpt-6-astra` and timestamps are all in the same files.

Recovery writes `bench/agent-build-off/results/codex-astra.md` on the same
headings the other three use: Session, Tokens, Code, Libraries, Build output,
Process, Defects, Not verified. Its existing `docs/VERIFICATION.md` and
`docs/performance.json` fold into the Process and Not-verified sections. Arm
`codex-astra` is the only arm with a measured frame rate — 60.00 fps mean over
125 s — which the other three list as "not collected". The site shows that
asymmetry as a gap in the others, not as a win for this arm.

Sessions are split across eight rollout files because Codex starts a new file
on resume. Wall time is the span from the first to the last, with the same
input-wait and sleep deductions the `opencode-qwen38-superpowers` STATS already
applies. Where a deduction cannot be computed, the row says so.

### Layout Skill Bench

No metrics at all. All three sessions are present in
`~/.local/share/opencode/opencode.db`:

| Arm | Session | Title | Started |
| --- | --- | --- | --- |
| `design-skill` | `ses_f87267505ffelX5pJ5rzkCs9Pl` | Landing page 5 iterations | 2026-09-06 22:31:57 |
| `taste-skill` | `ses_f8718363bffeHuTLocWC8uYT7G` | Anti-slop frontend design skill | 2026-09-06 22:47:31 |
| `taste2` | `ses_f86fd99a2ffe1axcggL9fDiPuH` | Awwwards-Tier UI Design | 2026-09-06 23:16:35 |

The same query that produced arm `opencode-qwen38`'s numbers applies. Each arm
gets a `results/<arm>.md` and a record in `arms.json`. The brief per arm is
quoted verbatim from the session, because the three titles suggest the briefs
may not be identical — if they differ, the site presents the arms as three
runs, not as a controlled skill comparison.

### `arms.json`

One JSON file per campaign, holding a `MODELS`-style arm roster and a
`RESULTS`-style list of tidy metric records, matching the two-array data model
that `reports/README.md` documents. Numbers live once, in `arms.json`. The
dashboard pages read from it. A metric not collected for an arm is `null` and
renders as a gap, never as zero.

## 4. The site

### Current state

GitHub Pages serves branch `gh-pages`, path `/`, at
`https://snagnever.github.io/macstudio-local-llm/`. That branch holds three
files: `index.html`, `overview.html`, `perf-lines.html`. The entire `reports/`
directory — five dashboards and `charts-common.js` — is **not published**. The
workflow in section 5 fixes that.

### Published tree

```
index.html                        hub, with cards for all benchmarks
agent-build-off.html              NEW
layout-skill-bench.html           NEW
harness-matrix-svgbench.html      SVGBench, existing
benchmark-charts.html
quality-benchmarks-charts.html
terminal-bench-scoreboard.html
charts-common.js
overview.html                     preserved from the current gh-pages
perf-lines.html                   preserved from the current gh-pages
demos/
├── build-off/{opencode-qwen38, opencode-qwen38-superpowers,
│              claude-opus5, codex-astra}/
└── layout/{design-skill, taste-skill, taste2}/
```

`overview.html` and `perf-lines.html` exist only on `gh-pages` today. They are
copied into `reports/` on `main` first, so the workflow has one source and
nothing is lost when it overwrites the branch.

### `agent-build-off.html`

A comparison table across every metric the four arms share: wall time, active
time, tokens by class, source lines, source files, documentation lines, direct
and transitive dependencies, bundle size raw and gzipped, build time, tests,
tool calls, and defects found. A **Play** button per arm opens the live demo.

The defect narratives are the strongest content in the three existing STATS
files — a Rapier collision bug found by per-frame tracing, a hitbox defect
found by a scripted autopilot, a shader flicker traced by reading installed
shader source. Each arm's defects appear as a list under its column.

The page states plainly what is not comparable: the local arms cost no money
and took longer, one arm ran with a skill library the others lacked, and only
one arm has a measured frame rate.

### `layout-skill-bench.html`

A 3 × 5 grid. Each cell is a live thumbnail linking to the real page. Session
metrics per skill sit above the grid. Where the briefs differ, the page quotes
each one.

Both pages are self-contained, load `charts-common.js` as a classic script, and
keep their data inline, matching the conventions in `reports/README.md`.

### Hub

`reports/index.html` gains a card per new benchmark alongside the existing SVG
section, and links `overview.html` and `perf-lines.html` so the older pages stay
reachable.

## 5. Publishing

A GitHub Actions workflow, `.github/workflows/publish-pages.yml`, on push to
`main`, and manually via `workflow_dispatch`.

Steps:

1. Check out `main`. Set up Node 22.
2. For each demo: `npm ci`, then build with an explicit base path.
3. Apply the publish-time fixes listed below.
4. Assemble the site tree: copy `reports/*`, then the built demos into `demos/`.
5. Deploy to `gh-pages`.

### Publish-time fixes

Each fix exists because the model-written source assumes it is served from a
domain root. The site is served from `/macstudio-local-llm/`. The tracked
source keeps what the model wrote; the fix is applied to the copy the workflow
builds, and every fix is listed in the campaign's `plan.md`.

| Arm | Problem | Fix |
| --- | --- | --- |
| `opencode-qwen38` | no `base` in `vite.config.ts`; `dist` emits `/assets/…` | `vite build --base=/macstudio-local-llm/demos/build-off/opencode-qwen38/` |
| `opencode-qwen38-superpowers` | same | same, with its own path |
| `claude-opus5` | none — `base: './'` already set | build unchanged |
| `codex-astra` | none — `base: './'` already set | build unchanged |
| `taste-skill` | no `base`; **and** `normalize()` in `src/App.tsx` matches `window.location.pathname` against `/1`…`/5`, falling back to `/1` for anything else, so every subpath URL collapses to page 1 | `vite build --base=…`, plus a patch prefixing the route table and `navigate()` with the base path, plus `404.html` copied from `index.html` for history-API fallback |
| `design-skill` | index and in-page switchers link to `/1/`…`/5/` absolutely | rewrite to relative links in the copied files |
| `taste2` | pages link extensionlessly (`href="1"`), resolved by its Node `server.js`, which the static host does not run; no index page | rewrite to `href="1.html"`…`"5.html"` and generate an index listing the five pages |

The `taste-skill` patch is the only fix that changes program logic rather than
a path string. It is applied as a checked-in patch file under
`bench/layout-skill-bench/`, so what changed is reviewable and the original
source stays untouched.

`taste2` and `design-skill` load fonts from Google Fonts and Fontshare at
runtime. Those requests continue to work on the public site and are noted, not
removed.

### Reproducibility

`npm ci` against each committed `package-lock.json` pins every transitive
version, so a rebuild reproduces the measured bundle. If a future build drifts
from the recorded size, the site's figures still come from `arms.json`, which
is the measurement, and the drift is a finding to report rather than a number
to overwrite.

## 6. Verification

Before the workflow is wired:

- Build all seven demos locally. A demo that does not build is reported, not
  dropped from the site.
- Serve the assembled tree from a local static server under the real
  `/macstudio-local-llm/` prefix. Confirm every demo loads, every switcher and
  route works, and no request 404s.
- Check both new dashboard pages against `arms.json`: every displayed number
  traces to a record, and every `null` renders as a gap.

After the first deploy:

- Load the live site and confirm the same checks pass.

Not verified, and stated once on the site: audible output in any demo,
behaviour on physical mobile hardware, and frame rate for the three arms that
never measured it.

## 7. Order of work

1. Recover arm `codex-astra` and the three layout arms into `results/`.
2. Vendor sources, write both `plan.md` files, amend AGENTS.md, copy
   `overview.html` and `perf-lines.html` into `reports/`.
3. Build `agent-build-off.html` and `layout-skill-bench.html`; update the hub.
4. Add the workflow, verify the assembled site locally, deploy, verify live.
