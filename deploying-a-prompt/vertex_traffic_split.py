"""Google. Vertex endpoints with traffic split.

Model Garden pins dated model versions and endpoints support a traffic split
across deployed models, so the mechanics are there.

The pairing discipline is entirely manual. Nothing stops a new prompt going out
against a moving model reference, so it has to be a convention you enforce in
code. deploy/release.py is that convention.
"""
import os

from google.cloud import aiplatform


def set_canary(endpoint_name: str, stable_id: str, candidate_id: str,
               canary_percent: int) -> None:
    aiplatform.init(project=os.environ["GCP_PROJECT"],
                    location=os.environ.get("GCP_LOCATION", "us-central1"))
    endpoint = aiplatform.Endpoint(endpoint_name)
    endpoint.update(traffic_split={
        stable_id: 100 - canary_percent,
        candidate_id: canary_percent,
    })
