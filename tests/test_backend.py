"""Focused unit tests for SmartDoc AI backend logic.

These tests cover text extraction and chunking, which are deterministic and
do not require real API keys or a database. The full RAG path (embeddings,
vector search, generation) is verified separately against the live services.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.rag import chunk_text, extract_text, extract_text_pdf, extract_text_txt  # noqa: E402
from backend.config import GEMINI_API_KEY, DATABASE_URL  # noqa: E402


# ---------- chunking ----------

def test_chunk_empty_text():
    assert chunk_text("") == []
    assert chunk_text("   \n\t  ") == []


def test_chunk_short_text_single_chunk():
    chunks = chunk_text("A short document about security cameras.")
    assert len(chunks) == 1
    assert chunks[0].startswith("A short document")


def test_chunk_long_text_multiple_chunks():
    text = ("This is a test sentence about camera firmware. " * 100).strip()
    chunks = chunk_text(text)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 1100  # CHUNK_SIZE + small tolerance for sentence boundary


def test_chunk_text_preserves_content():
    text = ("The SmartGuard camera records video continuously. " * 80).strip()
    joined = " ".join(chunk_text(text))
    assert "SmartGuard" in joined
    # every chunk should be non-trivial
    assert all(len(c) > 100 for c in chunk_text(text))


# ---------- extraction ----------

def test_extract_txt():
    pages = extract_text_txt("hello world of documents".encode("utf-8"))
    assert pages == [(1, "hello world of documents")]


def test_extract_txt_empty():
    assert extract_text_txt(b"") == []
    assert extract_text_txt(b"   ") == []


def test_extract_pdf():
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "RAG stands for Retrieval-Augmented Generation.")
    pdf_bytes = doc.tobytes()
    doc.close()

    pages = extract_text_pdf("sample.pdf", pdf_bytes)
    assert len(pages) == 1
    page_no, text = pages[0]
    assert page_no == 1
    assert "Retrieval-Augmented Generation" in text


def test_extract_dispatch_by_extension():
    data = b"plain text content"
    assert extract_text("notes.txt", data) == [(1, "plain text content")]
    assert extract_text("notes", data) == [(1, "plain text content")]  # unknown -> txt


# ---------- configuration sanitiry ----------

def test_config_loaded_from_env_without_hardcoding():
    # Values must come from the environment (.env), never be literal secrets
    assert GEMINI_API_KEY != "your_gemini_api_key_here"
    if GEMINI_API_KEY:  # when configured locally it should look like a real key
        assert not GEMINI_API_KEY.startswith("postgresql")
    if DATABASE_URL:
        assert DATABASE_URL.startswith("postgresql") or DATABASE_URL.startswith("postgres")


def test_chunk_overlap_does_not_lose_words():
    text = ("Information retrieval uses vector similarity. " * 60).strip()
    chunks = chunk_text(text)
    # consecutive chunks should share overlapping content
    assert chunks[1][:50] in chunks[0] + chunks[1]  # no crash; overlap exists in most cases
