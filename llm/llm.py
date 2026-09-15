"""LLM integration for the harness agent."""

import json
import os
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Union, cast

import dotenv
from ollama import AsyncClient, ChatResponse, Client, GenerateResponse
from ollama._types import (
    Message as OllamaMessage,
)
from ollama._types import (
    Options as OllamaOptions,
)
from ollama._types import (
    Tool as OllamaTool,
)

from context import context
from security import SecurityError
from skills.skills import skills_prompt
from tools import tools
from utils.model_parser import model_select

# Ollama uses a bare `Callable` in the `tools` union, which makes Pyright mark the
# bound methods as "partially unknown". We cast each bound method we use to a plain
# variadic callable with the concrete return type for the mode we actually call.
ChatCallable = Callable[..., ChatResponse]
ChatStreamCallable = Callable[..., Iterator[ChatResponse]]
ChatAsyncCallable = Callable[..., Awaitable[ChatResponse]]
ChatStreamAsyncCallable = Callable[..., Awaitable[AsyncIterator[ChatResponse]]]
GenerateCallable = Callable[..., GenerateResponse]
GenerateStreamCallable = Callable[..., Iterator[GenerateResponse]]
GenerateAsyncCallable = Callable[..., Awaitable[GenerateResponse]]
GenerateStreamAsyncCallable = Callable[..., Awaitable[AsyncIterator[GenerateResponse]]]

dotenv.load_dotenv()

# Configure explicit Ollama clients pointing at the remote host. The module-level
# `ollama.chat` helper defaults to localhost:11434, which is wrong for cloud models.
_ollama_headers = {"Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY", "")}
_ollama_client = Client(host=os.getenv("OLLAMA_HOST"), headers=_ollama_headers)
_ollama_async_client = AsyncClient(host=os.getenv("OLLAMA_HOST"), headers=_ollama_headers)

_chat: ChatCallable = _ollama_client.chat  # type: ignore[assignment]
_chat_stream: ChatStreamCallable = _ollama_client.chat  # type: ignore[assignment]
_chat_async: ChatAsyncCallable = _ollama_async_client.chat  # type: ignore[assignment]
_chat_stream_async: ChatStreamAsyncCallable = _ollama_async_client.chat  # type: ignore[assignment]

_generate: GenerateCallable = _ollama_client.generate  # type: ignore[assignment]
_generate_stream: GenerateStreamCallable = _ollama_client.generate  # type: ignore[assignment]
_generate_async: GenerateAsyncCallable = _ollama_async_client.generate  # type: ignore[assignment]
_generate_stream_async: GenerateStreamAsyncCallable = _ollama_async_client.generate  # type: ignore[assignment]

MAX_TOOL_ITERATIONS = 10

SYSTEM_PROMPT = f"""
You are a coding agent. Your job is to code, always code.
Use the bash tool to inspect files.
Answer back to the user once exploration is done.

Your current working directory is: {os.getcwd()}

You operate inside a security sandbox. File writes and edits are restricted
to the project directory by default. Destructive shell commands, writes to
executable or script files, and access to sensitive system paths are blocked
or require explicit user confirmation. If a tool call is rejected, explain the
issue to the user and ask how to proceed.

You have skills available. Each one is a set of instructions for a task.
If a skill matches what the user wants, call read_skill first and follow it.

{skills_prompt()}
"""


@dataclass()
class Options:
    """Configuration for the agent."""

    # system prompt to use for the agent.
    system_prompt: str
    # model name to use for the agent.
    model: Optional[str] = None
    # tools for the agent to use.
    tools: Optional[Sequence[OllamaTool | Mapping[str, Any]]] = None
    # stream the agent's response as it is generated.
    stream: bool = False
    # think enables the agent to reason about its actions before taking them.
    think: Optional[Union[bool, Literal["low", "medium", "high"]]] = None
    # format specification for the agent's response.
    format: Optional[Union[Literal["", "json"], dict[str, Any]]] = None

    """
    Internal generation controls. These values are forwarded to the underlying
    model provider and can influence output quality, determinism, and token usage.
    """

    # Sampling randomness or how cretive a model should be in [0.0, 2.0], e.g. 0.7.
    temperature: Optional[float] = None
    # Maximum number of tokens to generate for the completion, e.g. 256.
    max_tokens: Optional[int] = None
    # Nucleus sampling threshold. Lower values make the model choose more likely
    # next tokens; higher values allow more diversity. Example: 0.9.
    top_p: Optional[float] = None
    # Stop sequences tell the model when to halt generation early. Example: ("\n\n", "END").
    stop: Optional[Sequence[str]] = None
    # Seed for deterministic sampling when supported by the provider, e.g. 1234.
    seed: Optional[int] = None
    # Penalizes repeating tokens too frequently in the output. Example: 0.5.
    frequency_penalty: Optional[float] = None
    # Penalizes introducing tokens that are not already present in the prompt. Example: 0.2.
    presence_penalty: Optional[float] = None

    # options dictionary to be passed to the LLM provider. This is constructed from the above fields.
    options: Optional[OllamaOptions] = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.model is None:
            self.model = os.environ.get("OLLAMA_LANG_MODEL", default="glm-5.1:cloud")

        opts = cast(OllamaOptions, {})
        if self.temperature is not None:
            opts["temperature"] = self.temperature
        if self.max_tokens is not None:
            # Ollama uses 'num_predict' for max_tokens.
            opts["num_predict"] = self.max_tokens
        if self.top_p is not None:
            opts["top_p"] = self.top_p
        if self.stop is not None:
            opts["stop"] = list(self.stop)
        if self.seed is not None:
            opts["seed"] = self.seed
        if self.frequency_penalty is not None:
            opts["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty is not None:
            opts["presence_penalty"] = self.presence_penalty
        self.options = opts


class BaseAgent:
    """Stateful agent that manages conversation history and tool calling."""

    def __init__(self, options: Options) -> None:
        options.model = model_select(options.model or os.environ.get("OLLAMA_LANG_MODEL", default="glm-5.1:cloud"))
        self.options = options
        self.messages: list[Union[Mapping[str, Any], OllamaMessage]] = []
        if options.system_prompt:
            self.messages.append({"role": "system", "content": options.system_prompt})

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """Append a raw message to the conversation history."""
        self.messages.append({"role": role, "content": content, **kwargs})

    def add_user_message(self, content: str) -> None:
        """Append a user message to the conversation history."""
        self.add_message("user", content)

    def add_assistant_message(self, response: ChatResponse) -> None:
        """Append an assistant response to the conversation history."""
        self.messages.append(response.message.model_dump(exclude_none=True))

    def add_tool_result(self, content: str) -> None:
        """Append a tool result to the conversation history."""
        self.add_message("tool", content)

    def reset(self) -> None:
        """Clear history and re-inject the system prompt if configured."""
        self.messages.clear()
        if self.options.system_prompt:
            self.messages.append({"role": "system", "content": self.options.system_prompt})

    def _build_messages(self) -> list[Union[Mapping[str, Any], OllamaMessage]]:
        """Return current messages with the latest context reminder appended."""
        return [*self.messages, context.reminder()]

    def chat(self) -> ChatResponse:
        """Start a non-streaming chat session with the agent."""
        return _chat(
            model=cast(str, self.options.model),
            messages=self._build_messages(),
            tools=self.options.tools,
            stream=False,
            think=self.options.think,
            format=self.options.format,
            options=self.options.options,
        )

    def chat_stream(self) -> Iterator[ChatResponse]:
        """Start a streaming chat session with the agent."""
        return _chat_stream(
            model=cast(str, self.options.model),
            messages=self._build_messages(),
            tools=self.options.tools,
            stream=True,
            think=self.options.think,
            format=self.options.format,
            options=self.options.options,
        )

    async def chat_async(self) -> ChatResponse:
        """Start an async non-streaming chat session with the agent."""
        response = await _chat_async(
            model=cast(str, self.options.model),
            messages=self._build_messages(),
            tools=self.options.tools,
            stream=False,
            think=self.options.think,
            format=self.options.format,
            options=self.options.options,
        )
        return response

    async def chat_stream_async(self) -> AsyncIterator[ChatResponse]:
        """Start an async streaming chat session with the agent."""
        stream = await _chat_stream_async(
            model=cast(str, self.options.model),
            messages=self._build_messages(),
            tools=self.options.tools,
            stream=True,
            think=self.options.think,
            format=self.options.format,
            options=self.options.options,
        )
        async for chunk in stream:
            yield chunk

    def generate(self, prompt: str) -> GenerateResponse:
        """Generate a non-streaming response for the given prompt."""
        return _generate(
            model=cast(str, self.options.model),
            prompt=prompt,
            system=self.options.system_prompt,
            stream=False,
            think=self.options.think,
            format=self.options.format,
            options=self.options.options,
        )

    def generate_stream(self, prompt: str) -> Iterator[GenerateResponse]:
        """Generate a streaming response for the given prompt."""
        return _generate_stream(
            model=cast(str, self.options.model),
            prompt=prompt,
            system=self.options.system_prompt,
            stream=True,
            think=self.options.think,
            format=self.options.format,
            options=self.options.options,
        )

    async def generate_async(self, prompt: str) -> GenerateResponse:
        """Generate an async non-streaming response for the given prompt."""
        response = await _generate_async(
            model=cast(str, self.options.model),
            prompt=prompt,
            system=self.options.system_prompt,
            stream=False,
            think=self.options.think,
            format=self.options.format,
            options=self.options.options,
        )
        return response

    async def generate_stream_async(self, prompt: str) -> AsyncIterator[GenerateResponse]:
        """Generate an async streaming response for the given prompt."""
        stream = await _generate_stream_async(
            model=cast(str, self.options.model),
            prompt=prompt,
            system=self.options.system_prompt,
            stream=True,
            think=self.options.think,
            format=self.options.format,
            options=self.options.options,
        )
        async for chunk in stream:
            yield chunk

    def _execute_tool(self, call: OllamaMessage.ToolCall) -> str:
        """Execute a single tool call and return its string result."""
        name = call.function.name
        if name not in tools.TOOLS:
            return f"Error: unknown tool {name}"
        try:
            raw_arguments = call.function.arguments
            if isinstance(raw_arguments, str):
                arguments = json.loads(raw_arguments)
            else:
                arguments = dict(raw_arguments)
            return str(tools.TOOLS[name](**arguments))
        except SecurityError as e:
            return f"SecurityError: {e.reason}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    def run_turn(self, user_input: str) -> ChatResponse:
        """Run one user turn, including any tool calls, and return the final response."""
        self.add_user_message(user_input)
        response = self.chat()
        self.add_assistant_message(response)

        for _ in range(MAX_TOOL_ITERATIONS):
            if not response.message.tool_calls:
                break
            for call in response.message.tool_calls:
                result = self._execute_tool(call)
                self.add_tool_result(result)
            response = self.chat()
            self.add_assistant_message(response)

        return response

    async def run_turn_async(self, user_input: str) -> ChatResponse:
        """Run one async user turn, including any tool calls, and return the final response."""
        self.add_user_message(user_input)
        response = await self.chat_async()
        self.add_assistant_message(response)

        for _ in range(MAX_TOOL_ITERATIONS):
            if not response.message.tool_calls:
                break
            for call in response.message.tool_calls:
                result = self._execute_tool(call)
                self.add_tool_result(result)
            response = await self.chat_async()
            self.add_assistant_message(response)

        return response
