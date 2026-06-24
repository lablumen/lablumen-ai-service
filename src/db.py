"""Synchronous DB writes (psycopg) into the pgvector-backed schema."""

import os

import psycopg


def _dsn() -> str:
    # Normalize the SQLAlchemy-style URL to a plain libpq DSN.
    url = os.environ["DATABASE_URL"]
    return url.replace("+asyncpg", "").replace("+psycopg", "")


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


def resolve_report_id(s3_key: str) -> str | None:
    with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
        cur.execute("SELECT report_id FROM lab_reports WHERE s3_url = %s", (s3_key,))
        row = cur.fetchone()
        return str(row[0]) if row else None


def save_results(
    report_id: str, summary: str, chunks_with_vectors: list[tuple[str, list[float]]]
) -> None:
    with psycopg.connect(_dsn()) as conn, conn.cursor() as cur:
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
