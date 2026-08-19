"""AWS. Bedrock prompt management plus application inference profiles.

Prompts get versions addressed by ARN, which is an immutable identifier rather
than a string in a config file. Pair it with an application inference profile
from the FinOps article in this series and the canary arm carries its own cost
attribution, so you can see what the candidate costs before promoting it.

What Bedrock does not do, and neither does any of the other three: stop you
deploying a new prompt against a moving model reference.
"""
import os

import boto3


def invoke_pinned(prompt_arn: str, model_version: str, variables: dict):
    """The pairing is explicit in both arguments, and both are recorded."""
    if not model_version[-8:].isdigit():
        raise ValueError(f"{model_version} is not a dated version")

    client = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
    resp = client.converse(
        modelId=os.environ["BEDROCK_CANARY_PROFILE_ARN"],   # cost attribution
        promptVariables={k: {"text": v} for k, v in variables.items()},
        additionalModelRequestFields={"promptArn": prompt_arn},
        requestMetadata={"prompt_arn": prompt_arn, "model_version": model_version},
    )
    return resp["output"]["message"]["content"][0]["text"]
