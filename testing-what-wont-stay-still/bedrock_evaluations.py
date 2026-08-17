"""AWS. Bedrock Evaluations.

Automated metrics or human reviewers, with LLM-as-judge evaluators using a
second Bedrock model to score at scale. Knowledge base evaluation scores
retrieval and generation separately, which is the right instinct and the same
argument as the RAG article in this series: generation quality is bounded by
retrieval recall, so a single blended score cannot tell you which half to fix.

Bring-Your-Own-Inference lets you evaluate a RAG system running outside
Bedrock, which matters when your retrieval layer is not AWS.

What it does not do, and neither does any of the other three: tell you your
judge's agreement rate with human labels. See evals/judge.py.
"""
import os

import boto3


def start_evaluation(dataset_s3_uri: str, job_name: str):
    client = boto3.client("bedrock", region_name=os.environ["AWS_REGION"])
    return client.create_evaluation_job(
        jobName=job_name,
        roleArn=os.environ["BEDROCK_EVAL_ROLE_ARN"],
        evaluationConfig={"automated": {
            "datasetMetricConfigs": [{
                "taskType": "Generation",
                "dataset": {"name": "booking-extraction",
                            "datasetLocation": {"s3Uri": dataset_s3_uri}},
                "metricNames": ["Builtin.Correctness", "Builtin.Faithfulness"],
            }],
        }},
        inferenceConfig={"models": [{"bedrockModel": {
            "modelIdentifier": os.environ["BEDROCK_MODEL_ID"],
            "inferenceParams": '{"temperature":0}',
        }}]},
        outputDataConfig={"s3Uri": os.environ["BEDROCK_EVAL_OUTPUT_S3"]},
    )
