"""Helper functions for common tasks."""

from llm.llm import ollama_client
from utils import printer


def status() -> None:
    """Print the status of the LLM client, including available models."""
    models = ollama_client.list().models
    printer.models_table(list(models))
