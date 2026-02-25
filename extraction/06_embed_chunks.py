#!/usr/bin/env python3
"""
Step 6 — Embed chunks via OpenAI and insert into chat.document_chunk.

Reads all_chunks.jsonl produced by 04_build_chunks.py, generates embeddings
with text-embedding-3-large (2000 dimensions), and upserts each row into
the chat.document_chunk table.

Resumable: skips chunks that already exist (keyed on source + page_number).

Usage:
    source scripts/set-db-env-staging.sh   # or production
    export OPENAI_API_KEY=sk-...
    python extraction/06_embed_chunks.py
"""

import json
import logging
import sys
import time

import psycopg2
import psycopg2.extras
from config import CHUNKS_DIR, DATABASE_URL
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
log = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 2000
BATCH_SIZE = 100
SOURCE_TAG = "retriangulation_pdf"
CHUNKS_FILE = CHUNKS_DIR / "all_chunks.jsonl"


def load_chunks():
    """Load all chunks from the JSONL file."""
    chunks = []
    with open(CHUNKS_FILE) as f:
        for line in f:
            chunks.append(json.loads(line))
    log.info("Loaded %d chunks from %s", len(chunks), CHUNKS_FILE)
    return chunks


def get_existing_pages(conn):
    """Return the set of (source, page_number) pairs already in the table."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT source, metadata_->>'page_number' "
            "FROM chat.document_chunk WHERE source = %s",
            (SOURCE_TAG,),
        )
        return {(row[0], row[1]) for row in cur.fetchall()}


def embed_batch(client, texts):
    """Call the OpenAI embedding API for a batch of texts."""
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    return [item.embedding for item in response.data]


def insert_chunks(conn, rows):
    """Bulk-insert rows into chat.document_chunk."""
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO chat.document_chunk (source, text, embedding, metadata_)
            VALUES %s
            """,
            rows,
            template="(%s, %s, %s::vector, %s::jsonb)",
            page_size=BATCH_SIZE,
        )
    conn.commit()


def main():
    if not DATABASE_URL:
        log.error("DATABASE_URL is not configured. Source the DB env script first.")
        sys.exit(1)

    client = OpenAI()

    chunks = load_chunks()

    conn = psycopg2.connect(DATABASE_URL)
    try:
        existing = get_existing_pages(conn)
        log.info("Found %d existing chunks in database", len(existing))

        to_embed = []
        for i, chunk in enumerate(chunks):
            page = str(chunk["metadata"].get("page_number", ""))
            if (SOURCE_TAG, page) in existing:
                continue
            to_embed.append((i, chunk))

        log.info(
            "%d chunks to embed (%d already present)",
            len(to_embed),
            len(chunks) - len(to_embed),
        )

        if not to_embed:
            log.info("Nothing to do — all chunks already embedded.")
            return

        total_tokens = 0
        for batch_start in range(0, len(to_embed), BATCH_SIZE):
            batch = to_embed[batch_start : batch_start + BATCH_SIZE]
            texts = [c["text"] for _, c in batch]

            t0 = time.time()
            embeddings = embed_batch(client, texts)
            elapsed = time.time() - t0

            rows = []
            for (idx, chunk), emb in zip(batch, embeddings):
                emb_str = "[" + ",".join(str(v) for v in emb) + "]"
                rows.append(
                    (
                        SOURCE_TAG,
                        chunk["text"],
                        emb_str,
                        json.dumps(chunk["metadata"]),
                    )
                )

            insert_chunks(conn, rows)

            batch_tokens = sum(
                c.get("metadata", {}).get("estimated_tokens", 350) for _, c in batch
            )
            total_tokens += batch_tokens

            log.info(
                "Batch %d–%d: embedded %d chunks in %.1fs (~%d tokens)",
                batch_start,
                batch_start + len(batch) - 1,
                len(batch),
                elapsed,
                batch_tokens,
            )

        cost = total_tokens / 1_000_000 * 0.13
        log.info(
            "Done. Embedded %d chunks (~%d tokens, est. $%.4f)",
            len(to_embed),
            total_tokens,
            cost,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
