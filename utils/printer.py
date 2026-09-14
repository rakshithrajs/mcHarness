import json
from typing import Any

from rich.box import DOUBLE, ROUNDED
from rich.console import Console
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def agent_message(content: str, turn: int = 0) -> None:
    """Render the agent's response in a styled panel."""
    title = f"Agent — Turn {turn}" if turn else "Agent"
    panel = Panel(
        renderable=Markdown(content),
        title=title,
        title_align="left",
        border_style="green",
        box=ROUNDED,
    )
    console.print(panel)


def tool_call(name: str, args: dict[str, Any], turn: int = 0) -> None:
    """Render a tool invocation with its name and arguments."""
    title = f"Tool Call — Turn {turn}" if turn else "Tool Call"
    args_text = json.dumps(args, indent=2, ensure_ascii=False)
    panel = Panel(
        renderable=Markdown(f"**{name}**\n\n```json\n{args_text}\n```"),
        title=title,
        title_align="left",
        border_style="yellow",
        box=ROUNDED,
    )
    console.print(panel)


def tool_result(result: str) -> None:
    """Render a tool's returned output, code-blocked if multi-line."""
    result = result.strip()
    if "\n" in result:
        content = f"```text\n{result}\n```"
    else:
        content = f"`{result}`"
    panel = Panel(
        renderable=Markdown(content),
        title="Tool Result",
        title_align="left",
        border_style="cyan",
        box=ROUNDED,
    )
    console.print(panel)


def security_block(name: str, args: dict[str, Any], reason: str) -> None:
    """Render a security rejection for a tool call."""
    args_text = json.dumps(args, indent=2, ensure_ascii=False)
    content = f"**{name}** was blocked.\n\nReason: `{reason}`\n\nArguments:\n```json\n{args_text}\n```"
    panel = Panel(
        renderable=Markdown(content),
        title="Security Block",
        title_align="left",
        border_style="red",
        box=ROUNDED,
    )
    console.print(panel)


def usage_stats(usage: dict[str, Any]) -> None:
    """Render token usage as a compact table."""
    table = Table(
        title="Token Usage",
        box=ROUNDED,
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")

    for key, value in usage.items():
        label = key.replace("_", " ").title()
        table.add_row(label, str(value))

    console.print(table)


def models_table(models: list[Any]) -> None:
    """Render a list of available models as a table."""
    table = Table(
        title="Available Models",
        box=ROUNDED,
        show_header=True,
        header_style="bold blue",
    )
    table.add_column("ID", style="green", no_wrap=True)
    table.add_column("Created", style="white")
    table.add_column("Owned By", style="cyan")

    for model in models:
        created = getattr(model, "created", "—")
        owned_by = getattr(model, "owned_by", "—")
        table.add_row(str(model.id), str(created), str(owned_by))

    console.print(table)


def section(title: str) -> None:
    """Render a full-width section heading."""
    console.print(Panel(title, box=DOUBLE, style="bold white on blue", expand=True))


def status(message: str) -> None:
    """Render a dim status/info line."""
    console.print(f"{message}", style="dim")


def error(message: str) -> None:
    """Render an error in a red panel."""
    panel = Panel(
        renderable=Text(message, style="bold red"),
        title="Error",
        title_align="left",
        border_style="red",
        box=ROUNDED,
    )
    console.print(panel)


def raw_json(data: Any) -> None:
    """Render any JSON-serializable object with syntax highlighting."""
    console.print(JSON.from_data(data))


def debug(data: Any) -> None:
    """Render debug lines"""
    console.log(data)
