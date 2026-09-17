"""Main entry point for the harness agent."""

import io
import sys

# Windows terminals default to cp1252; force UTF-8 so Rich can render emoji/box chars.
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from llm.llm import SYSTEM_PROMPT, BaseAgent, Options
from tools import tools
from utils import printer
from utils.printer import TodoFooter


def _print_tool_call(name: str, args: dict[str, object]) -> None:
    """Print a tool invocation to the console."""
    printer.tool_call(name, args)


def _print_tool_result(result: str) -> None:
    """Print a tool result to the console."""
    printer.tool_result(result)


def main() -> None:
    """Run the harness agent."""
    agent = BaseAgent(
        Options(
            system_prompt=SYSTEM_PROMPT,
            tools=tools.OLLAMA_TOOLS,
        ),
        on_tool_call=_print_tool_call,
        on_tool_result=_print_tool_result,
    )

    with TodoFooter() as footer:
        while True:
            footer.pause()
            try:
                user_input = input("Enter your prompt> ").strip()
            finally:
                footer.resume()

            if not user_input or user_input.lower() in ("/quit", "/exit"):
                break

            response = agent.run_turn(user_input)
            content = response.message.content
            if content:
                printer.agent_message(content.strip())
            else:
                printer.agent_message("(agent returned no content)")

    printer.status("Done")


if __name__ == "__main__":
    main()
