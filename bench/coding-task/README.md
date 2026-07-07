# Coding task — qualitative app-build benchmark

Each subdirectory is a small "task manager" app produced by a different local model
when given roughly the same product brief. Use these to compare each model's
**actual coding output** (architecture choices, code clarity, completeness, bugs)
side-by-side — complementing the numeric scores in `../../reports/` and
`../../tools/local-llm-bench-m4-32gb/results/`.

## The brief (paraphrased)

> Build a small task manager: add tasks, mark complete, delete, persist state.
> Pick the stack you'd reach for. Ship something that runs.

Each model picked its own stack and depth of implementation. No follow-up
prompts, no manual fixes.

## What's here

| Folder | Model | Stack picked | How to run |
|---|---|---|---|
| `qwen3-coder-next-80b-a3b/` | Qwen3-Coder-Next 80B/3B MoE (6-bit MLX) | Next.js 16 + Tailwind + SQLite | `npm install && npm run dev` (then http://localhost:3000) |
| `qwen3.6-27b-mlx-6bit/` | Qwen3.6 27B dense (6-bit MLX) | Static HTML/CSS/JS, localStorage | Open `index.html` in a browser |

The Next.js app's `node_modules/` and `.next/` are intentionally **not** checked in —
`npm install` regenerates them.

## Suggested comparison axes

- **Stack ambition vs. fit**: did the model over-engineer (DB + framework for a TODO) or under-engineer (no persistence)?
- **First-run correctness**: does it work after `install` / open with zero edits?
- **Code clarity**: file organisation, naming, comments.
- **Robustness**: empty input, duplicate tasks, refresh persistence.
- **Accessibility / UX polish**: keyboard handling, focus, semantics.

Add new subdirectories here when running the same brief against more models.
