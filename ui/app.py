"""Textual application for the harness coding agent."""

from __future__ import annotations

import contextlib
import json
from typing import Any, ClassVar

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from context import context
from llm.llm import SYSTEM_PROMPT, BaseAgent, Options
from security.permissions import SecurityDecision
from tools import tools
from tools.todos import TODOS
from ui.confirm import ConfirmDialog

_MAX_TOOL_RESULT_SNIPPET = 400


class AgentFinished(Message):
    """Posted when an agent turn completes."""

    def __init__(self, content: str) -> None:
        """Store the final assistant content."""
        self.content = content
        super().__init__()


class ToolCallMessage(Message):
    """Posted when the agent invokes a tool."""

    def __init__(self, name: str, arguments: dict[str, Any]) -> None:
        """Store tool name and arguments."""
        self.name = name
        self.arguments = arguments
        super().__init__()


class ToolResultMessage(Message):
    """Posted when a tool returns a result."""

    def __init__(self, result: str) -> None:
        """Store the tool result."""
        self.result = result
        super().__init__()


class HarnessApp(App):
    """Terminal UI for running the harness agent."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        layout: horizontal;
        height: 1fr;
    }
    #todos {
        width: 1fr;
        min-width: 18;
        max-width: 28;
        height: 1fr;
        border: solid $primary 60%;
    }
    #todos-title {
        height: 1;
        content-align: center middle;
        text-style: bold;
        background: $surface;
    }
    #chat-scroll {
        width: 1fr;
        min-width: 40;
        height: 1fr;
        border: solid $primary 60%;
    }
    #user-input {
        height: 3;
        border: solid $primary;
    }
    #status {
        height: 1;
        content-align: center middle;
        color: $text-muted;
        background: $surface;
    }
    .user-message {
        margin: 0 1 1 1;
        padding: 0 1 0 1;
        text-style: bold;
        color: $text;
        border-left: outer $accent;
    }
    .agent-message {
        margin: 0 1 1 1;
        padding: 0 1 0 1;
        color: $text;
        border-left: outer $success;
    }
    .tool-call {
        margin: 0 2 1 2;
        height: auto;
    }
    .tool-call Static {
        padding: 0 1 0 1;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+r", "reset", "Reset"),
        ("ctrl+l", "clear", "Clear"),
    ]

    status_text: reactive[str] = reactive("ready")
    _turn: reactive[int] = reactive(0)

    def __init__(self, **kwargs: Any) -> None:
        """Create the app and the underlying agent."""
        super().__init__(**kwargs)
        self._agent_busy = False
        self._pending_tool_collapsible: Collapsible | None = None
        self._setup_permission_sender()
        self.agent = BaseAgent(
            Options(
                system_prompt=SYSTEM_PROMPT,
                tools=tools.OLLAMA_TOOLS,
            ),
            on_tool_call=self._on_tool_call,
            on_tool_result=self._on_tool_result,
        )

    def _setup_permission_sender(self) -> None:
        """Wire the permission manager to show modal dialogs on the main thread."""

        def sender(decision: SecurityDecision) -> None:
            self.call_from_thread(self._show_confirm, decision)

        tools.PERMISSIONS.set_tui_confirm_sender(sender)

    def compose(self) -> ComposeResult:
        """Build the widget tree."""
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            with Vertical(id="todos"):
                yield Static("Todos", id="todos-title")
                yield ListView(id="todo-list")
            yield VerticalScroll(id="chat-scroll")
        yield Input(placeholder="Enter your prompt…", id="user-input")
        yield Static(self.status_text, id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize UI state after the app is mounted."""
        self.query_one("#user-input", Input).focus()
        self.status_text = (
            f"model: {self.agent.options.model} | "
            f"branch: {context.git_branch()} | ready"
        )
        self._refresh_todos()

    def action_reset(self) -> None:
        """Reset the agent conversation history."""
        self.agent.reset()
        self._clear_chat()
        self._turn = 0
        self._pending_tool_collapsible = None
        self.status_text = (
            f"model: {self.agent.options.model} | "
            f"branch: {context.git_branch()} | reset"
        )

    def action_clear(self) -> None:
        """Clear the chat history only."""
        self._clear_chat()
        self._pending_tool_collapsible = None

    def _clear_chat(self) -> None:
        """Remove all messages from the chat scroll area."""
        chat = self.query_one("#chat-scroll", VerticalScroll)
        chat.remove_children()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the user submitting a prompt."""
        if self._agent_busy or not event.value.strip():
            return

        user_text = event.value.strip()
        input_widget = self.query_one("#user-input", Input)
        input_widget.value = ""
        input_widget.disabled = True
        self._agent_busy = True
        self._turn += 1
        self._pending_tool_collapsible = None

        self._append_user_message(user_text)
        self.status_text = (
            f"model: {self.agent.options.model} | "
            f"branch: {context.git_branch()} | thinking…"
        )
        self.run_worker(self._run_agent_turn(user_text), exclusive=True)

    async def _run_agent_turn(self, user_input: str) -> None:
        """Run the agent turn in a worker and post the result back to the UI."""
        try:
            response = await self.agent.run_turn_async(user_input)
            content = response.message.content or ""
        except Exception as exc:
            content = f"Error: {type(exc).__name__}: {exc}"
        finally:
            self._agent_busy = False

        self.post_message(AgentFinished(content))

    def on_agent_finished(self, message: AgentFinished) -> None:
        """Render the agent response and restore the input box."""
        self._append_agent_message(message.content)
        self._refresh_todos()
        input_widget = self.query_one("#user-input", Input)
        input_widget.disabled = False
        input_widget.focus()
        self.status_text = (
            f"model: {self.agent.options.model} | "
            f"branch: {context.git_branch()} | ready"
        )

    def _append_user_message(self, content: str) -> None:
        """Add a user message bubble to the chat."""
        chat = self.query_one("#chat-scroll", VerticalScroll)
        chat.mount(
            Static(
                f"[b]You[/b] (turn {self._turn})\n{content}",
                classes="user-message",
            ),
        )
        chat.scroll_end(animate=False)

    def _append_agent_message(self, content: str) -> None:
        """Add an agent message bubble to the chat."""
        chat = self.query_one("#chat-scroll", VerticalScroll)
        chat.mount(
            Static(
                f"[b]Agent[/b] (turn {self._turn})\n{content}",
                classes="agent-message",
            ),
        )
        chat.scroll_end(animate=False)

    def _on_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        """Post a tool invocation to the UI thread."""
        self.post_message(ToolCallMessage(name, arguments))

    def _on_tool_result(self, result: str) -> None:
        """Post a tool result to the UI thread."""
        self.post_message(ToolResultMessage(result))

    def on_tool_call_message(self, message: ToolCallMessage) -> None:
        """Render a tool call as an inline collapsible in the chat."""
        args_text = json.dumps(message.arguments, indent=2, ensure_ascii=False)
        body = Static(f"[b]Arguments[/b]\n[dim]{args_text}[/dim]", markup=True)
        collapsible = Collapsible(
            body,
            title=f"🛠 {message.name}",
            collapsed=True,
            classes="tool-call",
        )
        self._pending_tool_collapsible = collapsible
        chat = self.query_one("#chat-scroll", VerticalScroll)
        chat.mount(collapsible)
        chat.scroll_end(animate=False)

    def on_tool_result_message(self, message: ToolResultMessage) -> None:
        """Append the tool result to the current tool call collapsible."""
        result = message.result
        snippet = (
            result
            if len(result) < _MAX_TOOL_RESULT_SNIPPET
            else result[:_MAX_TOOL_RESULT_SNIPPET] + "\n…"
        )
        body = Static(f"[b]Result[/b]\n{snippet}", markup=True)
        if self._pending_tool_collapsible is not None:
            self._pending_tool_collapsible.mount(body)
        else:
            collapsible = Collapsible(
                body,
                title="🛠 result",
                collapsed=True,
                classes="tool-call",
            )
            chat = self.query_one("#chat-scroll", VerticalScroll)
            chat.mount(collapsible)
            chat.scroll_end(animate=False)

    def _show_confirm(self, decision: SecurityDecision) -> None:
        """Push the security confirmation modal and forward its result."""
        self.push_screen(ConfirmDialog(decision), callback=self._on_confirm_done)

    def _on_confirm_done(self, result: bool | str) -> None:
        """Resolve the pending TUI confirmation with the modal result."""
        tools.PERMISSIONS.resolve_tui_confirm(result)

    def _refresh_todos(self) -> None:
        """Synchronize the left sidebar with the global todo list."""
        todo_list = self.query_one("#todo-list", ListView)
        todo_list.clear()
        if not TODOS:
            todo_list.append(ListItem(Label("No active todos")))
            return
        for todo in TODOS:
            status = todo.get("status", "pending")
            content = str(
                todo.get("content")
                or todo.get("task")
                or todo.get("title")
                or todo.get("description")
                or "untitled",
            )
            marker = {"pending": "[ ]", "in_progress": "[-]", "done": "[x]"}.get(
                status,
                "[?]",
            )
            style = (
                "dim strike"
                if status == "done"
                else "bold yellow" if status == "in_progress" else ""
            )
            todo_list.append(
                ListItem(Label(f"{marker} {content}", classes=style)),
            )

    def watch_status_text(self, status_text: str) -> None:
        """Reactive watch handler that updates the status Static."""
        with contextlib.suppress(NoMatches):
            self.query_one("#status", Static).update(status_text)


def run() -> None:
    """Run the Textual UI."""
    app = HarnessApp()
    app.run()
