# backup toolkit — usage guide

This document is the long form of the `--help` text of the five scripts. It
explains every flag, shows typical command lines, lists the exit codes and
answers the questions that come up most often. The reasoning behind the design
(why the timestamp is in the file name, why there is a sidecar per archive,
why the scripts only need bash 3.2) is in [DESIGN.md](DESIGN.md).

Contents

1. [Conventions shared by all scripts](#1-conventions-shared-by-all-scripts)
2. [backup.sh](#2-backupsh)
3. [rotate.sh](#3-rotatesh)
4. [verify.sh](#4-verifysh)
5. [restore.sh](#5-restoresh)
6. [report.sh](#6-reportsh)
7. [lib/log.sh](#7-liblogsh)
8. [Putting it together: a nightly job](#8-putting-it-together-a-nightly-job)
9. [Exit codes](#9-exit-codes)
10. [FAQ](#10-faq)

---

## 1. Conventions shared by all scripts

### 1.1 File naming

An archive is always called

```
<name>-<YYYYmmdd>-<HHMMSS>.tar.gz
```

for example `photos-20260314-021500.tar.gz`. `<name>` is whatever you pass to
`--name` (or, for `backup.sh`, the basename of the source directory when you
do not pass it). The stamp is local time at the moment the archive was
started. Right next to each archive lives its sidecar:

```
<name>-<YYYYmmdd>-<HHMMSS>.tar.gz.sha256
```

The sidecar is one line in the format produced by `shasum -a 256`:

```
3b1f0c...e9d2  photos-20260314-021500.tar.gz
```

(two spaces between the digest and the file name). Because the sidecar
records the bare file name and not a path, a destination directory can be
moved, rsynced or mounted somewhere else and `shasum -c` will still work on it
from inside that directory.

Every other script recognises archives by this pattern. A file in the
destination that does not match it, say `notes.tar.gz` or `old-backup.tgz`,
is invisible to `rotate.sh` and `report.sh` and will never be deleted or
listed. This is deliberate: the destination is often a shared drop folder.

### 1.2 Ordering

Age is decided by the stamp in the file name, never by the modification time
of the file. Copying a backup folder with `cp -r`, downloading it from object
storage or restoring it from another backup all reset mtimes, and a rotation
that trusted mtimes would then delete the wrong archives. Sorting file names
with the same `<name>-` prefix is the same as sorting by date, because the
stamp is zero-padded and goes from the most significant unit to the least.

### 1.3 Options that every script accepts

| flag | meaning |
|------|---------|
| `--dest DIR` | the directory that holds (or receives) the archives |
| `--name NAME` | the archive base name |
| `--keep N` | how many archives to keep (only `rotate.sh` acts on it) |
| `-q`, `--quiet` | print only warnings and errors on stderr |
| `-n`, `--dry-run` | describe what would happen, change nothing |
| `-h`, `--help` | print the short help and exit 0 |

Values can be given either as `--dest DIR` or as `--dest=DIR`. A bare `--`
ends option parsing; anything after it is treated as a positional argument
even if it starts with a dash. Options and positional arguments may be mixed
in any order.

Every script accepts the whole set so that a flag means the same thing
everywhere, but not every script does something with every flag: `--keep`
is read and validated by `backup.sh` and then ignored. An unknown flag is a
usage error: the help text goes to stderr and the script exits with status 1.

### 1.4 Where the output goes

The scripts keep a strict separation:

* **stdout** carries the one thing a caller may want to capture: the path of
  the new archive, the `ok`/`BAD` lines, the report rows, the names of the
  deleted archives, the target directory of a restore.
* **stderr** carries everything that is for a human: progress, warnings,
  errors, each line prefixed with a timestamp, a level and the script name.

So `archive=$(backup.sh ...)` does exactly what you expect, and
`backup.sh ... 2>/dev/null` silences the chatter without losing the result.

### 1.5 Relative paths

Any directory you pass is resolved against the current working directory and
turned into an absolute path with symlinks resolved before it is used or
printed. This is why the path printed by `backup.sh` may look different from
the one you typed (`/private/var/...` instead of `/var/...` on macOS, for
instance). They name the same place.

---

## 2. backup.sh

```
backup.sh [--dest DIR] [--name NAME] [--quiet] [--dry-run] SOURCE
```

Creates a gzip-compressed tarball of the directory `SOURCE` and writes the
`.sha256` sidecar next to it. The directory itself is stored in the archive,
not only its contents, so an archive of `/home/ana/photos` contains entries
`photos/`, `photos/2026/...` and a restore recreates the `photos` directory
under the target.

### 2.1 Flags

`SOURCE` (positional, required)
: The directory to archive. It must exist and be readable. Exactly one
  source is accepted per run; to back up several directories call the script
  several times, with a different `--name` each.

`--dest DIR`
: Where the archive goes. Defaults to `./backups`. The directory is created
  with `mkdir -p` when it does not exist (not in dry-run mode).

`--name NAME`
: The base name of the archive. Defaults to the basename of `SOURCE`, so
  `backup.sh /srv/www` writes `www-<stamp>.tar.gz`. The name may contain
  spaces and dots but not a slash.

`--quiet`, `-q`
: Suppress informational messages. The archive path is still printed on
  stdout.

`--dry-run`, `-n`
: Print the `tar` command that would run and the sidecar that would be
  written, then exit 0 without touching the destination. The path that the
  archive would have is printed on stdout exactly as in a real run, which
  makes it easy to test a cron line.

`--help`, `-h`
: Show the short help.

### 2.2 Environment

`BACKUP_STAMP`
: Overrides the timestamp part of the name. It must look like
  `YYYYmmdd-HHMMSS`. This exists for tests that need a predictable file
  name; do not set it in production, or two runs in the same second would
  collide (the script refuses to overwrite an existing archive).

`VERBOSE`
: `0`, `1` (default) or `2`; see [lib/log.sh](#7-liblogsh).

### 2.3 Examples

Back up the current project into `./backups`:

```
$ ./backup.sh ~/projects/site
2026-03-14 02:15:00 [INFO] backup.sh: archiving /Users/ana/projects/site -> /Users/ana/projects/backups/site-20260314-021500.tar.gz
2026-03-14 02:15:01 [INFO] backup.sh: wrote site-20260314-021500.tar.gz (184233 bytes) and site-20260314-021500.tar.gz.sha256
/Users/ana/projects/backups/site-20260314-021500.tar.gz
```

Give the archive a name and a destination, and capture the path:

```
$ archive=$(./backup.sh --quiet --dest /Volumes/vault --name photos ~/Pictures)
$ echo "$archive"
/Volumes/vault/photos-20260314-021502.tar.gz
```

See what would happen without writing anything:

```
$ ./backup.sh --dry-run --dest /Volumes/vault --name photos ~/Pictures
2026-03-14 02:15:03 [INFO] backup.sh: would run: tar -czf '/Volumes/vault/photos-20260314-021503.tar.gz' -C '/Users/ana' 'Pictures'
2026-03-14 02:15:03 [INFO] backup.sh: would write: /Volumes/vault/photos-20260314-021503.tar.gz.sha256
/Volumes/vault/photos-20260314-021503.tar.gz
```

### 2.4 Failure behaviour

* If `tar` fails (disk full, unreadable file) the partial archive is removed
  and the script exits 3. Nothing is left behind.
* If `shasum` fails, both the archive and the half-written sidecar are
  removed and the script exits 3. An archive without a valid sidecar would
  be reported as BAD forever, so it is better not to have it.
* If an archive with the same name already exists the script exits 2 without
  touching it.

---

## 3. rotate.sh

```
rotate.sh --dest DIR --name NAME [--keep N] [--dry-run] [--quiet]
```

Deletes every archive called `NAME-<stamp>.tar.gz` in `DIR` except the `N`
newest. The sidecar of a deleted archive is deleted with it. Archives with a
different name, and files that do not follow the naming convention, are
never touched. "Newest" is decided by the stamp in the file name (see
[1.2](#12-ordering)).

### 3.1 Flags

`--dest DIR` (required)
: The directory to clean up.

`--name NAME` (required)
: Only archives with this base name are considered. The flag is required on
  purpose: rotating a shared destination without a name would be a very easy
  way to lose someone else's backups.

`--keep N`
: How many archives to keep. Defaults to 5. Must be a whole number of at
  least 1; `--keep 0` is refused because it would delete every archive, and
  there is `rm` for that.

`--dry-run`, `-n`
: Print `would delete <file>` for each surplus archive and change nothing.

`--quiet`, `-q`
: Suppress the summary and the count on stderr. The `deleted <file>` lines
  still go to stdout.

### 3.2 Output

One line per removed archive on stdout:

```
deleted photos-20260301-021500.tar.gz
deleted photos-20260302-021500.tar.gz
```

With `--dry-run` the lines read `would delete ...` instead. A summary with
the number removed and the number remaining is logged on stderr.

### 3.3 Examples

Keep the seven most recent nightly archives:

```
$ ./rotate.sh --dest /Volumes/vault --name photos --keep 7
2026-03-14 02:16:00 [INFO] rotate.sh: 9 archive(s) named 'photos' in /Volumes/vault, keeping 7
deleted photos-20260305-021500.tar.gz
deleted photos-20260306-021500.tar.gz
2026-03-14 02:16:00 [INFO] rotate.sh: removed 2 archive(s), 7 remain
```

Check first:

```
$ ./rotate.sh --dry-run --dest /Volumes/vault --name photos --keep 7
would delete photos-20260305-021500.tar.gz
would delete photos-20260306-021500.tar.gz
```

When there are fewer archives than `--keep` nothing happens and the exit
status is still 0, so the script is safe to run every night regardless of how
many archives have accumulated.

---

## 4. verify.sh

```
verify.sh --dest DIR [--name NAME] [--quiet]
```

Recomputes the SHA-256 digest of every archive that has a sidecar in `DIR`
and compares it with the recorded value. The result is one line per archive
on stdout and an exit status that says whether everything was fine.

### 4.1 Flags

`--dest DIR` (required)
: The directory holding archives and sidecars.

`--name NAME`
: Check only the archives whose name starts with `NAME-`. Without it every
  sidecar in the directory is checked, whatever the name.

`--quiet`, `-q`
: Suppress the final count on stderr.

### 4.2 Output

```
ok photos-20260313-021500.tar.gz
ok photos-20260314-021500.tar.gz
BAD site-20260314-021500.tar.gz
BAD site-20260312-021500.tar.gz (archive missing)
```

The vocabulary is intentionally tiny so the output is easy to grep:

* `ok <file>` — the digest matches.
* `BAD <file>` — the digest differs. The archive was modified, truncated or
  the sidecar belongs to another file.
* `BAD <file> (archive missing)` — there is a sidecar but no archive.
* `BAD <name>.sha256 (malformed sidecar)` — the sidecar could not be parsed.

The file name printed is the archive name exactly as it appears in the
directory, spaces and all, so you can paste it into another command.

### 4.3 Exit status

`0` when every checked archive is ok, also when there was nothing to check
(a warning is logged in that case). `2` as soon as one archive is BAD. This
makes the script usable directly as a health check:

```
./verify.sh --quiet --dest /Volumes/vault || mail -s "backup verification failed" ops@example.org < /dev/null
```

### 4.4 Example

```
$ ./verify.sh --dest /Volumes/vault --name photos
ok photos-20260312-021500.tar.gz
ok photos-20260313-021500.tar.gz
ok photos-20260314-021500.tar.gz
2026-03-14 02:17:00 [INFO] verify.sh: checked 3 archive(s): 3 ok, 0 bad
```

---

## 5. restore.sh

```
restore.sh [--dest DIR] [--target DIR] [--list] [--dry-run] [--quiet] ARCHIVE
```

Extracts an archive into a target directory, after checking its sidecar when
there is one. With `--list` the contents are printed instead.

### 5.1 Flags

`ARCHIVE` (positional, required)
: Either a path to the `.tar.gz` file, or a bare file name that is looked up
  in `--dest`. If the argument names an existing file it is used as is and
  `--dest` is ignored.

`--dest DIR`
: Where a bare `ARCHIVE` name is looked up. Required when `ARCHIVE` is not a
  path.

`--target DIR`
: Where to extract. Defaults to the current directory. It is created with
  `mkdir -p` when it does not exist. The archive's top-level directory is
  recreated inside it, so restoring `photos-...tar.gz` into
  `--target /tmp/r` produces `/tmp/r/photos/...`.

`--list`, `-l`
: Print the entries of the archive (`tar -tzf`) and exit without extracting.
  The checksum is still verified first.

`--dry-run`, `-n`
: Log what would be extracted and where, print the entry list, write
  nothing.

`--quiet`, `-q`
: Suppress informational messages.

### 5.2 The checksum gate

If `ARCHIVE.sha256` exists next to the archive it is checked before anything
is read from the tarball. A mismatch aborts with exit status 2 and the
message `checksum mismatch for <file>; refusing to restore`. If there is no
sidecar a warning is logged and the restore proceeds; you are presumably
restoring something you brought from elsewhere and know what you are doing.

### 5.3 Examples

Look inside the latest archive:

```
$ ./restore.sh --list --dest /Volumes/vault photos-20260314-021500.tar.gz
2026-03-14 09:00:00 [INFO] restore.sh: checksum ok for photos-20260314-021500.tar.gz
2026-03-14 09:00:00 [INFO] restore.sh: contents of photos-20260314-021500.tar.gz
Pictures/
Pictures/2026/
Pictures/2026/IMG_0001.jpg
...
```

Restore it somewhere harmless and compare:

```
$ ./restore.sh --quiet --target /tmp/check --dest /Volumes/vault photos-20260314-021500.tar.gz
/tmp/check
$ diff -r /tmp/check/Pictures ~/Pictures && echo identical
identical
```

Restore from an archive that is not in a managed destination (a path is
given, so `--dest` is not needed):

```
$ ./restore.sh --target /srv ./downloads/www-20260301-000000.tar.gz
2026-03-14 09:05:00 [WARN] restore.sh: no .sha256 sidecar next to www-20260301-000000.tar.gz; restoring unverified
2026-03-14 09:05:00 [INFO] restore.sh: extracting www-20260301-000000.tar.gz into /srv
2026-03-14 09:05:02 [INFO] restore.sh: restored 1842 entries into /srv
/srv
```

---

## 6. report.sh

```
report.sh --dest DIR [--name NAME] [--top N] [--no-header] [--quiet]
```

Prints a table of the archives in `DIR`: size in bytes, the date decoded from
the file name, and the file name, with the largest archive first.

### 6.1 Flags

`--dest DIR` (required)
: The directory to inspect.

`--name NAME`
: Only list archives whose name starts with `NAME-`.

`--top N`
: Show only the `N` largest archives. `N` must be a whole number.

`--no-header`
: Omit the `SIZE DATE NAME` header line, for piping into other tools.

`--quiet`, `-q`
: Suppress the summary (count and total bytes) on stderr.

### 6.2 Output

```
        SIZE  DATE                 NAME
   184233921  2026-03-14 02:15:02  photos-20260314-021502.tar.gz
   184190004  2026-03-13 02:15:01  photos-20260313-021501.tar.gz
      184233  2026-03-14 02:15:00  site-20260314-021500.tar.gz
```

Sizes are right-aligned in a 12-character column, dates take 19 characters,
and the name runs to the end of the line so that names containing spaces
stay intact. Files whose names do not carry a stamp show `-` in the date
column; they are only listed when they still match `*-<digits>-<digits>.tar.gz`.

Rows are ordered by size, largest first, regardless of how many digits the
sizes have: an archive of 10000 bytes always comes before one of 9999 bytes.
Ties keep an arbitrary but stable order.

### 6.3 Examples

What is eating the disk?

```
$ ./report.sh --dest /Volumes/vault --top 3
```

Total size per name, using the no-header form and awk:

```
$ ./report.sh --quiet --no-header --dest /Volumes/vault | awk '{ split($NF, a, "-"); s[a[1]] += $1 } END { for (n in s) print s[n], n }'
```

---

## 7. lib/log.sh

Not a command; it is sourced by every script and provides:

| function | purpose |
|----------|---------|
| `log_debug MSG` | shown only with `VERBOSE=2` |
| `log_info MSG` | shown with `VERBOSE>=1`; hidden by `--quiet` |
| `log_warn MSG` | always shown |
| `log_error MSG` | always shown |
| `die [CODE] MSG` | `log_error` then `exit CODE` (default 1) |
| `set_quiet` | the same as `--quiet` for callers that source the library |
| `log_is_quiet` | true when informational messages are suppressed |

Every message has the form

```
2026-03-14 02:15:00 [INFO] backup.sh: archiving ...
```

The verbosity is controlled by the `VERBOSE` variable: `0` warnings and
errors only, `1` plus informational messages (default), `2` plus debug. The
variable is honoured when set in the environment, so a cron job can run
`VERBOSE=0 /opt/backup/backup.sh ...` instead of passing `--quiet` to each
command. `--quiet` simply sets `VERBOSE=0` for the rest of the script.

---

## 8. Putting it together: a nightly job

A typical crontab entry runs the four maintenance steps in sequence and only
sends mail when something is wrong:

```
15 2 * * * cd /opt/backup && VERBOSE=0 ./backup.sh --dest /Volumes/vault --name photos /Users/ana/Pictures >/dev/null && ./rotate.sh --dest /Volumes/vault --name photos --keep 14 >/dev/null && ./verify.sh --dest /Volumes/vault --name photos >/dev/null
```

Because every script exits non-zero when it fails and cron mails any output,
a quiet night produces no mail at all. Add `./report.sh --dest /Volumes/vault
--top 5` as a weekly job if you want a size summary in your inbox.

A slightly longer wrapper is more readable and lets you decide what to do on
each failure:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /opt/backup
vault=/Volumes/vault
for dir in /Users/ana/Pictures /Users/ana/Documents; do
  name=$(basename "$dir")
  ./backup.sh --quiet --dest "$vault" --name "$name" "$dir" >/dev/null
  ./rotate.sh --quiet --dest "$vault" --name "$name" --keep 14 >/dev/null
done
./verify.sh --quiet --dest "$vault"
```

---

## 9. Exit codes

All scripts use the same small table.

| code | meaning | typical cause |
|------|---------|---------------|
| 0 | success | also "nothing to do" (no surplus to rotate, nothing to verify) |
| 1 | bad usage | unknown flag, missing value, `--keep abc`, no `SOURCE` |
| 2 | data problem | source missing, destination missing, archive missing, checksum mismatch, archive already exists, `BAD` result in verify |
| 3 | external tool failed | `tar`, `gzip` or `shasum` returned non-zero |

`--help` exits 0 after printing the help on stdout. When a usage error is
detected the help goes to stderr and the exit status is 1.

---

## 10. FAQ

**Why is the timestamp in the file name instead of relying on `ls -t`?**
Because mtimes are not stable. Copying or syncing a backup folder resets
them, and a rotation that trusted them could delete the wrong archive. The
stamp in the name travels with the file.

**Can I use a name with spaces?**
Yes. `--name "my backup"` produces `my backup-<stamp>.tar.gz` and every
script handles the name correctly, including verify and restore. It is
still a good idea to avoid spaces if other tools will touch the directory.

**Why `shasum -a 256` and not `sha256sum`?**
`shasum` is present on macOS and on every Linux with Perl, which is nearly
all of them; `sha256sum` does not exist on macOS. The sidecar format is the
same, so `sha256sum -c` works on it where that tool exists.

**Can I verify without the toolkit?**
Yes: `cd /Volumes/vault && shasum -a 256 -c *.sha256` prints the same
information as `verify.sh` in shasum's own format.

**Does `backup.sh` follow symlinks?**
No. `tar` stores symlinks as symlinks. If you want the content behind a
symlink, back up the real directory.

**Does `rotate.sh` ever delete an archive it did not create?**
It deletes only files called `<name>-<digits>-<digits>.tar.gz` and their
`.sha256` sidecars, for the one `--name` you pass. Everything else in the
directory is left alone.

**Why does `restore.sh` refuse to extract when the sidecar does not match?**
A mismatching sidecar means the archive is not what was backed up: it was
truncated, corrupted in transit, or someone replaced it. Extracting it over
real data could do more damage than having no restore at all. If you really
want the contents, extract with `tar -xzf` by hand.

**Can two backups run at the same time into the same destination?**
Two different names, yes. The same name twice within a second collides on
the file name and the second run exits 2 without touching the first archive.

**How do I keep backups by age instead of by count?**
Not supported directly. Because the stamp is in the name you can do it with
`find`-free shell: list the names, compare the stamp part with the date you
want, and `rm` the older ones together with their sidecars. A `--older-than`
flag is on the wish list in DESIGN.md.

**Is the toolkit safe on Linux?**
Yes. Everything is POSIX shell plus bash 3.2 features, `tar -czf`, `find`,
`sort`, `head`, `tail`, `wc`, `awk` and `shasum`. GNU and BSD variants of
those tools are both fine; the scripts avoid the flags that differ (for
example they never call `stat`, whose options are incompatible, and never
use `head -n -N`, which BSD head does not understand).

**The path printed by backup.sh is not the one I typed.**
Paths are resolved with `pwd -P`, so symlinks are expanded. On macOS `/tmp`
becomes `/private/tmp` and `/var` becomes `/private/var`. They are the same
directory.

**Where is the configuration file?**
There is none. Everything is a flag or an environment variable, so the
complete behaviour of a job is visible in the crontab line or wrapper script
that runs it.
