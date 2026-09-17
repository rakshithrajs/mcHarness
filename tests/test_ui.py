"""Tests for the Textual TUI."""

from unittest.mock import AsyncMock, patch

import pytest

from ui.app import HarnessApp, ToolCallMessage, ToolResultMessage


def mock_response(content: str) -> AsyncMock:
    """Build a minimal mock response object."""
    response = AsyncMock()
    response.message.content = content
    response.message.tool_calls = []
    return response


@pytest.fixture
def app() -> HarnessApp:
    """Create a fresh HarnessApp with the agent and permissions mocked."""
    with (
        patch("ui.app.BaseAgent") as mock_agent_class,
        patch("ui.app.tools.PERMISSIONS") as _mock_perms,
    ):
        instance = mock_agent_class.return_value
        instance.options.model = "test-model"
        instance.run_turn_async = AsyncMock(return_value=mock_response("Hello!"))
        yield HarnessApp()


@pytest.mark.anyio
async def test_app_mounts_widgets(app: HarnessApp) -> None:
    """The app should mount all expected widgets."""
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one("#user-input") is not None
        assert app.query_one("#chat-scroll") is not None
        assert app.query_one("#todo-list") is not None
        assert app.query_one("#status") is not None


@pytest.mark.anyio
async def test_user_message_appears_after_submit(app: HarnessApp) -> None:
    """Submitting input should render the user message in chat."""
    async with app.run_test() as pilot:
        await pilot.pause()
        input_widget = app.query_one("#user-input")
        input_widget.value = "say hello"
        await pilot.press("enter")
        await pilot.pause()

        chat = app.query_one("#chat-scroll")
        contents = [str(child.content) for child in chat.children]
        assert any("say hello" in c for c in contents)


@pytest.mark.anyio
async def test_agent_response_renders(app: HarnessApp) -> None:
    """After the worker finishes, the agent response should appear."""
    async with app.run_test() as pilot:
        await pilot.pause()
        input_widget = app.query_one("#user-input")
        input_widget.value = "hi"
        await pilot.press("enter")

        # Wait for the async worker to complete and UI updates to settle.
        await pilot.pause()
        await pilot.pause()

        chat = app.query_one("#chat-scroll")
        assert len(chat.children) == 2  # noqa: PLR2004
        assert "Agent" in chat.children[1].content
        assert "Hello!" in chat.children[1].content


@pytest.mark.anyio
async def test_tool_call_renders_inline_collapsible(app: HarnessApp) -> None:
    """Tool calls should appear as collapsible widgets inside the chat area."""
    async with app.run_test() as pilot:
        await pilot.pause()
        app.on_tool_call_message(ToolCallMessage("bash", {"command": "git status"}))
        app.on_tool_result_message(ToolResultMessage("On branch main"))
        await pilot.pause()

        chat = app.query_one("#chat-scroll")
        # The chat should contain exactly one collapsible tool widget.
        assert len(chat.children) == 1
        collapsible = chat.children[0]
        assert "bash" in collapsible.title
        contents = "\n".join(str(child.content) for child in collapsible.query("Static"))
        assert "git status" in contents
        assert "On branch main" in contents
