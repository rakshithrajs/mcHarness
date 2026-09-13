import os
import dotenv
from typing import Iterable

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from openai.types.chat.chat_completion_message import ChatCompletionMessage

import tools.tools as tools

dotenv.load_dotenv()

client = OpenAI(base_url=os.getenv("OLLAMA_HOST"), api_key=os.getenv("OLLAMA_API_KEY"))

SYSTEM_PROMPT = f"""
You are a coding agent. Your job is to code, always code.
Use the bash tool to inspect files.
Answer back to the user once exploration is done.

Your current working directory is: {os.getcwd()}
"""


def call_llm(
    messages: Iterable[ChatCompletionMessageParam],
) -> tuple[ChatCompletionMessage, dict[str, str | None]]:
    response = client.chat.completions.create(
        model=os.environ.get("OLLAMA_LANG_MODEL", default="glm-5.1:cloud"),
        messages=messages,
        tools=tools.TOOL_SCHEMAS,
    )

    message = response.choices[0].message

    completetion_details = getattr(response.usage, "completion_tokens_details", None)
    prompt_details = getattr(response.usage, "prompt_tokens_details", None)

    usage = {
        "prompt_token_details": prompt_details,
        "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
        "completion_tokens": getattr(response.usage, "completion_tokens", None),
        "reasoning_tokens": getattr(completetion_details, "reasoning_tokens", None),
        "cached_tokens": getattr(completetion_details, "cached_tokens", None),
    }
    return message, usage


if __name__ == "__main__":
    call_llm(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "hi how are you"},
        ]
    )
