import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector
from .config import DATABASE_URL, EMBED_DIM

_initialized = False


class Db:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.conn.close()


def get_db() -> Db:
    """Open a fresh connection (simple and reliable under exam load)."""
    conn = psycopg.connect(DATABASE_URL, autocommit=True, row_factory=dict_row)
    register_vector(conn)
    return Db(conn)


db_state = {"pool_ok": False}


def init_db() -> None:
    """Create pgvector extension and tables if they don't exist."""
    with get_db() as db:
        db.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
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
