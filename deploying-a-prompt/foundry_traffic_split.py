"""Azure. AI Foundry managed online endpoints.

The tightest integration of the four. Prompt Flow version-controls the
pipeline, evaluates it, and deploys it as a managed endpoint, so the artifact
you evaluated and the artifact you deployed are the same versioned thing. That
removes a class of drift where the eval ran against a prompt nobody shipped.

Traffic splitting is endpoint-native, so the canary percentage needs no extra
infrastructure.
"""
import os

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential


def client() -> MLClient:
    return MLClient(
        DefaultAzureCredential(),
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
        workspace_name=os.environ["AZURE_AI_PROJECT"],
    )


def set_canary(endpoint_name: str, canary_percent: int) -> None:
    """Shift traffic between the stable and candidate deployments."""
    ml = client()
    endpoint = ml.online_endpoints.get(endpoint_name)
    endpoint.traffic = {"stable": 100 - canary_percent, "candidate": canary_percent}
    ml.online_endpoints.begin_create_or_update(endpoint).result()


def rollback(endpoint_name: str) -> None:
    set_canary(endpoint_name, 0)
