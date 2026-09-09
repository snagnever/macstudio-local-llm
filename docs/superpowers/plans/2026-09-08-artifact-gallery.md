# 2026-09-08 — Artifact gallery: the visual comparison page

> Spec: the approved design in the session chat, summarised in "Design" below.
> Status: in execution.

## Goal

One new published page, `reports/artifacts.html`, that puts the model-generated
artifacts from three closed campaigns side by side so the eye compares first and
the numbers are captions. Existing results only; nothing is re-run.

| Section | Campaign | Rows | Cells |
| --- | --- | --- | --- |
| Drawings | `bench/harness-matrix` (SVGBench) | 7 prompts | one SVG per harness×model pair (best take by default) |
| Game | `bench/agent-build-off` | 1 brief | 4 arms, one screenshot each, link to the built demo |
| Skills | `bench/layout-skill-bench` | 1 brief, iteration selector 1–5 | 3 skill arms, one screenshot per iteration, link to the page |

## Design (binding)

- **Structure:** a row is one brief; a cell is one artifact from one contestant.
  Same grammar in all three sections.
- **Hero:** the first Drawings row (question 0, "cow plowing"), rendered large.
  No headline number, no stat tiles.
- **Views for Drawings:** `best take per prompt` (default: highest-scoring
  artifact of each pair on that question; ties → lowest `TAKE_RANK`), `all takes`
  (every artifact, grouped by prompt), `by model` (one row per pair, its prompts
  in question-index order). A `<select>` or segmented control, state in the URL
  hash so a view is linkable.
- **Cell caption:** contestant name, take label, and the support number(s).
  Drawings: `met/total` plus a thin meter. Game: wall min, output tokens, source
  lines, defects. Skills: wall min, output tokens. A metric the campaign did not
  collect renders as `—`, never 0.
- **Contestant colour:** a 3 px line above the caption. Qwen `#2a9d8f`, Claude
  `#e76f51`, Codex `#f4a261`, gpt-5.6-terra `#5c6f8a`. Qwen + superpowers uses
  `#52b788` (from `arms.json`). Local versus hosted is stated once in the legend.
- **Palette:** ground `#b7bbb5`, mat `#fbfbf9`, ink `#1a1c19`, soft ink
  `#4a4e49`, line `#9a9e98`. Single committed look; no dark-mode swap.
- **Type:** Fraunces (italic, optical size) for each row's prompt/brief title and
  the page title; Schibsted Grotesk for captions and controls, tabular numerals.
  Both from Google Fonts with real fallbacks. No all-caps labels, no eyebrows,
  no decorative numbering, no `→` in links.
- **Interaction:** click a cell → `<dialog>` with the artifact large, ← → to move
  along the row, Esc closes, focus returns to the cell. For Drawings the dialog
  lists each requirement with met/failed and the judge note. Only the dialog
  transitions; no entrance animation. `prefers-reduced-motion` disables it.
- **Layout:** left-aligned, `max-width: 1280px`; rows scroll horizontally under
  ~900 px with the prompt title staying put. Visible keyboard focus.
- **Quality floor:** self-contained HTML (inline CSS/JS, data embedded), works
  from `file://` opened at `reports/` and from the published site root.

## Paths (binding)

- Artifact SVGs: `bench/harness-matrix/logs/<harness>/<model>/<slug>.svg`
  (tracked; the publish workflow exports `bench/harness-matrix` to the site
  root). From `reports/artifacts.html` the relative path is
  `../bench/harness-matrix/...` locally and `bench/harness-matrix/...` on the
  site — reuse whatever `reports/harness-matrix-svgbench.html` does to resolve
  this and match it exactly.
- Game shots: `bench/agent-build-off/results/shots/<arm-id>.webp`.
- Skills shots: `bench/layout-skill-bench/results/shots/<arm-id>-<n>.webp`, n 1–5.
- Demo links on the site: `demos/build-off/<arm-id>/`, and for layouts the
  per-arm URL rules already in `reports/layout-skill-bench.html` (design-skill
  `demos/layout/design-skill/<n>/`, taste-skill `demos/layout/taste-skill/#<n>`
  or whatever that file uses, taste2 `demos/layout/taste2/<n>.html`). Copy the
  rule from that file; do not invent one.
- Data generator: `tools/artifacts_data.py`, writes the block between
  `/* DATA:begin */` and `/* DATA:end */` in `reports/artifacts.html`;
  `--check` exits 1 when stale. Same contract as
  `bench/harness-matrix/scripts/svgbench/gallery_data.py`.

## Global constraints

- Use existing results only. No benchmark is re-run, no score is edited.
- Screenshots photograph the vendored demos as built; they are not results and
  carry no score.
- Every number on the page traces to `scores.json` or an `arms.json`.
- Keep each `.webp` under 300 KB; viewport 1280×800; no retina scaling.
- Follow `AGENTS.md` placement rules.
- Commit per task with the repository's commit style
  (`reports: …`, `bench(<campaign>): …`, `ci: …`, `docs(plan): …`).

## Tasks

### Task 1 — Capture the game and layout screenshots

Files: `bench/agent-build-off/scripts/capture-shots.sh`,
`bench/layout-skill-bench/scripts/capture-shots.sh`, the 4 + 15 `.webp` files.

1. Serve each built game demo (`bench/agent-build-off/demos/<arm>/dist/`, already
   built locally; rebuild with `npx vite build` in that folder if `dist/` is
   missing) over a local `python3 -m http.server` on a free port and capture
   with headless Chrome (`/Applications/Google Chrome.app/Contents/MacOS/Google
   Chrome --headless=new --hide-scrollbars --window-size=1280,800
   --virtual-time-budget=10000 --screenshot=<png> <url>`). Do **not** pass
   `--disable-gpu`; three.js needs WebGL (SwiftShader is fine). If a demo shows
   a start screen, that start screen is the artifact; do not script clicks.
2. Layouts: `design-skill` is static (`demos/design-skill/<n>/index.html`),
   `taste2` is static (`demos/taste2/pages/<n>.html`), `taste-skill` is a vite
   app (build it with the base the publish workflow uses, serve `dist/`, and
   open the per-iteration URL the app uses — read
   `reports/layout-skill-bench.html` for the rule). Capture all five iterations
   per arm.
3. Convert with `cwebp -q 82 -resize 1280 0`; assert every file < 300 KB.
4. If a capture is blank or errors, keep the real capture and write the error
   into `results/shots/README.md` next to the file; never substitute an image.
5. The scripts must be re-runnable and must not modify `demos/`.

Verify: `ls -la` both `shots/` directories; open two captures with the Read
tool and confirm they show a scene, not a blank page.

Commit: `bench(agent-build-off,layout-skill-bench): screenshot the vendored demos`.

### Task 2 — Data generator and the page

Files: `tools/artifacts_data.py`, `reports/artifacts.html`.

1. Generator reads `bench/harness-matrix/results/svgbench/scores.json`,
   `bench/agent-build-off/results/arms.json`,
   `bench/layout-skill-bench/results/arms.json`. Emits one JSON object with
   `drawings` (questions with prompt text, pairs, artifacts with slug, take,
   file, animated, score, met, total, requirements[{t,m,n}]), `game` (arms with
   label, harness, model, hosted, color, shot path, demo path, metrics
   wallMinutes / tokensOutput / sourceLines / defectsFound with their notes),
   `skills` (arms with skillConfig, label, color, shots[1..5], page URLs,
   metrics wallMinutes / tokensOutput) and `generated_at`. Reuse
   `split_slug`/`TAKE_RANK`/`PROMPT_LABEL` from `gallery_data.py` by import or
   copy; keep behaviour identical.
2. Page per the Design section. Data block between the markers. All three
   sections rendered from that JSON by inline JS; no framework; Google Fonts is
   the only network dependency.
3. Tests: `tools/tests/test_artifacts_data.py` (pytest) covering best-take
   selection with a tie, `—` for a `None` metric, `--check` staleness.

Verify: run the generator, open the page in the browser pane from
`reports/artifacts.html`, check console is clean, screenshot the hero row and
each section, test the dialog and the three views.

Commit: `reports: artifacts gallery — drawings, game and skills side by side`.

### Task 3 — Publish, link, document

Files: `.github/workflows/publish-pages.yml`, `reports/index.html`,
`reports/README.md`.

1. Workflow: copy `bench/agent-build-off/results/shots` and
   `bench/layout-skill-bench/results/shots` into `site/` at the same relative
   paths; add `test -f site/artifacts.html` and one `test -f` per shots dir.
   Add both `shots/**` globs to the workflow `paths:` trigger list if it has one.
2. Hub: a link card to `artifacts.html` in the "Agent & skill comparisons"
   section, same markup as the two existing cards, copy in the page's voice.
3. README: one short section "Artifacts gallery" naming the generator, the
   `--check` command, and the two screenshot scripts.

Verify: `python3 tools/artifacts_data.py --check` exits 0; the workflow YAML
parses (`python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/publish-pages.yml'))"`
or `ruby -ryaml`).

Commit: `ci: publish the artifacts gallery and its screenshots`.
