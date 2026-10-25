import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from paperpilot.db import get_conn
from paperpilot.pipeline import process_paper, register_paper
from paperpilot.store import Status

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

app = FastAPI(title="PaperPilot")

class PaperOut(BaseModel):
    id: int
    title: str
    status: str
    error: str | None = None

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.post("/papers", response_model=PaperOut, status_code=201)
def upload_paper(file: Annotated[UploadFile, File()], title: Annotated[str, Form()],) -> PaperOut:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")
    path = UPLOAD_DIR / f"{uuid.uuid4()}.pdf"
    path.write_bytes(file.file.read())

    paper_id, status = register_paper(str(path), title)
    if status != Status.COMPLETED:
        try:
            process_paper(paper_id, str(path))
        except Exception: # noqa BLE001 
            pass
    return get_paper(paper_id)

@app.get("/papers", response_model=list[PaperOut])
def list_papers() -> list[PaperOut]:
    with get_conn as conn:
        rows = conn.execute(
            "SELECT id, title, status, error FROM papers ORDER BY id"
        ).fetchall()
    return [PaperOut(id=r[0], title=r[1], status=r[2], error=r[3]) for r in rows]

@app.get("/papers/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: int) -> PaperOut:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, title, status, error FROM papers WHERE id = %s", (paper_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return PaperOut(id=row[0], title=row[1], status=row[2], error=row[3])
