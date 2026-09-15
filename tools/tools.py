"""Tools for interacting with the system."""

import subprocess
from collections.abc import Callable, Iterable

from openai.types.chat import ChatCompletionToolParam

from context import context
from security import PermissionManager, SecurityError
from security.permissions import RiskLevel
from skills.skills import read_skill
from tools.todos import write_todos

PERMISSIONS = PermissionManager.from_environment()

TOOL_SCHEMAS: Iterable[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a powershell command and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The powershell command to run.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "this tool reads a file and returns its contents when provided with the file path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "the path to the file that you want to read the contents off.",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_skill",
            "description": "Open a skill by name and return its full instructions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "name of the skill to open",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "This tool is used to create a new a file or overwrite"
                "an existing file with completely new contnent"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "path of the file to create or overwrite",
                    },
                    "content": {
                        "type": "string",
                        "description": "It contains the content of the file to written.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "str_replace",
            "description": "This tool is used to edit the content of a file",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "path of the file to create or overwrite",
                    },
                    "old_str": {
                        "type": "string",
                        "description": "old_str is the string that has to be replaced in the file.",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "new_str is the string that will replace the old_str in the file.",
                    },
                    "line_number": {
                        "type": "integer",
                        "description": (
                            "Optional line number to scope the replacement to. "
                            "Use only when old_str appears on multiple lines."
                        ),
                    },
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_todos",
            "description": (
                "Record the plan for a multi-step task. Send the whole list every "
                "time. Keep exactly one task in_progress and update it as you go."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "The task, imperative: 'Fix the parser'",
                                },
                                "activeForm": {
                                    "type": "string",
                                    "description": "Present continuous: 'Fixing the parser'",
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "done"],
                                },
                            },
                            "required": ["content", "activeForm", "status"],
                        },
                    },
                },
                "required": ["todos"],
            },
        },
    },
]


def bash(command: str) -> str:
    """Run a shell command and return its combined stdout and stderr."""
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
    """Read a file and return its contents."""
    decision = PERMISSIONS.check_path(path, "read")
    if decision.risk == RiskLevel.BLOCKED:
        raise SecurityError(decision.reason)
    if not PERMISSIONS.confirm(decision):
        raise SecurityError("user denied file read")

    context.note_read(path)
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    """Create a file, or overwrite it if already exists."""
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

    If line_number is provided, the match is scoped to that line.
    Otherwise old_str must be unique in the entire file.
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


# The argument name differs between tools (`command` vs. `path`), and the
# dispatcher invokes each tool with keyword arguments unpacked from JSON.
# in the list on line 84 always preserve the order in which the TOOL_SCHEMA is defined.
TOOLS: dict[str, Callable[..., str]] = {
    schema["function"]["name"]: func
    for schema, func in zip(
        TOOL_SCHEMAS,
        [bash, read_file, read_skill, write_file, str_replace, write_todos],
        strict=True,
    )
}
