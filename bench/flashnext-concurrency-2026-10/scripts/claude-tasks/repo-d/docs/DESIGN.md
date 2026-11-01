# backup toolkit — design notes

This file records why the toolkit looks the way it does. It is written for
the next person who has to change it, including the author six months from
now. Usage, flags and examples are in [USAGE.md](USAGE.md); this document is
about the decisions, the constraints and the things that were tried and
rejected.

Contents

1. [Goals and non-goals](#1-goals-and-non-goals)
2. [Repository layout](#2-repository-layout)
3. [The archive naming convention](#3-the-archive-naming-convention)
4. [The sidecar](#4-the-sidecar)
5. [One script per verb](#5-one-script-per-verb)
6. [Option parsing](#6-option-parsing)
7. [Logging and output discipline](#7-logging-and-output-discipline)
8. [Exit codes](#8-exit-codes)
9. [Portability rules](#9-portability-rules)
10. [Error handling under `set -euo pipefail`](#10-error-handling-under-set--euo-pipefail)
11. [Handling of unusual file names](#11-handling-of-unusual-file-names)
12. [Testing strategy](#12-testing-strategy)
13. [Decision records](#13-decision-records)
14. [Known limitations and wish list](#14-known-limitations-and-wish-list)

---

## 1. Goals and non-goals

The toolkit exists to back up a handful of directories on a workstation or a
small server to a local or mounted destination, in a way that can be read,
audited and repaired by anyone with a shell. The goals, in order:

1. **Inspectable.** An archive is a plain `tar.gz`; its checksum is a plain
   text file next to it. Nothing in the destination needs the toolkit to be
   understood or restored. `tar -xzf` and `shasum -c` are enough in an
   emergency, and emergencies are when backups matter.
2. **Boring.** No daemon, no database, no configuration file, no network
   code. Each invocation is a complete, stateless operation driven by its
   flags. The whole behaviour of a job is visible in the crontab line that
   runs it.
3. **Portable across the machines we actually have.** macOS with its stock
   bash 3.2 and BSD userland, and Linux with bash 4 or 5 and GNU userland.
   The same scripts must run unchanged on both.
4. **Safe by default.** Nothing is overwritten, nothing is deleted outside
   the one name you asked to rotate, and a restore refuses an archive whose
   checksum does not match.

Non-goals, equally important to state:

* Incremental or deduplicated backups. If you need those, use a tool built
  for them (restic, borg, Time Machine). This toolkit makes full archives.
* Encryption. Encrypt the destination volume, or pipe the archive through
  `age` or `gpg` in a wrapper.
* Remote destinations. Mount them, or rsync the destination directory
  afterwards. Sidecars make the copy verifiable at the other end.
* Scheduling. cron and launchd exist.

---

## 2. Repository layout

```
backup.sh       make an archive + sidecar
rotate.sh       delete all but the newest N archives of a name
verify.sh       recompute digests, compare with sidecars
restore.sh      extract or list an archive, after checking its sidecar
report.sh       size table of the archives, largest first
lib/log.sh      logging helpers, verbosity convention, die()
tests/run_tests.sh
docs/USAGE.md   user documentation
docs/DESIGN.md  this file
README.md       two paragraphs and a pointer here
```

The five commands sit at the top level rather than in a `bin/` directory so
that `./backup.sh` works from a checkout and `/opt/backup/backup.sh` works
from an install, with no `PATH` manipulation. Each script locates the library
relative to its own location (`$(dirname "${BASH_SOURCE[0]}")/lib/log.sh`),
so the directory can be moved or symlinked as a whole. Symlinking an
individual script elsewhere does not work and is not meant to; the README
says so.

There is deliberately no `install.sh`. Copy the directory.

---

## 3. The archive naming convention

```
<name>-<YYYYmmdd>-<HHMMSS>.tar.gz
```

### 3.1 Why the timestamp is in the name

The alternative is to rely on file modification times, which is what
`ls -t` based rotation scripts do. We rejected it for a concrete reason: the
first time the backup volume was replaced, the archives were copied with a
tool that did not preserve mtimes, every file received the same time, and an
mtime-based rotation would have deleted an arbitrary subset. Putting the
stamp in the name makes age a property of the archive rather than of the
file system entry. It also makes the name self-describing in a directory
listing, which is worth a lot at three in the morning.

### 3.2 Why this stamp format

`YYYYmmdd-HHMMSS` sorts lexically in chronological order as long as all the
fields are zero-padded, which `date +%Y%m%d-%H%M%S` guarantees. The dash in
the middle is there for human readers; it costs nothing because the sort
compares equal prefixes first. Second resolution is enough: the toolkit
refuses to overwrite an existing archive, so two runs in the same second for
the same name fail loudly instead of silently producing one archive.

We considered ISO 8601 with colons (`2026-03-14T02:15:00`). Colons are not
allowed in file names on some file systems that backup volumes often use
(exFAT, SMB shares exported from Windows), so they were out.

### 3.3 Local time, not UTC

The stamp is local time because that is what the person reading the
directory listing expects to match with "the backup from last night". The
cost is an ambiguous hour once a year around daylight-saving changes; since
the stamp also includes the date, lexical order is still correct across the
change except for runs inside the repeated hour itself, which we accept.
A `--utc` flag would be a small change confined to `backup.sh` and the
`archive_date` helper in `report.sh`.

### 3.4 What counts as an archive

Every script recognises archives with the same glob,
`<name>-[0-9]*-[0-9]*.tar.gz`, anchored at the destination directory
(`find -maxdepth 1`). Anything else in the directory is invisible to the
toolkit. The pattern is intentionally slightly loose (it does not insist on
exactly eight and six digits) so that a hand-made archive named along the
same lines is still listed by `report.sh`; the `archive_date` decoder in
`report.sh` is strict and prints `-` when the stamp is not well-formed.

---

## 4. The sidecar

Each archive has a `<archive>.sha256` next to it containing one line in the
format emitted by `shasum -a 256`:

```
<64 hex digits><two spaces><file name>
```

### 4.1 Why a sidecar per archive

The alternatives were a single `SHA256SUMS` manifest per directory, or no
checksum at all.

A manifest is a shared, mutable file. Every backup appends to it, every
rotation has to edit it, two names in the same directory contend for it,
and a crash in the middle of an edit leaves it inconsistent. A sidecar is
created once, deleted with its archive, and never modified. Rotation is a
two-file `rm`. The cost is twice as many files in the directory, which is
irrelevant at the scale the toolkit targets.

No checksum at all was rejected because a backup that cannot be verified is
a hope, not a backup. Bit rot on consumer drives is rare but not
hypothetical, and a truncated copy after a failed rsync is common.

### 4.2 Why the shasum format

Using exactly the format that `shasum` prints means `shasum -c` and
`sha256sum -c` can check our sidecars with no help from us, and tools that
write that format (nearly everything) produce sidecars we can read. It also
means `backup.sh` does not format anything: it runs `shasum -a 256 <name>`
inside the destination and redirects the output. Running it inside the
destination is what makes the second field a bare file name rather than a
path, and a bare name is what keeps the sidecar valid when the directory is
moved.

### 4.3 Reading the sidecar

`verify.sh` reads the first line of the sidecar, takes the digest from it,
and compares it with a freshly computed digest of the archive. The archive
name used for the comparison is the sidecar's own name without the
`.sha256` suffix, which is the only thing that is guaranteed to be correct;
the name recorded inside the sidecar is informational. The comparison is a
plain string comparison of two 64-character lowercase hex strings; `shasum`
always prints lowercase, so no case folding is needed (and `${var,,}` is not
available in bash 3.2 anyway).

---

## 5. One script per verb

The toolkit could have been a single `backup` command with sub-commands
(`backup make`, `backup rotate`, ...). We went with five files because:

* Each file is short enough to read top to bottom. A sub-command dispatcher
  pushes every script's logic into functions in one long file, which is
  harder to review and harder to copy a single piece out of.
* cron lines and wrapper scripts read naturally: `./verify.sh --dest ...`
  says what it does.
* A broken script does not take the others down. If `report.sh` has a syntax
  error, `backup.sh` still runs tonight.

The price is duplication: the option parser and the directory resolution
helper are the same in every script. See the next section for how that is
managed and what we would like to do about it.

---

## 6. Option parsing

### 6.1 The shared block

Every script carries the same option-parsing block: a `while [[ $# -gt 0 ]]`
loop with a `case` over `--dest`, `--name`, `--keep`, `--quiet`, `--dry-run`
and `--help`, followed by a `resolve_dir` helper. The block is marked with a
comment saying it is copied verbatim and must be kept in sync by hand.

Why a copy rather than a library? Historically `lib/log.sh` was the only
shared file and the parser was small. It grew flags one by one, each added to
all five scripts at once, and the copies stayed in step because every change
was reviewed as a five-file diff. The arrangement works but it is the most
error-prone part of the codebase: a flag fixed in four scripts and forgotten
in the fifth is exactly the kind of bug a reviewer does not notice. The
obvious refactor, a `lib/common.sh` that owns the parser and `resolve_dir`
and is sourced by every script, is the first item on the wish list.

### 6.2 Why every script accepts every common flag

`backup.sh` accepts `--keep` even though it does nothing with it. This is on
purpose. A wrapper that passes the same set of flags to several scripts
should not have to know which script tolerates which flag, and a flag that is
a usage error in one script and silently accepted in another is confusing.
The rule is: common flags parse everywhere, and a script uses the subset it
needs. Script-specific flags (`--target`, `--list` in `restore.sh`; `--top`,
`--no-header` in `report.sh`) are handled by a `parse_local_option` hook that
each script defines before the shared block runs. The hook sets `CONSUMED`
to the number of words it used and the shared loop shifts them away.

### 6.3 Values

Both `--flag VALUE` and `--flag=VALUE` are accepted because people type both
and because the `=` form is unambiguous when the value starts with a dash.
A flag that needs a value and does not get one is a usage error, not an
empty value. Numeric flags are validated with a regular expression
(`^[0-9]+$`) right after parsing, so a typo like `--keep 7x` fails before
anything is listed or deleted.

### 6.4 Positional arguments

Positional arguments are collected into the `ARGS` array in order. Scripts
that take none (`rotate.sh`, `verify.sh`, `report.sh`) reject any; scripts
that take exactly one (`backup.sh`, `restore.sh`) reject zero or several. A
`--` ends option parsing, so a directory literally named `-x` can be backed
up with `backup.sh -- -x`.

---

## 7. Logging and output discipline

### 7.1 stdout is the result, stderr is the narrative

This rule is enforced everywhere and is the single most useful property of
the toolkit for scripting. `archive=$(backup.sh ...)` captures the path and
nothing else. `verify.sh | grep ^BAD` works. `report.sh --no-header | awk`
works. The log lines, with their timestamps and levels, go to stderr where
cron collects them.

### 7.2 Levels and verbosity

`lib/log.sh` offers `log_debug`, `log_info`, `log_warn`, `log_error` and
`die`. The threshold is the `VERBOSE` variable: `0` shows warnings and
errors, `1` (the default) adds informational lines, `2` adds debug lines
such as the full paths of removed files or both digests of a comparison.
`--quiet` sets `VERBOSE=0`. The variable is honoured when it comes from the
environment so a whole wrapper can be silenced with one assignment.

Warnings are never suppressed. If `--quiet` hid the "no sidecar; restoring
unverified" warning, a quiet cron job could restore corrupt data without a
trace in the mail.

### 7.3 Message format

```
2026-03-14 02:15:00 [INFO] backup.sh: archiving /Users/ana/Pictures -> ...
```

Timestamp, level in brackets, the script name, a colon, the message. The
script name is derived from `BASH_SOURCE[1]` at load time, so a wrapper that
sources `lib/log.sh` itself gets its own name. The format is fixed-width up
to the message, so `cut -c21-` strips the timestamp when you do not want it.

---

## 8. Exit codes

| code | meaning |
|------|---------|
| 0 | success, including "nothing to do" |
| 1 | usage error |
| 2 | data problem (missing source/archive/destination, checksum mismatch, refusing to overwrite, BAD result) |
| 3 | an external tool (`tar`, `gzip`, `shasum`) failed |

Three non-zero codes is as fine-grained as we need. A wrapper can tell "I
called it wrong" (1) from "the data is not what I expected" (2) from "the
machine is unhappy" (3), and that is what decides whether to page someone.
`die` takes the code as an optional first argument so call sites read
`die 2 "not a directory: $p"`.

"Nothing to do" is success. `rotate.sh` with fewer archives than `--keep`,
`verify.sh` on an empty directory and `report.sh` on an empty directory all
exit 0, with a warning where silence would be surprising. A nightly job must
not fail on its first night.

---

## 9. Portability rules

The scripts run on the stock `/bin/bash` of macOS, which is bash 3.2.57 and
will stay that way for licensing reasons, and on whatever bash a Linux
distribution ships. The rules below keep both happy. They are checked by
reviewers, not by tooling, so they are listed here.

### 9.1 Bash features that are off limits

* **Associative arrays** (`declare -A`) — bash 4.
* **Case modification** (`${var,,}`, `${var^^}`) — bash 4. Use `tr` if you
  must.
* **`mapfile` / `readarray`** — bash 4. Use a `while IFS= read -r` loop.
* **`|&`** and **`;&` / `;;&`** in `case` — bash 4.
* **`${var:offset:length}` on arrays with negative offsets** — bash 4.2.
* **`"${array[@]}"` on an empty array under `set -u`** — an error in bash
  3.2 and 4.0 through 4.3. Check `${#array[@]}` first, or use the
  `${array[@]+"${array[@]}"}` idiom.
* **`local -n`**, **`declare -g`** — bash 4.3 / 4.2.

Allowed and used: `[[ ]]`, `=~` with `BASH_REMATCH`, indexed arrays,
`$(( ))`, `${var#pattern}` and friends, `printf -v`, process substitution
`< <(...)`, here-strings and here-documents, `set -o pipefail`.

### 9.2 Userland differences we work around

* **`stat`** has incompatible flags (`-f %z` on BSD, `-c %s` on GNU). We
  never call it. File sizes come from `wc -c < file`.
* **`date -r`** means "format this epoch" on BSD and "use this file's mtime"
  on GNU. We never call it. Dates in `report.sh` are decoded from the file
  name.
* **`head -n -N`** (all but the last N lines) is GNU-only. Rotation works
  with `tail -n +K` on a sorted list instead.
* **`sort`**: `-r` and `-n` behave the same everywhere. `-V` (version sort)
  is GNU-only and is not used; the stamp format sorts correctly as text.
* **`sed -i`** needs an argument on BSD and must not have one on GNU. We do
  not edit files in place anywhere.
* **`mktemp -d`** without a template works on both.
* **`readlink -f`** is GNU-only (and only recently on macOS). Absolute paths
  are produced with `cd dir && pwd -P`, which is the `resolve_dir` helper.
* **`find -maxdepth 1`** works on both; `-printf` does not and is not used.
* **`tar`**: `-czf`, `-xzf`, `-tzf` and `-C` are common to bsdtar and GNU
  tar. Nothing else is used. Archives created by one extract with the other.
* **`shasum`** is a Perl script shipped with every macOS and with Perl on
  Linux. `sha256sum` is GNU coreutils only. We call `shasum -a 256`.

### 9.3 Things that are the same but look suspicious

* `echo` with escapes differs; we only `echo` plain strings and use
  `printf` for anything with a format.
* `tr -d ' '` after `wc -c` strips the leading padding that BSD `wc` emits.
  GNU `wc` has none, so the `tr` is harmless there.

---

## 10. Error handling under `set -euo pipefail`

Every script starts with `set -euo pipefail`. The combination catches most
accidents but has sharp edges that are worth remembering when editing.

* **Arithmetic that evaluates to zero fails.** `((count++))` when `count` is
  0 returns 1 and, under `set -e`, exits the script. Always write
  `count=$((count + 1))`.
* **`[[ cond ]] && action` as the last line of a function** returns the
  status of the condition when it is false. `log_info` ends with an explicit
  `return 0` for that reason.
* **Command substitutions do not trigger `set -e` in the parent** unless
  they are a simple assignment. `x=$(false)` exits; `echo "$(false)"` does
  not. Capture results into a variable first when the exit status matters.
* **`pipefail` plus `head`** can turn a successful pipeline into a failure
  when the producer is killed by SIGPIPE after `head` closes its input. The
  producers in `report.sh` are small enough that this does not occur in
  practice, but if a future list becomes large, add `|| true` after the
  pipeline or write the list to a temp file first.
* **Globs that match nothing stay literal.** `for f in "$dest"/*.sha256`
  iterates once over the literal pattern when the directory is empty.
  `verify.sh` checks `[[ -e "$f" ]]` first. `shopt -s nullglob` would be
  cleaner but changes behaviour for every glob in the script, so we did not.
* **`read` at end of input** returns 1 for the last line when it has no
  trailing newline. All our producers end lines with `\n`, and the loops
  tolerate a final empty line anyway.

The `die` helper logs and exits with the given code; nothing else in the
scripts calls `exit` with a non-zero code directly, so grepping for `die`
finds every failure path.

---

## 11. Handling of unusual file names

Names come from two places: `--name`, which the user controls, and the
destination directory, which may contain anything. The rules:

* **Spaces** in `--name` and therefore in archive names are supported. Every
  variable expansion that holds a path is double-quoted; lists of paths are
  processed one per line with `while IFS= read -r`; the sidecar is written
  by `shasum` itself so its format is right by construction; `verify.sh`
  takes the archive name from the sidecar's file name rather than by
  splitting the sidecar's content on blanks.
* **Leading dashes** are impossible by construction (`--name` values that
  start with `-` are parsed as flags; use `--name=-odd` if you insist), and
  every `rm` uses `--` in case one gets through.
* **Slashes** in `--name` are refused by `backup.sh`.
* **Newlines** in file names are not supported. The one-path-per-line
  protocol between `find`, `sort` and the processing loops cannot represent
  them. `find -print0` and `read -d ''` would fix it at the cost of
  readability, and no one has ever needed it. Documented limitation.
* **Non-ASCII** is passed through untouched; the scripts never inspect
  individual characters of a name beyond the digits of the stamp.

---

## 12. Testing strategy

`tests/run_tests.sh` is a plain bash script with a `check NAME EXPECTED
ACTUAL` helper, in the same style used by our other shell projects. There is
no framework to install; `bash tests/run_tests.sh` from the repository root
is the whole interface, and a non-zero exit means a failure.

Principles:

* **Fixtures are built, not checked in.** Each test group creates a
  temporary directory, writes a few files, runs the scripts and removes the
  directory. A test never depends on another group's state.
* **Time is pinned.** `BACKUP_STAMP` fixes the stamp so the expected file
  name is a literal. The log timestamps go to stderr and are not compared.
* **Paths are canonical.** The helper `tmpdir` resolves symlinks with
  `pwd -P` the same way the scripts do, so `/var` versus `/private/var` on
  macOS cannot cause a spurious failure.
* **One behaviour per check.** Each `check` has a one-line name that reads
  as a sentence. When a test fails the output shows the expected and actual
  values on separate lines so a diff is unnecessary.
* **Exit statuses are asserted explicitly** with the `rc=0; out=$(...) ||
  rc=$?` pattern, which captures the status without tripping `set -e` (the
  test runner itself does not use `-e` for this reason).

Regression tests are added next to the existing ones under the heading of
the script they exercise. A bug report should turn into a test that fails on
the buggy script and passes after the fix, in the same change.

---

## 13. Decision records

Short records of decisions that were debated, so they are not re-debated.

**DR-1: gzip, not zstd or xz.** gzip is everywhere, including on recovery
media and old NAS boxes. zstd compresses faster and better but is not on
stock macOS. xz is slow. A `--compress` flag could be added later; the
sidecar and naming would be unaffected apart from the extension.

**DR-2: the archive contains the top-level directory.** `tar -C parent
leaf` rather than `tar -C leaf .`. Restoring into an empty target produces a
single directory that can be inspected or moved, instead of a spray of
files. It also makes `restore.sh --list` immediately show what the archive
is about.

**DR-3: rotation by count, not by age.** Count is what people reason about
("keep two weeks of nightlies" is `--keep 14`), it needs no clock, and it
bounds disk usage. Age-based retention would keep growing if the job ran
more often than planned. Both could coexist; see the wish list.

**DR-4: `--name` is required for rotate.** The first prototype rotated
every archive in the directory when no name was given. It was removed after
a near miss on a shared destination. Deleting is the one operation where a
forgotten flag must be a usage error rather than a wider scope.

**DR-5: restore verifies before extracting.** Verification costs one read
of the archive, extraction costs another. For the sizes we handle the
doubled I/O is seconds. Extracting an unverified corrupt archive over live
data would cost much more.

**DR-6: no colour in log output.** Logs go to cron mail and files far more
often than to a terminal. Escape sequences in mail are noise.

**DR-7: `--dry-run` prints the would-be path.** A dry run that prints
nothing on stdout cannot be used to test a wrapper that captures the path.
Printing the path the archive would have had makes `--dry-run` a drop-in
substitute for a real run in a wrapper under test.

---

## 14. Known limitations and wish list

Limitations we know about and accept for now:

* File names containing a newline are not supported (section 11).
* Rotation and report consider only the top level of the destination;
  archives in sub-directories are ignored.
* There is no locking. Two runs of `backup.sh` with the same name in the
  same second collide on the file name and the second fails; two runs of
  `rotate.sh` on the same name at the same time may both try to delete the
  same file, and one of them will log a harmless warning.
* `verify.sh` trusts the first line of the sidecar and ignores the rest.

Wish list, roughly in priority order:

1. **`lib/common.sh`.** Move the option parser and `resolve_dir` out of the
   five scripts into one sourced file. This is the single refactor that
   would most reduce the risk of the copies drifting apart.
2. **`--older-than DAYS` for rotate.sh**, combinable with `--keep` so that
   both a count floor and an age ceiling apply.
3. **`--utc`** for stamps and report dates.
4. **`--exclude PATTERN`** passed through to tar, repeatable.
5. **`--json`** for report.sh, for dashboards that would rather not parse
   columns.
6. **`verify.sh --fix-missing`** to delete orphan sidecars whose archive is
   gone, which happens when someone removes an archive by hand.
7. **Progress for large archives** via `pv` when it is installed.

Items 2 through 7 should wait for item 1; each of them touches the option
parser, and adding a flag to five copies is how copies drift apart.
