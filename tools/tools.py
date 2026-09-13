import subprocess
from typing import Iterable
from openai.types.chat import ChatCompletionToolParam

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
]


def bash(command: str):
    """Run a shell command and return its combined stdout and stderr."""
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        executable=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    )
    return result.stdout + result.stderr


def read_file(path: str) -> str:
    """read a file and return its contents."""
    with open(path) as f:
        return f.read()
