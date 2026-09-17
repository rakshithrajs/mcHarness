"""Context management for the harness agent."""

import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from tools.todos import todo_prompt

SEEN: dict[str, float] = {}


def note_read(path: str) -> None:
    """Record the last modified time of a file when it is read."""
    SEEN[path] = os.path.getmtime(path)


def stale_files() -> list[str]:
    """Return a list of files that have changed on disk since they were read."""
    return [p for p, mtime in SEEN.items() if os.path.getmtime(p) != mtime]


def todos_note() -> str:
    """To return the late injection format of message to be appended for the messages."""
    plan = todo_prompt()
    return f"\n<todos>\n{plan}\n</todos>" if plan else ""


def git_branch() -> str:
    """Return the current git branch name, or '(detached)' if in a detached HEAD state."""
    result = subprocess.run(
        "git branch --show-current",
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        executable=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        check=False,
    )
    return result.stdout.strip() or "(detached)"


def reminder() -> dict[str, str]:
    """Return a reminder message with the current time, git branch, and any stale files or todos."""
    return {
        "role": "user",
        "content": (
            "<env>\n"
            f"time {datetime.now(tz=ZoneInfo('Asia/Kolkata')):%Y-%m-%d %H:%M}\n"
            f"git branch: {git_branch()}\n"
            "</env>"
        )
        + stale_note()
        + todos_note(),
    }


def stale_note() -> str:
    """Return a reminder if any files have changed on disk since they were read."""
    changed = stale_files()

    if not changed:
        return ""
    return (
        "\n<system_reminder>\n"
        "These files changed on disk since you read them. Read them again "
        "before editing: \n" + "\n".join(changed) + "\n</system_reminder>"
    )
