import json
from typing import cast

from openai.types.chat import ChatCompletionMessageParam

from context import context
from llm.llm import SYSTEM_PROMPT, call_llm
from security import SecurityError
from tools.tools import TOOLS
import utils.printer as printer


def run_agent() -> None:
    user_input = input("Enter your prompt> ")

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]

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
        if content:
            printer.agent_message(content, turn=turn)

        if not message.tool_calls:
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
                    printer.security_block(function_name, function_arguments, str(e.reason))
                except Exception as e:
                    result = f"Error: {type(e).__name__}: {e}"

                printer.tool_call(function_name, function_arguments, turn=turn)
                printer.tool_result(result)

                messages.append(
                    {"role": "tool", "tool_call_id": i.id, "content": result}
                )

        printer.usage_stats(usage)

    printer.status("Done")


if __name__ == "__main__":
    run_agent()
