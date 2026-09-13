import subprocess

BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "Run a shell command and return its output.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run.",
                }
            },
            "required": ["command"],
        },
    },
}


def bash(command):
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        executable=r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    )
    return result.stdout + result.stderr
