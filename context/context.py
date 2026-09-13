import os
import subprocess
from datetime import datetime

SEEN: dict[str, float] = {}


def note_read(path: str):
    SEEN[path] = os.path.getmtime(path)


def stale_files() -> list[str]:
    return [p for p, mtime in SEEN.items() if os.path.getmtime(p) != mtime]


def git_branch():
    result = subprocess.run(
        "git branch --show-current",
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="repalce",
        executable=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    )
    return result.stdout.strip() or "(detached)"


def reminder():
    return {
        "role": "user",
        "content": (
            "<env>\n"
            f"time {datetime.now():%Y-%m-%d %H:%M}\n"
            f"git branch: {git_branch()}\n"
            "</env>"
        ),
    }


def stale_note():
    changed = stale_files()

    if not changed:
        return ""
    return (
        "\n<systen_reminder>\n"
        "These files changed on disk since you read them. Read them again "
        "before editing: \n" + "\n".join(changed) + "\n</system_reminder>"
    )
