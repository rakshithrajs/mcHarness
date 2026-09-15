"""Tools for managing a list of todos."""

from typing import Literal

MARKS = {"pending": "[]", "in_progress": "[-]", "done": "[x]"}
TODOS: list[dict[str, str | Literal["pending", "in_progress", "done"]]] = []


def write_todos(
    todos: list[dict[str, str | Literal["pending", "in_progress", "done"]]],
) -> str:
    """
    Record the plan for a multi-step task.
    Send the whole list every time. Keep exactly one task in_progress and update it as you go.
    """

    active = [t for t in todos if t["status"] == "in_progress"]
    if len(active) > 1:
        return f"Error: {len(active)} tasks are in progress. Only 1 task is allowed to be active at once."

    TODOS[:] = todos
    return todo_prompt() or "Todo list cleared"


def todo_prompt() -> str:
    """Return a string representation of the current todo list."""
    return "\n".join(f"{MARKS[t['status']]} {t['content']}" for t in TODOS)


def active_form() -> str:
    """Return the active form of the task that is currently in progress."""
    for todo in TODOS:
        if todo["status"] == "in_progress":
            return todo["activeForm"]
    return "thinking"
