#!/usr/bin/env python3
"""Stand-in for a harness binary. FAKE_MODE picks the behaviour; the task comes from FAKE_TASK.

solve: apply the reference solution and exit 0.   exit0_no_work: exit 0, change nothing.
crash: exit 3.   hang_with_child: start a child that sleeps, write its pid to child.pid, then sleep.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if "--version" in sys.argv:
    print("fake 1.0")
    sys.exit(0)

print("SECRET-TRANSCRIPT working on it")
mode = os.environ.get("FAKE_MODE", "solve")
if mode == "solve":
    import solutions
    solutions.solve(os.environ["FAKE_TASK"], Path.cwd())
elif mode == "crash":
    sys.exit(3)
elif mode == "hang_with_child":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    Path("child.pid").write_text(str(child.pid))
    time.sleep(600)
