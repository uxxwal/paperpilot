import argparse
import hashlib

from paperpilot.db import get_conn
from paperpilot.embed import embed_texts
from paperpilot.ingest import chunk_pages, extract_pages
from paperpilot.store import Status, insert_chunks, insert_paper, set_status


def file_sha256(path: str) -> str:
    """Fingerprint a file so the same PDF is never ingested twice."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()

def register_paper(pdf_path: str, title: str) -> tuple[int, str]:
    """Phase 1: Create the paper row as PENDING (or return the exisiting one)"""
    file_hash = file_sha256(pdf_path)
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, status FROM papers WHERE file_hash = %s", (file_hash,)
        ).fetchone()
        if existing:
            return existing[0], existing[1]
        paper_id = insert_paper(conn, title, source="upload", file_hash=file_hash)
        return paper_id, Status.PENDING
def process_paper(paper_id: int, pdf_path: str) -> None:
    """Phase 2: extract, chunk, embed, store. Mark COMPLETED or FAILED."""
    with get_conn() as conn:
        set_status(conn, paper_id, Status.PROCESSING)
    try:
        pages = extract_pages(pdf_path)
        if not pages:
            raise ValueError("No extractable text in PDF (scanned or image-only?)")
        chunks = chunk_pages(pages)
        embeddings = embed_texts([c.text for c in chunks])
        with get_conn() as conn:
            insert_chunks(conn, paper_id, chunks, embeddings)
            set_status(conn, paper_id, Status.COMPLETED)
    except Exception as e:
        with get_conn() as conn:
            set_status(conn, paper_id, Status.FAILED, error=str(e))
        raise

def ingest_pdf(pdf_path: str, title:str) -> int:
    """Register and process a PDF end to end. Returns the paper id."""
    paper_id, status = register_paper(pdf_path, title)
    if status == Status.COMPLETED:
        return paper_id
    process_paper(paper_id, pdf_path)
    return paper_id

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a PDF into Paperpilot")
    parser.add_argument("pdf_path")
    parser.add_argument("title")
    args = parser.parse_args()
    pid = ingest_pdf(args.pdf_path, args.title)
    print(f"Ingested paper {pid}")