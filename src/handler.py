"""S3 ObjectCreated -> Textract OCR -> Nova summary + Titan embeddings -> pgvector.

Document-scoped: everything written here is tied to the single report_id resolved from the
uploaded object key.
"""

import logging
from urllib.parse import unquote_plus

from .bedrock import embed_text, summarize
from .chunking import chunk_text
from .db import resolve_report_id, save_results
from .textract_ocr import extract_text

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _process_object(bucket: str, key: str) -> None:
    report_id = resolve_report_id(key)
    if report_id is None:
        logger.warning("No lab_reports row for key=%s; skipping", key)
        return

    text = extract_text(bucket, key)
    summary = summarize(text)
    chunks_with_vectors = [(chunk, embed_text(chunk)) for chunk in chunk_text(text)]
    save_results(report_id, summary, chunks_with_vectors)
    logger.info("Processed report_id=%s chunks=%d", report_id, len(chunks_with_vectors))


def lambda_handler(event: dict, context: object) -> dict:
    # Support both direct S3 event notifications and EventBridge S3 notifications
    if "Records" in event:
        for record in event["Records"]:
            bucket = record["s3"]["bucket"]["name"]
            key = unquote_plus(record["s3"]["object"]["key"])
            _process_object(bucket, key)
    elif "detail" in event:
        bucket = event["detail"]["bucket"]["name"]
        key = unquote_plus(event["detail"]["object"]["key"])
        _process_object(bucket, key)
    return {"status": "ok"}

