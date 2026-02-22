"""Configuration for the PDF VLM extraction pipeline."""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
JPEG_DIR = OUTPUT_DIR / "jpeg"
PAGES_DIR = OUTPUT_DIR / "pages"
LINKED_DIR = OUTPUT_DIR / "linked"
CHUNKS_DIR = OUTPUT_DIR / "chunks"
PROMPTS_DIR = SCRIPT_DIR / "prompts"

# ── Claude API ───────────────────────────────────────────────────
ANTHROPIC_MODEL = "claude-sonnet-4-6"
MAX_CONCURRENT_REQUESTS = 3

# ── Image conversion ─────────────────────────────────────────────
MAX_IMAGE_EDGE = 3000          # longest edge in pixels
JPEG_QUALITY = 92

# ── Entity linking ───────────────────────────────────────────────
FUZZY_MATCH_THRESHOLD = 85     # rapidfuzz score (0–100)

# ── RAG chunking ─────────────────────────────────────────────────
CHUNK_TARGET_TOKENS = 350
CHUNK_MAX_TOKENS = 500

# ── Database ─────────────────────────────────────────────────────
# Constructed from DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME
# (set by `source scripts/set-db-env-production.sh`),
# falling back to DATABASE_URL from .env if the components aren't set.


def _build_database_url() -> str:
    db_host = os.environ.get("DB_HOST", "")
    db_user = os.environ.get("DB_USER", "")
    if db_host and db_user:
        db_port = os.environ.get("DB_PORT", "5432")
        db_password = os.environ.get("DB_PASSWORD", "")
        db_name = os.environ.get("DB_NAME", "")
        encoded_user = quote_plus(db_user)
        encoded_password = quote_plus(db_password)
        return (
            f"postgresql://{encoded_user}:{encoded_password}"
            f"@{db_host}:{db_port}/{db_name}?sslmode=require"
        )
    return os.environ.get("DATABASE_URL", "")


DATABASE_URL = _build_database_url()
