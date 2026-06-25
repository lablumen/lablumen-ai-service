"""Synchronous Textract OCR.

Per the locked directive, OCR is kept synchronous (low-overhead). `detect_document_text` is the
synchronous API and suits single-page documents/images; multi-page async Textract is intentionally
out of scope for v1.
"""

import os

import boto3


def _make_textract_client():
    role_arn = os.environ.get("BEDROCK_CROSS_ACCOUNT_ROLE_ARN")
    if not role_arn:
        return boto3.client("textract")
    sts = boto3.client("sts")
    creds = sts.assume_role(
        RoleArn=role_arn,
        RoleSessionName="lablumen-ai-textract",
    )["Credentials"]
    return boto3.client(
        "textract",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )


_textract = _make_textract_client()


def extract_text(bucket: str, key: str) -> str:
    resp = _textract.detect_document_text(
        Document={"S3Object": {"Bucket": bucket, "Name": key}}
    )
    lines = [b["Text"] for b in resp.get("Blocks", []) if b.get("BlockType") == "LINE"]
    return "\n\n".join(lines)
