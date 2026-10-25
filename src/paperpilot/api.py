import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from paperpilot.db import get_conn
from paperpilot.pipeline import process_paper, register_paper
from paperpilot.store import Status

executor = ThreadPoolExecutor(max_workers=1)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    for paper_id, path in recover_stuck_papers():
        logger.info("Recovering paper %s", paper_id)
        executor.submit(process_in_background, paper_id, path)
    yield


app = FastAPI(title="PaperPilot", lifespan=lifespan)
logger = logging.getLogger("paperpilot")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


def process_in_background(paper_id: int, path: str) -> None:
    """Background wrapper: run phase 2 and log any failures (its already recorded on the paper)"""
    try:
        process_paper(paper_id, path)
    except Exception:
        logger.exception("Processing failed for paper %s", paper_id)


def recover_stuck_papers() -> list[tuple[int, str]]:
    """Find papers interrupted by a restart."""
    with get_conn() as conn:
        return conn.execute(
            "SELECT id, file_path FROM papers WHERE status IN (%s, %s) AND file_path IS NOT NULL ORDER BY id",
            (Status.PENDING, Status.PROCESSING),
        ).fetchall()


class PaperOut(BaseModel):
    id: int
    title: str
    status: str
    error: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/papers", response_model=PaperOut, status_code=202)
def upload_paper(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    background_tasks: BackgroundTasks,
) -> PaperOut:
    data = file.file.read()
    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    path = UPLOAD_DIR / f"{uuid.uuid4()}.pdf"
    path.write_bytes(data)

    paper_id, status = register_paper(str(path), title)
    if status != Status.COMPLETED:
        executor.submit(process_in_background, paper_id, str(path))
    return get_paper(paper_id)


@app.get("/papers", response_model=list[PaperOut])
def list_papers() -> list[PaperOut]:
    with get_conn() as conn:
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
