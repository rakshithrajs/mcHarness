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
                    "line_number": {
                        "type": "integer",
                        "description": "line_number specifies the the number of the line that you want to edit in the file.",
                    },
                },
                "required": ["path", "old_str", "new_str", "line_number"],
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


def str_replace(
    path: str,
    old_str: str,
    new_str: str,
    line_number: int,
):
    """Replace old_str with new_str on a specific line of a file."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content_lines = content.splitlines(keepends=True)
    if not (0 <= line_number < len(content_lines)):
        return f"Error: line_number {line_number} is out of range for {path}"

    line = content_lines[line_number]
    count = line.count(old_str)
    if count == 0:
        return f"Error: old_str was not found on line {line_number} in {path}"
    if count > 1:
        return (
            f"Error: old_str matches {count} times on line {line_number} in {path}. "
            "Add surrounding context to make it unique."
        )

    content_lines[line_number] = line.replace(old_str, new_str)

    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(content_lines))
    return f"Replaced {count} match(es) on line {line_number} in {path}"


# The argument name differs between tools (`command` vs. `path`), and the
# dispatcher invokes each tool with keyword arguments unpacked from JSON.
# in the list on line 84 always preserve the order in which the TOOL_SCHEMA is defined.
TOOLS: dict[str, Callable[..., str]] = {
    schema["function"]["name"]: func
    for schema, func in zip(
        TOOL_SCHEMAS, [bash, read_file, read_skill, write_file, str_replace]
    )
}
