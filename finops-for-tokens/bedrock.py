"""AWS. Attribution is native. Enforcement is yours to build.

Application inference profiles carry cost allocation tags and deliver spend to
Cost Explorer and the CUR. The granularity is one usage type per day, so they
answer "which team spent what last week" rather than "what did this request
cost". Per-request detail comes from requestMetadata landing in model
invocation logs.

There is no native token limit policy, so the hard stop is the BudgetGuard in
this repository, sitting in front of this call.

Profiles go at the team or cost-centre level. Do not create one per user; put
the user in requestMetadata instead.
"""
import os

from finops.context import CallContext
from finops.pricing import Usage


def invoke(messages: list[dict], tags: dict) -> tuple[str, Usage]:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
    resp = client.converse(
        modelId=os.environ["BEDROCK_INFERENCE_PROFILE_ARN"],
        messages=[{"role": m["role"], "content": [{"text": m["content"]}]}
                  for m in messages],
        inferenceConfig={"maxTokens": 2000, "temperature": 0},
        requestMetadata=tags,          # tenant, feature, user, trace_id
    )
    u = resp["usage"]
    return resp["output"]["message"]["content"][0]["text"], Usage(
        input_tokens=u["inputTokens"],
        output_tokens=u["outputTokens"],
        cache_read_tokens=u.get("cacheReadInputTokens", 0),
        cache_write_tokens=u.get("cacheWriteInputTokens", 0),
    )


def example(ctx: CallContext) -> dict:
    """What the tags look like on the wire."""
    return ctx.as_tags()
