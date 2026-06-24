"""Synchronous Textract OCR.

Per the locked directive, OCR is kept synchronous (low-overhead). `detect_document_text` is the
synchronous API and suits single-page documents/images; multi-page async Textract is intentionally
out of scope for v1.
"""

import boto3

_textract = boto3.client("textract")


def extract_text(bucket: str, key: str) -> str:
    resp = _textract.detect_document_text(
        Document={"S3Object": {"Bucket": bucket, "Name": key}}
    )
    lines = [b["Text"] for b in resp.get("Blocks", []) if b.get("BlockType") == "LINE"]
    return "\n\n".join(lines)
