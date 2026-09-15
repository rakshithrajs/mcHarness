"""Tools for interacting with the system."""

import subprocess
from collections.abc import Callable, Sequence

from ollama._types import Tool as OllamaTool
from ollama._utils import convert_function_to_tool  # type: ignore[partially-known]

from context import context
from security import PermissionManager, SecurityError
from security.permissions import RiskLevel
from skills.skills import read_skill
from tools.todos import write_todos

PERMISSIONS = PermissionManager.from_environment()


def bash(command: str) -> str:
    """Run a shell command and return its combined stdout and stderr.

    Args:
        command: The shell command to run.

    Returns:
        The combined stdout and stderr from the command.
    """
    decision = PERMISSIONS.check_shell(command)
    if decision.risk == RiskLevel.BLOCKED:
        raise SecurityError(decision.reason)
    if not PERMISSIONS.confirm(decision):
        raise SecurityError("user denied shell command")

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        executable=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        check=False,
    )
    return (result.stdout or "") + (result.stderr or "")


def read_file(path: str) -> str:
    """Read a file and return its contents.

    Args:
        path: The path to the file to read.

    Returns:
        The contents of the file.
    """
    decision = PERMISSIONS.check_path(path, "read")
    if decision.risk == RiskLevel.BLOCKED:
        raise SecurityError(decision.reason)
    if not PERMISSIONS.confirm(decision):
        raise SecurityError("user denied file read")

    context.note_read(path)
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    """Create a new file or overwrite an existing one.

    Args:
        path: The path of the file to create or overwrite.
        content: The content to write into the file.

    Returns:
        A confirmation message.
    """
    decision = PERMISSIONS.check_path(path, "write")
    if decision.risk == RiskLevel.BLOCKED:
        raise SecurityError(decision.reason)
    if not PERMISSIONS.confirm(decision):
        raise SecurityError("user denied file write")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {path}"


def str_replace(
    path: str,
    old_str: str,
    new_str: str,
    line_number: int | None = None,
) -> str:
    """Replace old_str with new_str in a file.

    Args:
        path: The path to the file to edit.
        old_str: The string to replace.
        new_str: The string to insert in its place.
        line_number: Optional line number to scope the replacement.

    Returns:
        A confirmation or error message.
    """
    decision = PERMISSIONS.check_path(path, "edit")
    if decision.risk == RiskLevel.BLOCKED:
        raise SecurityError(decision.reason)
    if not PERMISSIONS.confirm(decision):
        raise SecurityError("user denied file edit")

    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    if line_number is not None:
        if not (0 <= line_number < len(lines)):
            return f"Error: line_number {line_number} is out of range for {path}"

        line = lines[line_number]
        count = line.count(old_str)
        if count == 0:
            return f"Error: old_str was not found on line {line_number} in {path}"
        if count > 1:
            return (
                f"Error: old_str matches {count} times on line {line_number} in {path}. "
                "Add surrounding context to make it unique."
            )

        lines[line_number] = line.replace(old_str, new_str, 1)
    else:
        content = "".join(lines)
        count = content.count(old_str)
        if count == 0:
            return f"Error: old_str was not found in {path}"
        if count > 1:
            return (
                f"Error: old_str matches {count} times in {path}. "
                "Add line_number or surrounding context to make it unique."
            )

        lines = content.replace(old_str, new_str, 1).splitlines(keepends=True)

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return f"Replaced {count} match(es) in {path}"


# Register tools here in the order they should be exposed to the model.
_TOOL_FUNCTIONS: Sequence[Callable[..., str]] = [
    bash,
    read_file,
    read_skill,
    write_file,
    str_replace,
    write_todos,
]

OLLAMA_TOOLS: Sequence[OllamaTool] = [
    convert_function_to_tool(func) for func in _TOOL_FUNCTIONS
]

# Tool dispatch must preserve the order in which OLLAMA_TOOLS is defined.
TOOLS: dict[str, Callable[..., str]] = {}
for func in _TOOL_FUNCTIONS:
    TOOLS[func.__name__] = func
