from dataclasses import dataclass
import pymupdf

@dataclass
class Chunk:
    page: int
    index: int
    text: str

def extract_pages(pdf_path: str) -> list[tuple[int, str]]:
    
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                pages.append((i+1, text))
    return pages

def chunk_pages(pages: list[tuple[int,str]], size:int = 250, overlap: int = 40) -> list[Chunk]:
    if size <= 0:
        raise ValueError("Chunk size must be positive.")
    if not 0 <= overlap < size:
        raise ValueError("Overlap must be non-negative and less than chunk size.")
    
    step = size - overlap   
    chunks: list[Chunk] = []
    for page_num, text in pages:
        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + size, len(words))
            chunk_text = " ".join(words[start:end])
            chunks.append(Chunk(page=page_num, index=len(chunks), text=chunk_text))
            if end == len(words):
                break
            start += step
    return chunks