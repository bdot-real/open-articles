"""Azure. AI Foundry evaluation.

Prompt Flow version-controls the pipeline, runs evaluations against it, and
deploys it as a managed endpoint from the same place. The integration is the
selling point: the artifact you evaluated and the artifact you deployed are the
same versioned thing, which removes a class of drift where the eval ran against
a prompt nobody shipped.
"""
import os

from azure.ai.evaluation import GroundednessEvaluator, evaluate
from azure.identity import DefaultAzureCredential


def run(dataset_path: str):
    model_config = {
        "azure_endpoint": os.environ["AZURE_AI_ENDPOINT"],
        "azure_deployment": os.environ["AZURE_AI_DEPLOYMENT"],
    }
    return evaluate(
        data=dataset_path,
        evaluators={"groundedness": GroundednessEvaluator(model_config)},
        azure_ai_project={
            "subscription_id": os.environ["AZURE_SUBSCRIPTION_ID"],
            "resource_group_name": os.environ["AZURE_RESOURCE_GROUP"],
            "project_name": os.environ["AZURE_AI_PROJECT"],
        },
        credential=DefaultAzureCredential(),
    )
