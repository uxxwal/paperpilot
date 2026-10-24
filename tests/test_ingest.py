import itertools

import pytest

from paperpilot.ingest import chunk_pages


def make_text(n: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{i}" for i in range(n))


def test_chunks_respect_size():
    pages = [(1, make_text(600))]
    chunks = chunk_pages(pages, size=250, overlap=40)
    for chunk in chunks:
        assert len(chunk.text.split()) <= 250


def test_neighbouring_chunks_overlap():
    pages = [(1, make_text(600))]
    chunks = chunk_pages(pages, size=250, overlap=40)
    for prev, nxt in itertools.pairwise(chunks):
        assert prev.text.split()[-40:] == nxt.text.split()[:40]


def test_short_page_is_one_chunk():
    pages = [(1, make_text(50))]
    chunks = chunk_pages(pages, size=250, overlap=40)
    assert len(chunks) == 1
    assert chunks[0].text == make_text(50)


def test_index_runs_across_pages():
    pages = [(1, make_text(600, "a")), (2, make_text(600, "b"))]
    chunks = chunk_pages(pages, size=250, overlap=40)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert {c.page for c in chunks} == {1, 2}


def test_overlap_too_big_rasies():
    with pytest.raises(ValueError):
        chunk_pages([(1, make_text(100))], size=50, overlap=50)


def test_exactly_size_words_is_one_chunk():
    pages = [(1, make_text(250))]
    chunks = chunk_pages(pages, size=250, overlap=40)
    assert len(chunks) == 1


def test_no_pages_returns_no_chunks():
    pages = [(1, "")]
    chunks = chunk_pages(pages, size=250, overlap=40)
    assert chunks == []
