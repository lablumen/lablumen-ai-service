"""Synchronous DB writes (psycopg) into the pgvector-backed schema."""

import json
import os

import boto3
import psycopg

# Secret name is configurable via env var so the function can be tested locally
# with a different secret or overridden without code change.
_SECRET_ID = os.environ.get("DATABASE_SECRET_ID", "lablumen/app/database-url")

# Cache the DSN at Lambda cold start — avoids a Secrets Manager call on every invocation.
_dsn_cache: str | None = None


def _get_dsn() -> str:
    global _dsn_cache
    if _dsn_cache is not None:
        return _dsn_cache

    sm = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    raw = sm.get_secret_value(SecretId=_SECRET_ID)["SecretString"]

    # The secret may be a plain DSN string or a JSON object with a "url" key.
    try:
        url = json.loads(raw).get("url", raw)
    except (json.JSONDecodeError, AttributeError):
        url = raw

    # Normalize the SQLAlchemy-style URL to a plain libpq DSN.
    _dsn_cache = url.replace("+asyncpg", "").replace("+psycopg", "")
    return _dsn_cache


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def resolve_report_id(s3_key: str) -> str | None:
    with psycopg.connect(_get_dsn()) as conn, conn.cursor() as cur:
        cur.execute("SELECT report_id FROM lab_reports WHERE s3_url = %s", (s3_key,))
        row = cur.fetchone()
        return str(row[0]) if row else None


def save_results(
    report_id: str, summary: str, chunks_with_vectors: list[tuple[str, list[float]]]
) -> None:
    with psycopg.connect(_get_dsn()) as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE lab_reports SET ai_layman_summary = %s WHERE report_id = %s",
            (summary, report_id),
        )
        for chunk, vec in chunks_with_vectors:
            cur.execute(
                "INSERT INTO report_embeddings (report_id, chunk_content, embedding) "
                "VALUES (%s, %s, %s::vector)",
                (report_id, chunk, _vector_literal(vec)),
            )
        conn.commit()

