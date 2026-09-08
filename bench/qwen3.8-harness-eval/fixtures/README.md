# Fixtures

Starter projects for the challenge templates in `../tasks/`.

| Fixture | Used by | What it is |
|---|---|---|
| `ledger/` | T1, T2, T4 | Python CLI with three seeded bugs and failing tests |
| `envfail/` | T5 | Python project with a broken developer environment |

Never hand these directories to an agent in place. Copy them first:

```bash
cp -R bench/qwen3.8-harness-eval/fixtures/ledger /path/to/scratch/ledger-<run-id>
```

The copy keeps the fixture clean for the next run and keeps agent output out of
this repository.
