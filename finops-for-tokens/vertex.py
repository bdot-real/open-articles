"""Google. Same shape as AWS.

Labels give billing-level attribution and quotas give a ceiling, but the
ceiling is per project and per region rather than per tenant. Anything
tenant-shaped is application-layer work, which means the BudgetGuard in this
repository again.
"""
import os

from finops.pricing import Usage


def invoke(messages: list[dict], tags: dict) -> tuple[str, Usage]:
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=os.environ["GCP_PROJECT"],
        location=os.environ.get("GCP_LOCATION", "us-central1"),
    )
    resp = client.models.generate_content(
        model=os.environ["GEMINI_MODEL"],
        contents=[m["content"] for m in messages],
        config=types.GenerateContentConfig(
            temperature=0,
            max_output_tokens=2000,
            labels={k: v for k, v in tags.items() if k in ("tenant_id", "feature")},
        ),
    )
    m = resp.usage_metadata
    return resp.text, Usage(
        input_tokens=m.prompt_token_count,
        output_tokens=m.candidates_token_count,
        cache_read_tokens=getattr(m, "cached_content_token_count", 0) or 0,
    )
