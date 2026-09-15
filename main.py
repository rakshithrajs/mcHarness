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


def main() -> None:
    """Run the harness agent."""
    agent = BaseAgent(
        Options(
            system_prompt=SYSTEM_PROMPT,
            tools=tools.OLLAMA_TOOLS,
        ),
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

    printer.status("Done")


if __name__ == "__main__":
    main()
