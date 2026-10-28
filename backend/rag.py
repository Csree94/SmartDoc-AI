from google import genai
from google.genai import types as gtypes
from .config import GEMINI_API_KEY, EMBED_MODEL, EMBED_DIM, GEN_MODEL, CHUNK_SIZE, CHUNK_OVERLAP

_client = genai.Client(api_key=GEMINI_API_KEY)  # type: ignore[arg-type]


# ---------- Document text extraction ----------

def extract_text_pdf(filename: str, data: bytes) -> list[tuple[int, str]]:
    """Return list of (page_number, text) for a PDF."""
    import pymupdf

    pages: list[tuple[int, str]] = []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()
            if text:
                pages.append((i, text))
    return pages


def extract_text_txt(data: bytes) -> list[tuple[int, str]]:
    text = data.decode("utf-8", errors="replace").strip()
    return [(1, text)] if text else []


def extract_text(filename: str, data: bytes) -> list[tuple[int, str]]:
    if filename.lower().endswith(".pdf"):
        return extract_text_pdf(filename, data)
    return extract_text_txt(data)


# ---------- Chunking ----------

def chunk_text(text: str) -> list[str]:
    """Split text into overlapping chunks of ~CHUNK_SIZE characters."""
    text = " ".join(text.split())  # normalize whitespace
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        # try to break at a sentence end near the boundary
        if end < len(text):
            period = text.rfind(". ", start + CHUNK_SIZE // 2, end)
            if period != -1:
                end = period + 1
        chunks.append(text[start:end])
        start = end if end <= start else end - CHUNK_OVERLAP
        if end >= len(text):
            break
    return chunks


# ---------- Embeddings (Gemini) ----------

def embed_texts(texts: list[str]) -> list[list[float]]:
    result = _client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=gtypes.EmbedContentConfig(output_dimensionality=EMBED_DIM),
    )
    embs = [list(e.values) for e in result.embeddings]  # type: ignore[union-attr]
    if len(embs) != len(texts):
        raise RuntimeError("Embedding API returned fewer vectors than inputs")
    return embs


def embed_query(question: str) -> list[float]:
    return embed_texts([question])[0]


# ---------- Generation (Gemini) ----------

SYSTEM_INSTRUCTIONS = (
    "You are SmartDoc AI, a helpful assistant. "
    "You will receive CONTEXT consisting of two clearly labeled parts: "
    "DOCUMENT EXCERPTS (retrieved from documents the user uploaded) and "
    "WEB RESULTS (found on the internet). "
    "Rules: 1) Ground every claim in the provided context. "
    "2) When using document evidence, cite it like [Doc: filename, page N]. "
    "3) When using web evidence, cite it like [Web: title]. "
    "4) Clearly distinguish document evidence from web evidence. "
    "5) If the context is insufficient, say so honestly and explain what is missing."
)


def generate_answer(question: str, doc_context: str, web_context: str) -> str:
    parts = [
        f"QUESTION: {question}\n"
    ]
    if doc_context:
        parts.append(f"DOCUMENT EXCERPTS:\n{doc_context}\n")
    else:
        parts.append("DOCUMENT EXCERPTS:\n(none - no relevant document content found)\n")
    if web_context:
        parts.append(f"WEB RESULTS:\n{web_context}\n")
    else:
        parts.append("WEB RESULTS:\n(none)\n")
    parts.append(
        "Answer the question using the available evidence. Cite sources as instructed."
    )
    response = _client.models.generate_content(
        model=GEN_MODEL,
        contents="\n\n".join(parts),
        config=gtypes.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTIONS,
            temperature=0.2,
        ),
    )
    if not response.text:
        raise RuntimeError("Gemini returned an empty answer")
    return response.text
