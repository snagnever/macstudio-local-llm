# backup toolkit

Five small bash scripts that together implement a plain, inspectable backup
routine for a directory: make a timestamped `tar.gz` with a SHA-256 sidecar,
keep the newest N archives, check the checksums, restore, and report sizes.

```
backup.sh   --dest DIR --name NAME SOURCE      write NAME-<stamp>.tar.gz + .sha256
rotate.sh   --dest DIR --name NAME --keep N    delete all but the N newest
verify.sh   --dest DIR                         "ok <file>" / "BAD <file>" per archive
restore.sh  --dest DIR [--target DIR] ARCHIVE  extract (or --list) an archive
report.sh   --dest DIR [--top N]               size table, largest first
```

Every script accepts `--quiet`, `--dry-run` where it makes sense and `-h`.
The scripts need only bash 3.2 (the stock macOS `/bin/bash`), `tar`, `gzip`,
`shasum`, `find` and `sort`. Logging helpers live in `lib/log.sh`.

Full documentation: [docs/USAGE.md](docs/USAGE.md) for the flags, examples and
exit codes; [docs/DESIGN.md](docs/DESIGN.md) for the reasoning behind the file
layout, the naming convention and the portability rules.

Tests: `bash tests/run_tests.sh` from the repository root.
