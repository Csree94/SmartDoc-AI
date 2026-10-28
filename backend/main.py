import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import validate_env, TOP_K, MIN_SIMILARITY
from .db import init_db, get_db
from . import rag

validate_env()

app = FastAPI(title="SmartDoc AI", description="AI chatbot with RAG and web search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=4)


async def run_in_thread(func, *args):
    return await asyncio.get_running_loop().run_in_executor(_executor, func, *args)


@app.on_event("startup")
def startup() -> None:
    try:
        init_db()
    except Exception as exc:  # connection problems must be visible, never hidden
        raise RuntimeError(
            f"Could not connect to Neon Postgres. Check DATABASE_URL in .env. Details: {exc}"
        ) from exc


@app.get("/health")
def health():
    try:
        with get_db() as db:
            n = db.conn.execute(
                "SELECT COUNT(*) AS n FROM documents"
            ).fetchone()["n"]
        return {"status": "ok", "documents_indexed": n}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database error: {exc}")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    filename = file.filename or "unknown"
    if not filename.lower().endswith((".pdf", ".txt")):
        raise HTTPException(status_code=400, detail="Only PDF and TXT files are supported.")

    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File is larger than 10 MB.")

    try:
        pages = await run_in_thread(rag.extract_text, filename, data)
        if not pages:
            raise HTTPException(status_code=400, detail="No readable text found in the file (it may be a scanned PDF).")

        doc_id = await run_in_thread(_index_document, filename, pages)
        with get_db() as db:
            row = db.conn.execute(
                "SELECT COUNT(*) AS n FROM chunks WHERE document_id = %s", (doc_id,)
            ).fetchone()
        return {
            "status": "indexed",
            "filename": filename,
            "pages": len(pages),
            "chunks": row["n"],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}")


def _index_document(filename: str, pages: list[tuple[int, str]]) -> int:
    with get_db() as db:
        row = db.conn.execute(
            "INSERT INTO documents (filename) VALUES (%s) RETURNING id", (filename,)
        ).fetchone()
        doc_id = row["id"]
        batch: list[tuple[int, str, str]] = []
        chunk_total = 0
        for page_no, text in pages:
            for chunk in rag.chunk_text(text):
                batch.append((doc_id, page_no, chunk))
        for i in range(0, len(batch), 32):
            part = batch[i : i + 32]
            contents = [p[2] for p in part]
            embeddings = rag.embed_texts(contents)
            insert_rows = [
                (p[0], p[1], p[2], e) for p, e in zip(part, embeddings)
            ]
            db.conn.executemany(
                "INSERT INTO chunks (document_id, page_no, content, embedding) VALUES (%s, %s, %s, %s)",
                insert_rows,
            )
            chunk_total += len(insert_rows)
        return doc_id


class ChatRequest(BaseModel):
    question: str


@app.post("/chat")
async def chat(body: ChatRequest):
    question = (body.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is empty.")

    try:
        answer, used_web, doc_sources, web_sources = await run_in_thread(_answer_question, question)
        return {
            "answer": answer,
            "used_web_search": used_web,
            "doc_sources": doc_sources,
            "web_sources": web_sources,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error generating answer: {exc}")


FORCE_WEB_PATTERNS = (
    "search the internet", "search the web", "browse the web", "latest", "today",
    "current", "news", "weather", "stock price", "real-time", "online", "internet",
)


def _answer_question(question: str):
    # 1. Embed the question and retrieve the top document chunks (real vector search)
    qvec = rag.embed_query(question)
    with get_db() as db:
        rows = db.conn.execute(
            """
            SELECT c.id, c.content, c.page_no, d.filename, 1 - (c.embedding <=> %s::vector) AS similarity
            FROM chunks c JOIN documents d ON d.id = c.document_id
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            (qvec, qvec, TOP_K),
        ).fetchall()

    doc_rows = [r for r in rows if r["similarity"] is not None and r["similarity"] >= MIN_SIMILARITY]

    force_web = any(p in question.lower() for p in FORCE_WEB_PATTERNS)

    doc_context = ""
    doc_sources: list[dict] = []
    if doc_rows:
        lines = []
        for r in doc_rows:
            lines.append(f"[Doc: {r['filename']}, page {r['page_no']}]\n{r['content']}")
            doc_sources.append(
                {"filename": r["filename"], "page": r["page_no"], "similarity": round(r["similarity"], 3)}
            )
        doc_context = "\n\n".join(lines)

    sufficient = len(doc_rows) > 0 and doc_rows[0]["similarity"] >= MIN_SIMILARITY

    # 2. Web search if document context is insufficient OR the user asked for the internet
    web_sources: list[dict] = []
    web_context = ""
    used_web = False
    if force_web or not sufficient:
        try:
            web_sources, web_context = _web_search(question)
            used_web = bool(web_sources)
        except Exception as exc:
            # A failed web search must not break the answer from documents
            print(f"[SmartDoc] Web search failed (continuing without it): {exc}")

    # 3. Generate the grounded answer
    answer = rag.generate_answer(question, doc_context, web_context)
    return answer, used_web, doc_sources, web_sources


def _web_search(question: str) -> tuple[list[dict], str]:
    from ddgs import DDGS

    results = DDGS().text(question, max_results=5)
    sources = [{"title": r["title"], "url": r["href"]} for r in results]
    context_lines = [
        f"[Web: {r['title']}]\n{r['body']}" for r in results
    ]
    return sources, "\n\n".join(context_lines)
