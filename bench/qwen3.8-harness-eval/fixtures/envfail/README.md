# envfail — fixture for task T5

A tiny service with a broken developer environment. The task for the agent:
make `make check` exit 0 without weakening the checks.

Seeded problems:

1. `requirements.txt` misses a dependency that the code imports.
2. `app/report.py` fails the linter (import style, unused import, unused variable).
3. One test depends on an environment variable that is not documented.

Do not fix the problems in this directory. Copy it to a scratch location first.
