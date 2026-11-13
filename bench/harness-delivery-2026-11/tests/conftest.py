"""Shared helpers: load the campaign scripts and build solved or cheated copies of a task repository."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE / "tests"))

import solutions  # noqa: E402
import tasks  # noqa: E402


def solved(task, tmp_path, drop_step=None):
    """A fresh copy of the task repository with the reference solution applied."""
    repo = tasks.fresh_copy(task, tmp_path / f"solved-{task}")
    solutions.solve(task, repo, drop_step=drop_step)
    return repo


def cheated(task, cheat, tmp_path):
    """The reference solution, then one forbidden shortcut on top of it."""
    repo = solved(task, tmp_path)
    solutions.cheat(task, cheat, repo)
    return repo


@pytest.fixture(scope="session")
def t5_solved(tmp_path_factory):
    """One solved T5 copy with its virtualenv (pip needs the network); tests copy it."""
    repo = solved("T5", tmp_path_factory.mktemp("t5"))
    subprocess.run(["make", "venv"], cwd=repo, check=True, capture_output=True)
    return repo


def clone(repo, dest):
    shutil.copytree(repo, dest, symlinks=True)
    return dest
