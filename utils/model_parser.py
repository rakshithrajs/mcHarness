"""Model name alias parser."""

import json
from pathlib import Path

MODEL_FILE_PATH = Path(__file__).resolve().parent / "config" / "models.json"


def model_select(model_name: str) -> str:
    try:
        with open(MODEL_FILE_PATH, "r", encoding="utf-8") as file:
            models: dict[str, str] = json.load(file)
    except FileNotFoundError as exc:
        raise exc from FileNotFoundError(
            f"Model file not found at {MODEL_FILE_PATH}. Please ensure the file exists."
        )

    if model_name not in models:
        available = ", ".join(models.keys())
        raise ValueError(
            f"Model '{model_name}' not found in models.json. Available models: {available}"
        )

    return models[model_name]
