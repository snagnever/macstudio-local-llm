"""Registry of the 7 coding tasks: where the repository comes from, the prompt and the time limit."""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_TASKS = REPO_ROOT / "bench/flashnext-concurrency-2026-10/scripts/claude-tasks"
HARNESS_EVAL = REPO_ROOT / "bench/qwen3.8-harness-eval"
IGNORED = shutil.ignore_patterns("__pycache__", ".pytest_cache", ".ruff_cache", ".venv", "*.pyc")


@dataclass(frozen=True)
class Task:
    id: str
    repo_src: Path
    prompt_file: Path
    limit_s: int
    hard: bool


def _small(task_id: str) -> Task:
    return Task(task_id, CLAUDE_TASKS / f"repo-{task_id}", CLAUDE_TASKS / f"task-{task_id}.md", 900, False)


def _hard(task_id: str, template: str, fixture: str, limit_s: int) -> Task:
    return Task(task_id, HARNESS_EVAL / "fixtures" / fixture, HARNESS_EVAL / "tasks" / template, limit_s, True)


TASKS: dict[str, Task] = {
    "a": _small("a"), "b": _small("b"), "c": _small("c"), "d": _small("d"),
    "T1": _hard("T1", "T1-bugfix.md", "ledger", 900),
    "T5": _hard("T5", "T5-env-repair.md", "envfail", 1200),
    "T7": _hard("T7", "T7-chain.md", "ledger", 1800),
}


def prompt(task_id: str) -> str:
    """The text a harness receives. Hard tasks: the first ```text block of the template's Prompt section."""
    task = TASKS[task_id]
    text = task.prompt_file.read_text(encoding="utf-8")
    if not task.hard:
        return text.strip()
    section = text.split("## Prompt", 1)[1]
    return re.search(r"```text\n(.*?)```", section, re.S).group(1).strip()


def fresh_copy(task_id: str, dest: Path) -> Path:
    """Copy the task repository to dest, without caches. dest must not exist."""
    shutil.copytree(TASKS[task_id].repo_src, dest, ignore=IGNORED)
    return dest
