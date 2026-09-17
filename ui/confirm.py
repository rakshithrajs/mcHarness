"""Security confirmation modal for the TUI."""

from textual.app import ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from security.permissions import SecurityDecision


class ConfirmDialog(ModalScreen[bool | str]):
    """Modal screen that asks the user to allow, block, or always allow a security decision."""

    CSS = """
    ConfirmDialog {
        align: center middle;
    }
    ConfirmDialog > Grid {
        grid-size: 3;
        grid-gutter: 1;
        padding: 1;
        width: 70;
        height: auto;
        border: thick $background 80%;
        background: $surface;
    }
    ConfirmDialog > Grid > Static {
        column-span: 3;
        width: 1fr;
        height: auto;
    }
    ConfirmDialog > Grid > Label {
        column-span: 3;
        width: 1fr;
        content-align: left top;
        text-style: bold;
    }
    ConfirmDialog > Grid > Button {
        width: 1fr;
    }
    """

    def __init__(self, decision: SecurityDecision) -> None:
        """Initialize with the decision to present."""
        super().__init__()
        self.decision = decision

    def compose(self) -> ComposeResult:
        """Build the dialog widgets."""
        lines = [
            "The agent wants to perform a high-risk action:",
            "",
        ]
        if self.decision.command:
            lines.append(f"Command: {self.decision.command}")
        if self.decision.path:
            lines.append(f"Path:    {self.decision.path}")
        lines.append(f"Reason:  {self.decision.reason}")

        with Grid():
            yield Label("Security Confirmation")
            yield Static("\n".join(lines))
            yield Button("Allow", id="allow", variant="success")
            yield Button("Always", id="always", variant="primary")
            yield Button("Block", id="block", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Return the user's choice and dismiss the dialog."""
        mapping = {
            "allow": True,
            "always": "always",
            "block": "block",
        }
        self.dismiss(mapping.get(event.button.id, False))
