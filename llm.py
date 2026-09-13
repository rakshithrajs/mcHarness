import os
import json
import dotenv

import tools

from openai import OpenAI

dotenv.load_dotenv()

client = OpenAI(base_url=os.getenv("OLLAMA_HOST"), api_key=os.getenv("OLLAMA_API_KEY"))

user_input = input("Enter your prompt: ")

SYSTEM_PROMPT = """
You are a coding agent. Your job is to code, always code.
Use the bash tool to inspect files.
Anser back to the user once exploration is done.
"""


response = client.chat.completions.create(
    model=os.environ.get("OLLAMA_LANG_MODEL"),
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ],
    tools=[tools.BASH_TOOL],
)

message = response.choices[0].message
output = message.content

completetion_details = response.usage.completion_tokens_details
prompt_details = response.usage.prompt_tokens_details

usage = {
    "prompt_tokens": response.usage.prompt_tokens,
    "completion_tokens": response.usage.completion_tokens,
    "reasoning_tokens": getattr(completetion_details, "reasoning_tokens", None),
    "cached_tokens": getattr(completetion_details, "cached_tokens", None),
}
print("\nAgent: ", output, "\n")

if message.tool_calls:
    tool_call = message.tool_calls[0]
    print(tool_call)
    command = json.loads(tool_call.function.arguments)["command"]
    print("Tool: bash", command)
    print(tools.bash(command), "\n")

print(usage)
