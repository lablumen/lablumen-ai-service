"""Bedrock calls via raw boto3 (no LangChain)."""

import json
import os

import boto3

_client = boto3.client("bedrock-runtime")

EMBED_MODEL_ID = os.environ.get("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v1")
TEXT_MODEL_ID = os.environ.get("BEDROCK_TEXT_MODEL_ID", "amazon.nova-2-lite-v1:0")

_SUMMARY_SYSTEM = (
    "You write a short, empathetic, plain-language summary of a patient's lab report. "
    "Avoid jargon, do not diagnose, and remind the reader to discuss results with their clinician."
)


def embed_text(text: str) -> list[float]:
    resp = _client.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps({"inputText": text}),
        accept="application/json",
        contentType="application/json",
    )
    return json.loads(resp["body"].read())["embedding"]


def summarize(report_text: str) -> str:
    resp = _client.converse(
        modelId=TEXT_MODEL_ID,
        system=[{"text": _SUMMARY_SYSTEM}],
        messages=[{"role": "user", "content": [{"text": report_text}]}],
        inferenceConfig={"maxTokens": 600, "temperature": 0.2},
    )
    return resp["output"]["message"]["content"][0]["text"]
