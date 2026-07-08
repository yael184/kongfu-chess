#!/usr/bin/env python3
"""PostToolUse hook: after Edit/Write on a Python *source* file, remind Claude to
keep CLAUDE.md in sync and to add/adjust tests for the change.

Reads the hook payload as JSON on stdin and, when relevant, prints a JSON object
whose `additionalContext` is injected back into the model's context.
Prints nothing for non-source files (tests, conftest, non-Python), so it stays quiet.
"""
import json
import os
import sys


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return  # malformed payload -> stay silent, never block

    file_path = (payload.get("tool_input") or {}).get("file_path", "") or ""
    normalized = file_path.replace("\\", "/")
    base = os.path.basename(normalized)

    is_python = base.endswith(".py")
    is_test = base.startswith("test_") or base == "conftest.py" or "/tests/" in normalized
    if not is_python or is_test:
        return

    reminder = (
        f"Reminder (project convention): you just edited the Python source file '{base}'. "
        "Before finishing: (1) update CLAUDE.md and README.md if this changes architecture, "
        "commands, conventions, or documented behavior; (2) add or adjust tests under tests/ "
        "so the change stays covered. Skip only if the edit is a pure comment/formatting change."
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": reminder,
        }
    }))


if __name__ == "__main__":
    main()
