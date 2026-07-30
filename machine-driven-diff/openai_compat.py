"""Open source. Anything speaking the OpenAI wire format.

Ollama, vLLM, llama.cpp and LM Studio all serve this interface, so one client
covers self-hosted models on a workstation, a runner, or a GPU box.

This is the shortest backend in the repository. What the managed platforms sell
is not a better call. It is IAM, audit logging and private networking.
"""
import os


def review(prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI(
        base_url=os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1"),
        api_key=os.environ.get("LLM_API_KEY", "not-needed"),
    )
    resp = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=2000,
    )
    return resp.choices[0].message.content
