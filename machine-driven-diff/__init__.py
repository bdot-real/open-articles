"""Backend selection.

One environment variable swaps the provider. The pipeline around it does not
change, which is the whole architectural point.
"""
import importlib
from typing import Callable

BACKENDS = {
    "bedrock": "review.backends.bedrock",
    "foundry": "review.backends.foundry",
    "gemini": "review.backends.gemini",
    "local": "review.backends.openai_compat",
}


def get_backend(name: str) -> Callable[[str], str]:
    if name not in BACKENDS:
        raise SystemExit(
            f"Unknown backend {name!r}. Choose one of: {', '.join(sorted(BACKENDS))}"
        )
    return importlib.import_module(BACKENDS[name]).review
