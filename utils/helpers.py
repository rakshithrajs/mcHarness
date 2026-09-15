"""Helper functions for common tasks."""

from llm.llm import client
from utils import printer


def status() -> None:
    """Print the status of the LLM client, including available models."""
    models = client.models.list().data
    printer.models_table(models)
