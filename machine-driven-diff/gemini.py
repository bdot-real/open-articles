"""Google. Gemini Enterprise Agent Platform, formerly Vertex AI.

The April 2026 rename did not change the SDK surface. Existing Vertex code and
endpoints continue to work.
"""
import os


def review(prompt: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(
        vertexai=True,
        project=os.environ["GCP_PROJECT"],
        location=os.environ.get("GCP_LOCATION", "us-central1"),
    )
    resp = client.models.generate_content(
        model=os.environ["GEMINI_MODEL"],
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0, max_output_tokens=2000),
    )
    return resp.text
