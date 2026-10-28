import os
import sys
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")


def validate_env() -> None:
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not DATABASE_URL:
        missing.append("DATABASE_URL")
    if missing:
        sys.stderr.write(
            f"[SmartDoc] Missing required environment variables: {', '.join(missing)}\n"
            f"[SmartDoc] Copy .env.example to .env and fill in real values.\n"
        )


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
CHUNK_SIZE = 1000  # characters per chunk
CHUNK_OVERLAP = 150
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
GEN_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]  # try in order
TOP_K = 5
MIN_SIMILARITY = 0.5  # below this, document context is considered insufficient
