import json
from typing import Any

from rich.box import DOUBLE, ROUNDED
from rich.console import Console, Group, RenderableType
from rich.json import JSON
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def _agent_message_panel(content: str, turn: int = 0) -> Panel:
    """Build the agent response panel."""
    title = f"Agent - Turn {turn}" if turn else "Agent"
    return Panel(
        renderable=Markdown(content),
        title=title,
        title_align="left",
        border_style="green",
        box=ROUNDED,
    )


def agent_message(content: str, turn: int = 0) -> None:
    """Render the agent's response in a styled panel."""
    console.print(_agent_message_panel(content, turn))


def _tool_call_panel(name: str, args: dict[str, Any], turn: int = 0) -> Panel:
    """Build the tool call panel."""
    title = f"Tool Call - Turn {turn}" if turn else "Tool Call"
    args_text = json.dumps(args, indent=2, ensure_ascii=False)
    return Panel(
        renderable=Markdown(f"**{name}**\n\n```json\n{args_text}\n```"),
        title=title,
        title_align="left",
        border_style="yellow",
        box=ROUNDED,
    )


def tool_call(name: str, args: dict[str, Any], turn: int = 0) -> None:
    """Render a tool invocation with its name and arguments."""
    console.print(_tool_call_panel(name, args, turn))


def _tool_result_panel(result: str) -> Panel | None:
    """Build the tool result panel, or skip if there is nothing to show."""
    result = result.strip()
    if not result:
        return None
    if "\n" in result:
        content = f"```text\n{result}\n```"
    else:
        content = f"`{result}`"
    return Panel(
        renderable=Markdown(content),
        title="Tool Result",
        title_align="left",
        border_style="cyan",
        box=ROUNDED,
    )


def tool_result(result: str) -> None:
    """Render a tool's returned output, code-blocked if multi-line."""
    panel = _tool_result_panel(result)
    if panel:
        console.print(panel)


def _security_block_panel(name: str, args: dict[str, Any], reason: str) -> Panel:
    """Build a security rejection panel."""
    args_text = json.dumps(args, indent=2, ensure_ascii=False)
    content = f"**{name}** was blocked.\n\nReason: `{reason}`\n\nArguments:\n```json\n{args_text}\n```"
    return Panel(
        renderable=Markdown(content),
        title="Security Block",
        title_align="left",
        border_style="red",
        box=ROUNDED,
    )


def security_block(name: str, args: dict[str, Any], reason: str) -> None:
    """Render a security rejection for a tool call."""
    console.print(_security_block_panel(name, args, reason))


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


# ---------------------------------------------------------------------------
# Live todo footer (simple Claude Code-style sticky footer)
# ---------------------------------------------------------------------------


class TodoFooter:
    """Render a sticky todo footer at the bottom of the terminal."""

    def __init__(self, screen: bool = False) -> None:
        self.screen = screen
        self._live: Live | None = None
        self._main: RenderableType = Text("")

    def __enter__(self) -> "TodoFooter":
        self._live = Live(
            self._render(),
            console=console,
            refresh_per_second=2,
            screen=self.screen,
            vertical_overflow="visible",
        )
        self._live.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._live:
            self._live.stop()
            self._live = None

    def pause(self) -> None:
        """Stop live updates for interactive prompts."""
        if self._live:
            self._live.stop()

    def resume(self) -> None:
        """Resume live updates after interactive prompts."""
        if self._live:
            self._live.start()

    def show(self, renderable: RenderableType | None) -> None:
        """Update the main panel above the footer."""
        if renderable is None:
            return
        self._main = renderable
        self._refresh()

    def _build_footer(self) -> Panel | None:
        from tools.todos import TODOS

        if not TODOS:
            return None

        lines: list[RenderableType] = []
        all_done = all(t["status"] == "done" for t in TODOS)

        for todo in TODOS:
            status = todo["status"]
            marker = {"pending": "[ ]", "in_progress": "[-]", "done": "[x]"}.get(
                status, "[?]"
            )
            text = f"{marker} {todo['content']}"
            if status == "done":
                lines.append(Text(text, style="dim strike"))
            elif status == "in_progress":
                lines.append(Text(text, style="bold yellow"))
            else:
                lines.append(Text(text))

        if all_done:
            lines.insert(0, Text("All tasks complete", style="bold green"))

        height = min(2 + len(lines), 12)
        return Panel(
            Group(*lines),
            title="Todos",
            title_align="left",
            border_style="blue",
            box=ROUNDED,
            height=height,
        )

    def _render(self) -> RenderableType:
        footer = self._build_footer()
        if footer is None:
            return self._main
        return Group(self._main, footer)

    def _refresh(self) -> None:
        if self._live:
            self._live.update(self._render())
