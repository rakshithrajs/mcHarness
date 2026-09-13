import subprocess
from typing import Callable, Iterable
from openai.types.chat import ChatCompletionToolParam
from skills.skills import read_skill

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
                    }
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
                    }
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
                    }
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "This tool is used to create a new a file or overwrite an existing file with completely new contnent",
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
                    "allow_multi_edit": {
                        "type": "boolean",
                        "default": "false",
                        "description": "allow_multi_edit is a flag that will allow to edit multiple occurences of the same old_str.",
                    },
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
]


def bash(command: str):
    """Run a shell command and return its combined stdout and stderr."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        executable=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    )
    return (result.stdout or "") + (result.stderr or "")


def read_file(path: str) -> str:
    """read a file and return its contents."""
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    """Create a file, or overwrite it if already exists."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Wrote {path}"


def str_replace(path: str, old_str: str, new_str: str, allow_multi_edit: bool = False):
    """Swap exact text in a file. old_str must match exactly once."""
    with open(path, "w", encoding="utf-8") as f:
        content = f.read()

    count = content.count(old_str)
    if count == 0:
        return f"Error: old_str want not found in {path}"
    if count > 1 and not allow_multi_edit:
        return (
            f"Error: old_str matches {count} time in {path}."
            "Add surrounding lines to make it unique."
            "or set allow_multi_edit to replace them all."
        )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content.replace(old_str, new_str))
    return f"Replaced {count} match(es) in {path}"


# The argument name differs between tools (`command` vs. `path`), and the
# dispatcher invokes each tool with keyword arguments unpacked from JSON.
# in the list on line 84 always preserve the order in which the TOOL_SCHEMA is defined.
TOOLS: dict[str, Callable[..., str]] = {
    schema["function"]["name"]: func
    for schema, func in zip(
        TOOL_SCHEMAS, [bash, read_file, read_skill, write_file, str_replace]
    )
}
