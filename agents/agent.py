import json
from typing import cast

from openai.types.chat import ChatCompletionMessageParam

from context import context
from llm.llm import SYSTEM_PROMPT, call_llm
from security import SecurityError
from tools.tools import PERMISSIONS, TOOLS
from utils.printer import (
    TodoFooter,
    _agent_message_panel,
    _security_block_panel,
    _tool_call_panel,
    _tool_result_panel,
)
import utils.printer as printer


def run_agent() -> None:
    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    with TodoFooter() as footer:
        PERMISSIONS.set_prompt_hooks(footer.pause, footer.resume)

        while True:
            footer.pause()
            try:
                user_input = input("Enter your prompt> ").strip()
            finally:
                footer.resume()

            if not user_input or user_input.lower() in ("/quit", "/exit"):
                break

            messages.append({"role": "user", "content": user_input})

            turn = 0
            while True:
                turn += 1
                message, usage = call_llm(
                    messages + [cast(ChatCompletionMessageParam, context.reminder())]
                )
                messages.append(
                    cast(ChatCompletionMessageParam, message.model_dump(exclude_none=True))
                )

                content = message.content
                if content and content.strip():
                    footer.show(_agent_message_panel(content.strip(), turn=turn))

                if not message.tool_calls:
                    printer.usage_stats(usage)
                    break

                for i in message.tool_calls:
                    if i.type == "function":
                        function_name = i.function.name
                        function_arguments = json.loads(i.function.arguments)
                        function = TOOLS[function_name]
                        try:
                            result = function(**function_arguments)
                        except SecurityError as e:
                            result = f"SecurityError: {e.reason}"
                            footer.show(
                                _security_block_panel(
                                    function_name, function_arguments, str(e.reason)
                                )
                            )
                        except Exception as e:
                            result = f"Error: {type(e).__name__}: {e}"

                        footer.show(_tool_call_panel(function_name, function_arguments, turn=turn))
                        footer.show(_tool_result_panel(result))

                        messages.append(
                            {"role": "tool", "tool_call_id": i.id, "content": result}
                        )

                printer.usage_stats(usage)

    printer.status("Done")


if __name__ == "__main__":
    run_agent()
