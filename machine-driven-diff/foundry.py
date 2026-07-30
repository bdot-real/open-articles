"""Azure. AI Foundry inference endpoint.

A key is used here for brevity. In CI prefer DefaultAzureCredential with a
federated workload identity, which removes the secret from the repo entirely.
"""
import os


def review(prompt: str) -> str:
    from azure.ai.inference import ChatCompletionsClient
    from azure.core.credentials import AzureKeyCredential

    client = ChatCompletionsClient(
        endpoint=os.environ["AZURE_AI_ENDPOINT"],
        credential=AzureKeyCredential(os.environ["AZURE_AI_KEY"]),
    )
    resp = client.complete(
        model=os.environ["AZURE_AI_DEPLOYMENT"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=2000,
    )
    return resp.choices[0].message.content
