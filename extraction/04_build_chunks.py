#!/usr/bin/env python3
"""Build RAG-ready text chunks from entity-linked page JSONs.

Usage:
    python 04_build_chunks.py

Reads:   extraction/output/linked/*.json
Writes:  extraction/output/chunks/all_chunks.jsonl
"""

import json
import sys
import time
from pathlib import Path

from config import CHUNK_MAX_TOKENS, CHUNK_TARGET_TOKENS, CHUNKS_DIR, LINKED_DIR

APPROX_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return len(text) // APPROX_CHARS_PER_TOKEN


def trig_ids_from_mentions(mentions: list[dict]) -> list[int]:
    """Extract unique, non-null trig IDs from linked mentions."""
    ids = set()
    for m in mentions:
        tid = m.get("trig_id")
        if tid is not None:
            ids.add(tid)
    return sorted(ids)


def split_prose(text: str, target_chars: int, max_chars: int) -> list[str]:
    """Split prose text into chunks at paragraph boundaries.

    Tries to keep chunks near *target_chars*, never exceeding *max_chars*
    (unless a single paragraph is longer, in which case it gets its own chunk).
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = para
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks


def chunk_prose_section(
    section: dict, page_num: int, chapter: str | None, mentions: list[dict]
) -> list[dict]:
    """Create chunks from a prose section."""
    text = section.get("text", "")
    heading = section.get("heading")
    if not text.strip():
        return []

    target_chars = CHUNK_TARGET_TOKENS * APPROX_CHARS_PER_TOKEN
    max_chars = CHUNK_MAX_TOKENS * APPROX_CHARS_PER_TOKEN

    text_parts = split_prose(text, target_chars, max_chars)
    chunks = []
    for i, part in enumerate(text_parts):
        prefix_parts = [f"[Page {page_num}]"]
        if chapter:
            prefix_parts.append(chapter)
        if heading:
            prefix_parts.append(heading)
        prefix = " — ".join(prefix_parts)

        chunk_text = f"{prefix}\n\n{part}"
        chunks.append({
            "text": chunk_text,
            "metadata": {
                "page_number": page_num,
                "chapter": chapter,
                "section_heading": heading,
                "section_type": "prose",
                "chunk_index": i,
                "trig_ids": trig_ids_from_mentions(mentions),
                "estimated_tokens": estimate_tokens(chunk_text),
            },
        })
    return chunks


def chunk_table_section(
    section: dict, page_num: int, chapter: str | None, mentions: list[dict]
) -> list[dict]:
    """Create a chunk from a table section.

    Tables are serialised as a natural-language header followed by
    a compact representation of the rows.
    """
    caption = section.get("caption") or section.get("table_number") or "Untitled table"
    description = section.get("description", "")
    columns = section.get("columns", [])
    rows = section.get("rows", [])

    parts = [f"[Page {page_num}]"]
    if chapter:
        parts.append(chapter)
    parts.append(f"Table: {caption}")
    header = " — ".join(parts)

    lines = [header]
    if description:
        lines.append(description)
    lines.append("")

    if columns and rows:
        lines.append(" | ".join(str(c) for c in columns))
        lines.append("-" * 40)
        for row in rows:
            if isinstance(row, dict):
                vals = [str(row.get(c, "")) for c in columns]
            elif isinstance(row, list):
                vals = [str(v) for v in row]
            else:
                vals = [str(row)]
            lines.append(" | ".join(vals))

    chunk_text = "\n".join(lines)
    return [{
        "text": chunk_text,
        "metadata": {
            "page_number": page_num,
            "chapter": chapter,
            "section_type": "table",
            "table_caption": caption,
            "row_count": len(rows),
            "trig_ids": trig_ids_from_mentions(mentions),
            "estimated_tokens": estimate_tokens(chunk_text),
        },
    }]


def chunk_diagram_section(
    section: dict, page_num: int, chapter: str | None,
    mentions: list[dict], connections: list[dict]
) -> list[dict]:
    """Create a chunk from a diagram/map section.

    Includes the description, all visible station names, and the
    connection topology — this is the highest-value extraction.
    """
    caption = section.get("caption") or section.get("figure_number") or "Untitled diagram"
    description = section.get("description", "")
    annotations = section.get("annotations", [])

    parts = [f"[Page {page_num}]"]
    if chapter:
        parts.append(chapter)
    parts.append(f"Diagram: {caption}")
    header = " — ".join(parts)

    lines = [header]
    if description:
        lines.append("")
        lines.append(description)

    # List station names from this page's mentions
    station_names = [m.get("name", "") for m in mentions if m.get("name")]
    if station_names:
        lines.append("")
        lines.append(f"Stations shown: {', '.join(station_names)}")

    # Connection topology
    if connections:
        lines.append("")
        lines.append("Connections:")
        for c in connections:
            conn_type = c.get("type", "unknown")
            lines.append(f"  {c.get('from', '?')} — {c.get('to', '?')} ({conn_type})")

    if annotations:
        lines.append("")
        lines.append(f"Annotations: {'; '.join(str(a) for a in annotations)}")

    chunk_text = "\n".join(lines)
    return [{
        "text": chunk_text,
        "metadata": {
            "page_number": page_num,
            "chapter": chapter,
            "section_type": "diagram",
            "diagram_caption": caption,
            "station_count": len(station_names),
            "connection_count": len(connections),
            "trig_ids": trig_ids_from_mentions(mentions),
            "estimated_tokens": estimate_tokens(chunk_text),
        },
    }]


def chunk_page(page_data: dict) -> list[dict]:
    """Generate all chunks for a single page."""
    if page_data.get("_parse_error"):
        return []

    page_num = page_data.get("page_number", 0)
    page_type = page_data.get("page_type", "")
    chapter = page_data.get("chapter")
    sections = page_data.get("sections", [])
    mentions = page_data.get("trig_points_mentioned", [])
    connections = page_data.get("trig_connections", [])

    if page_type in ("blank", "front_matter"):
        # Still extract front matter text if present
        if page_type == "blank":
            return []

    chunks = []
    for section in sections:
        section_type = section.get("type", "")

        if section_type == "prose":
            chunks.extend(chunk_prose_section(section, page_num, chapter, mentions))

        elif section_type == "table":
            chunks.extend(chunk_table_section(section, page_num, chapter, mentions))

        elif section_type in ("diagram", "map"):
            chunks.extend(
                chunk_diagram_section(
                    section, page_num, chapter, mentions, connections
                )
            )

        elif section_type == "photograph":
            desc = section.get("description", "")
            cap = section.get("caption", "")
            if desc or cap:
                text = f"[Page {page_num}] Photograph: {cap}\n\n{desc}".strip()
                chunks.append({
                    "text": text,
                    "metadata": {
                        "page_number": page_num,
                        "chapter": chapter,
                        "section_type": "photograph",
                        "trig_ids": trig_ids_from_mentions(mentions),
                        "estimated_tokens": estimate_tokens(text),
                    },
                })

        elif section_type == "footnote":
            # Footnotes are appended to the preceding prose chunk if small,
            # or emitted as their own chunk
            fn_text = section.get("text", "")
            marker = section.get("marker", "")
            if fn_text:
                text = f"[Page {page_num}] Footnote {marker}: {fn_text}"
                chunks.append({
                    "text": text,
                    "metadata": {
                        "page_number": page_num,
                        "chapter": chapter,
                        "section_type": "footnote",
                        "trig_ids": trig_ids_from_mentions(mentions),
                        "estimated_tokens": estimate_tokens(text),
                    },
                })

    return chunks


def main():
    t0 = time.monotonic()

    page_files = sorted(LINKED_DIR.glob("*.json"))
    page_files = [f for f in page_files if not f.name.startswith("_")]
    if not page_files:
        print(f"No linked page JSONs found in {LINKED_DIR}", file=sys.stderr)
        print("Run 03_link_entities.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(page_files)} linked page files")

    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = CHUNKS_DIR / "all_chunks.jsonl"

    all_chunks = []
    type_counts: dict[str, int] = {}
    token_counts: list[int] = []

    for page_file in page_files:
        page_data = json.loads(page_file.read_text(encoding="utf-8"))
        page_chunks = chunk_page(page_data)
        for chunk in page_chunks:
            stype = chunk["metadata"].get("section_type", "unknown")
            type_counts[stype] = type_counts.get(stype, 0) + 1
            token_counts.append(chunk["metadata"].get("estimated_tokens", 0))
        all_chunks.extend(page_chunks)

    # Write JSONL
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    elapsed = time.monotonic() - t0
    avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0

    print()
    print(f"Done in {elapsed:.1f}s")
    print(f"  Total chunks:   {len(all_chunks)}")
    print(f"  Avg tokens:     {avg_tokens:.0f}")
    print(f"  By type:")
    for stype, count in sorted(type_counts.items()):
        print(f"    {stype:<15s} {count}")
    print()
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
