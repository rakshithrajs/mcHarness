"""Model name alias parser."""

import json
from pathlib import Path

MODEL_FILE_PATH = Path(__file__).resolve().parent.parent / "config" / "models.json"


def model_select(model_name: str) -> str:
    """Select a model based on the provided name or alias."""
    try:
        with open(MODEL_FILE_PATH, encoding="utf-8") as file:
            models: dict[str, str] = json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Model file not found at {MODEL_FILE_PATH}. Please ensure the file exists.",
        ) from exc

    if model_name in models:
        return models[model_name]

    # If the name isn't a configured alias, treat it as a direct model reference
    # (e.g. "glm-5.1:cloud") and pass it through unchanged.
    return model_name
