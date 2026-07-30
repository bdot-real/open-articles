"""AWS. Bedrock Converse API.

Model IDs are region- and date-specific, so they live in the environment rather
than in the source. Auth comes from the ambient credential chain, which in CI
means an OIDC-assumed role with bedrock:InvokeModel.
"""
import os


def review(prompt: str) -> str:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
    resp = client.converse(
        modelId=os.environ["BEDROCK_MODEL_ID"],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 2000, "temperature": 0},
    )
    return resp["output"]["message"]["content"][0]["text"]
