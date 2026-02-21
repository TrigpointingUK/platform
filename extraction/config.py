"""Configuration for the PDF VLM extraction pipeline."""

import os
from pathlib import Path

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
DATABASE_URL = os.environ.get("DATABASE_URL", "")
