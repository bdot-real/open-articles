"""AWS. Bedrock AgentCore.

Actions are Lambda functions or OpenAPI schemas. Neither format carries an
effect annotation, so the classification lives in your handler.

DynamoDB conditional writes give you the dedupe primitive without another
service: the write succeeds once and throws on every replay, which is exactly
the semantics you want.
"""
import os

import boto3
from botocore.exceptions import ClientError

TABLE = os.environ.get("IDEMPOTENCY_TABLE", "agent-idempotency")

# The field the framework does not ask for. Keep it next to the tool
# definitions so a new tool cannot be registered without a decision.
EFFECTS = {
    "search_availability": "read",
    "validate_booking": "idempotent",
    "create_booking": "mutating",
    "cancel_booking": "mutating",
}


def handler(event, _context):
    action = event["actionGroup"]
    key = event["sessionAttributes"]["idempotency_key"]
    ddb = boto3.resource("dynamodb").Table(TABLE)

    if EFFECTS[action] == "read":
        return _perform(event)

    try:
        # Conditional write: succeeds once, throws on replay.
        ddb.put_item(
            Item={"key": key, "action": action, "ttl": _ttl()},
            ConditionExpression="attribute_not_exists(#k)",
            ExpressionAttributeNames={"#k": "key"},
        )
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        prior = ddb.get_item(Key={"key": key})["Item"]
        return {"deduplicated": True, "result": prior.get("result")}

    result = _perform(event)
    ddb.update_item(
        Key={"key": key},
        UpdateExpression="SET #r = :r",
        ExpressionAttributeNames={"#r": "result"},
        ExpressionAttributeValues={":r": result},
    )
    return result


def _perform(event):
    raise NotImplementedError("your tool goes here")


def _ttl(days: int = 7) -> int:
    import time
    return int(time.time()) + days * 86_400
