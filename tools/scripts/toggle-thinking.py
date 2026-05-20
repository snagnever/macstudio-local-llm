#!/usr/bin/env python3
"""Toggle thinking on/off for any Qwen model in LM Studio."""

import sys, os, shutil

TEMPLATE = os.path.expanduser("~/.lmstudio/models/mlx-community/Qwen3.6-27B-6bit/chat_template.jinja")
BACKUP = TEMPLATE + ".bench-backup"
PATCH_LINE = "{%- set enable_thinking = false %}"

def status():
    if not os.path.exists(TEMPLATE):
        print(f"Template not found: {TEMPLATE}")
        sys.exit(1)
    with open(TEMPLATE) as f:
        content = f.read()
    if PATCH_LINE in content:
        print("Thinking: OFF (patched)")
    else:
        print("Thinking: ON (original)")

def off():
    if not os.path.exists(TEMPLATE):
        print(f"Template not found: {TEMPLATE}", file=sys.stderr)
        sys.exit(1)
    with open(TEMPLATE) as f:
        content = f.read()
    if PATCH_LINE in content:
        print("Thinking is already OFF.")
        return
    shutil.copy2(TEMPLATE, BACKUP)
    with open(TEMPLATE, "w") as f:
        f.write(PATCH_LINE + "\n" + content)
    print("Thinking disabled. Reload the model in LM Studio to apply.")

def on():
    if os.path.exists(BACKUP):
        shutil.copy2(BACKUP, TEMPLATE)
        os.remove(BACKUP)
        print("Thinking restored to ON. Reload the model in LM Studio to apply.")
    elif PATCH_LINE not in open(TEMPLATE).read():
        print("Thinking is already ON (no backup found, template unchanged).")
    else:
        with open(TEMPLATE) as f:
            content = f.read()
        patched = content.replace(PATCH_LINE + "\n", "", 1)
        with open(TEMPLATE, "w") as f:
            f.write(patched)
        print("Thinking re-enabled (removed patch). Reload the model in LM Studio to apply.")

if len(sys.argv) < 2:
    print("Usage: toggle-thinking.py [on|off|status]")
    sys.exit(1)

cmd = sys.argv[1].lower()
{"status": status, "on": on, "off": off}.get(cmd, lambda: print(f"Unknown command: {cmd}"))()
