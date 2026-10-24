from enum import StrEnum

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from paperpilot.ingest import Chunk


class Status(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def insert_paper(
    conn: psycopg.Connection, title: str, source: str, file_hash: str | None = None
) -> int:
    row = conn.execute(
        "INSERT INTO papers (title, source, file_hash) VALUES (%s, %s, %s) RETURNING id",
        (title, source, file_hash),
    ).fetchone()
    return row[0]


def insert_chunks(
    conn: psycopg.Connection, paper_id: int, chunks: list[Chunk], embeddings: np.ndarray
) -> None:
    register_vector(conn)
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO chunks (paper_id, chunk_index, page, text, embedding) VALUES (%s, %s, %s, %s, %s)",
            [
                (paper_id, c.index, c.page, c.text, emb)
                for c, emb in zip(chunks, embeddings)
            ],
        )


def set_status(
    conn: psycopg.Connection, paper_id: int, status: str, error: str | None = None
) -> None:
    conn.execute(
        "Update papers SET status = %s, error = %s WHERE id = %s",
        (status, error, paper_id),
    )
