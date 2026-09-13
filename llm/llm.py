import os
import json
import dotenv
from openai import OpenAI

import tools.tools as tools

dotenv.load_dotenv()

client = OpenAI(base_url=os.getenv("OLLAMA_HOST"), api_key=os.getenv("OLLAMA_API_KEY"))


def run_agent():
    user_input = input("Enter your prompt: ")

    SYSTEM_PROMPT = """
    You are a coding agent. Your job is to code, always code.
    Use the bash tool to inspect files.
    Anser back to the user once exploration is done.
    """

    response = client.chat.completions.create(
        model=os.environ.get("OLLAMA_LANG_MODEL", default="glm-5.1:cloud"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        tools=tools.TOOL_SCHEMAS,
    )

    message = response.choices[0].message
    output = message.content

    completetion_details = getattr(response.usage, "completion_tokens_details", None)
    prompt_details = getattr(response.usage, "prompt_tokens_details", None)

    usage = {
        "prompt_token_details": prompt_details,
        "prompt_tokens": getattr(response.usage, "prompt_tokens", None),
        "completion_tokens": getattr(response.usage, "completion_tokens", None),
        "reasoning_tokens": getattr(completetion_details, "reasoning_tokens", None),
        "cached_tokens": getattr(completetion_details, "cached_tokens", None),
    }
    print("\nAgent: ", output, "\n")

    if message.tool_calls:
        for i in message.tool_calls:
            if i.type == "function":
                function_name = i.function.name
                function_arguments = json.loads(i.function.arguments)
                function = getattr(tools, function_name)
                print(
                    f"Function tool: {function_name}; parameters: {function_arguments}"
                )
                print(function(**function_arguments), "\n")

    print(usage)


if __name__ == "__main__":
    run_agent()
