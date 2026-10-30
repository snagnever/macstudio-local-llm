This repository is a small bash backup toolkit: `backup.sh`, `rotate.sh`, `verify.sh`, `restore.sh` and `report.sh`, with logging helpers in `lib/log.sh` and a test suite in `tests/run_tests.sh`.

Users report two bugs:
1. `rotate.sh --keep N` deletes a backup even when there are exactly N backups in the directory, and the one it deletes is the newest.
2. `verify.sh` reports an archive as BAD and exits non-zero when the archive name contains a space (for example `my backup-20260101-000000.tar.gz`), although its checksum is correct.

Fix the two bugs. Add one test for each bug to `tests/run_tests.sh`, next to the existing tests.

The five scripts also carry an identical copy of the option-parsing block and of the `resolve_dir` helper. Move that shared code into a new `lib/common.sh` and source it from every script instead of repeating it; the scripts must keep accepting the same flags.

Run `bash tests/run_tests.sh` from the repository root and make sure every test passes. When you are done, reply with one line that says which files you changed.
