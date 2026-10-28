import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from .config import DATABASE_URL, EMBED_DIM


class Db:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.conn.close()


def get_db() -> Db:
    """Open a fresh connection with pgvector types registered."""
    conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
    try:
        register_vector(conn)
    except psycopg.ProgrammingError as exc:
        conn.close()
        raise RuntimeError(
            "The pgvector extension is not installed on this database. "
            "Run init_db() first (it executes CREATE EXTENSION vector). "
            "If that fails, your Postgres host does not support pgvector."
        ) from exc
    return Db(conn)


def init_db() -> None:
    """Create the pgvector extension and tables if they don't exist."""
    # Use a plain connection first: the `vector` type is only available
    # AFTER the extension is created, so register_vector must come later.
    conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
    try:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    except psycopg.Error as exc:
        conn.close()
        raise RuntimeError(
            f"Could not create the pgvector extension on this database: {exc}"
        ) from exc
    finally:
        # close only after successful connect; re-open a fresh one for DDL
        pass
    conn.close()

    with get_db() as db:
        db.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id BIGSERIAL PRIMARY KEY,
                filename TEXT NOT NULL,
                uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        db.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                id BIGSERIAL PRIMARY KEY,
                document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                page_no INT NOT NULL DEFAULT 1,
                content TEXT NOT NULL,
                embedding vector({EMBED_DIM}) NOT NULL
            )
            """
        )
        db.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS chunks_embedding_idx
            ON chunks USING hnsw (embedding vector_cosine_ops)
            """
        )
    print("[SmartDoc] Database ready (pgvector extension + tables created).")
