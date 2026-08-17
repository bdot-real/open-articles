"""Azure. Azure ML, not AI Foundry.

The split is easy to get wrong. Azure ML is for classical machine learning.
AI Foundry is for generative work. A logistic regression belongs in the former,
and reaching for Foundry because it is the newer service puts a 1.5 KB model on
a platform built for a different problem.

Azure ML leans hard on MLflow and on data drift monitoring, which is the thing
you will need in month six and will not have thought about in week one.

Reference script. Needs an Azure ML workspace.
"""
import os

from azure.ai.ml import MLClient, command
from azure.ai.ml.entities import ManagedOnlineDeployment, ManagedOnlineEndpoint
from azure.identity import DefaultAzureCredential


def client() -> MLClient:
    return MLClient(
        DefaultAzureCredential(),
        subscription_id=os.environ["AZURE_SUBSCRIPTION_ID"],
        resource_group_name=os.environ["AZURE_RESOURCE_GROUP"],
        workspace_name=os.environ["AZURE_ML_WORKSPACE"],
    )


def submit_training(ml_client: MLClient):
    job = command(
        code="./platforms/azureml_src",
        command="python train_entry.py --data ${{inputs.data}} --max-iter 1000",
        environment="AzureML-sklearn-1.5@latest",
        compute="cpu-cluster",
        display_name="noshow-lr",
        experiment_name="appointment-noshow",
    )
    return ml_client.jobs.create_or_update(job)


def deploy(ml_client: MLClient, model):
    endpoint = ManagedOnlineEndpoint(name="noshow-lr", auth_mode="key")
    ml_client.online_endpoints.begin_create_or_update(endpoint).result()

    ml_client.online_deployments.begin_create_or_update(
        ManagedOnlineDeployment(
            name="blue", endpoint_name="noshow-lr", model=model,
            instance_type="Standard_DS2_v2", instance_count=1,
        )
    ).result()


if __name__ == "__main__":
    c = client()
    print(submit_training(c).studio_url)
