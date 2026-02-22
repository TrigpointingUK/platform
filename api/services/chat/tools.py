"""
Chat agent tools — vector search over PDF chunks, Text-to-SQL over the
trig/visit database, and direct trig point lookups via the existing
service layer.
"""

import logging
import re
from pathlib import Path
from typing import Any

from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud import locations as locations_crud
from api.crud import trig as trig_crud

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 2000
SQL_MODEL = "gpt-4.1-mini"

_SCHEMA_PROMPT = (
    Path(__file__).parent / "prompts" / "schema_description.txt"
).read_text()

_DISALLOWED_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|COPY)\b",
    re.IGNORECASE,
)


def _get_openai_client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY)


# ── Vector search ────────────────────────────────────────────────────


def vector_search(query: str, db: Session, *, top_k: int = 5) -> list[dict]:
    """Embed *query* and return the top-k most similar document chunks."""
    client = _get_openai_client()
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=query,
        dimensions=EMBEDDING_DIMENSIONS,
    )
    embedding = resp.data[0].embedding
    emb_str = "[" + ",".join(str(v) for v in embedding) + "]"

    rows = db.execute(
        text("""
            SELECT text, metadata_,
                   1 - (embedding <=> CAST(:emb AS vector)) AS similarity
            FROM chat.document_chunk
            WHERE source = 'retriangulation_pdf'
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :top_k
            """),
        {"emb": emb_str, "top_k": top_k},
    ).fetchall()

    results = []
    for row in rows:
        meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
        results.append(
            {
                "text": row.text,
                "page_number": meta.get("page_number"),
                "chapter": meta.get("chapter"),
                "section_type": meta.get("section_type"),
                "trig_ids": meta.get("trig_ids", []),
                "similarity": round(row.similarity, 4),
            }
        )
    return results


# ── Text-to-SQL ──────────────────────────────────────────────────────


def _generate_sql(question: str) -> str:
    """Ask the LLM to turn a natural language question into SQL."""
    client = _get_openai_client()
    resp = client.chat.completions.create(
        model=SQL_MODEL,
        messages=[
            {"role": "system", "content": _SCHEMA_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0,
        max_tokens=1024,
    )
    raw = (resp.choices[0].message.content or "").strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return raw.strip()


def _validate_sql(sql: str) -> None:
    """Raise ValueError if the SQL contains mutations or multiple statements."""
    if ";" in sql.rstrip(";"):
        raise ValueError("Multiple statements are not allowed.")
    if _DISALLOWED_SQL.search(sql):
        raise ValueError("Only SELECT queries are permitted.")
    if not sql.strip().upper().startswith("SELECT"):
        raise ValueError("Query must be a SELECT statement.")


def _format_results(columns: list[str], rows: Any, sql: str) -> str:
    """Return a human-readable table of query results."""
    if not rows:
        return f"Query returned no results.\n\nSQL: {sql}"

    # Cap output rows to avoid huge payloads
    capped = rows[:50]
    lines = [" | ".join(columns)]
    lines.append("-+-".join("-" * max(len(c), 6) for c in columns))
    for row in capped:
        lines.append(" | ".join(str(v) if v is not None else "NULL" for v in row))

    result = "\n".join(lines)
    if len(rows) > 50:
        result += f"\n\n... {len(rows) - 50} more rows (showing first 50)"
    result += f"\n\nSQL: {sql}"
    return result


def query_database(question: str, db: Session) -> str:
    """Generate SQL from a natural language question, validate, and execute."""
    sql = _generate_sql(question)
    logger.info("Generated SQL: %s", sql)

    try:
        _validate_sql(sql)
    except ValueError as exc:
        return f"Refused to execute query: {exc}\n\nGenerated SQL: {sql}"

    try:
        result = db.execute(text(sql))
        columns = list(result.keys())
        rows = result.fetchall()
        logger.info("SQL returned %d rows", len(rows))
        return _format_results(columns, rows, sql)
    except Exception as exc:
        logger.warning("SQL execution error: %s", exc)
        return f"Query failed: {exc}\n\nSQL: {sql}"


# ── Trig point lookup (uses existing service layer) ──────────────────


def _trig_to_dict(trig: Any) -> dict:
    """Convert a Trig model instance to a serialisable dict."""
    return {
        "waypoint": trig.waypoint,
        "name": trig.name,
        "fb_number": trig.fb_number,
        "type": trig.type_name,
        "category": trig.category_name,
        "condition": trig.condition,
        "town": trig.town,
        "wgs_lat": float(trig.wgs_lat) if trig.wgs_lat else None,
        "wgs_long": float(trig.wgs_long) if trig.wgs_long else None,
        "osgb_gridref": trig.osgb_gridref,
        "historic_use": trig.historic_use,
        "current_use": trig.current_use,
    }


def lookup_trig(query: str, db: Session) -> list[dict]:
    """Look up trig points by name, waypoint, or flush bracket number.

    Uses the existing search service — no LLM-generated SQL, so results
    are guaranteed to be accurate database records.
    """
    query = query.strip()
    if not query:
        return []

    # If it looks like a waypoint (e.g. TP1234), try exact match first
    if re.match(r"^TP\d+$", query, re.IGNORECASE):
        trig = trig_crud.get_trig_by_waypoint(db, query.upper())
        if trig:
            return [_trig_to_dict(trig)]

    results = locations_crud.search_trigpoints_by_name_or_waypoint(db, query, limit=10)
    return [_trig_to_dict(t) for t in results]


# ── Tool definitions for the Responses API ──────────────────────────

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "name": "vector_search",
        "description": (
            "Search the Retriangulation of Great Britain book (PDF) for "
            "information about the history, methods, and stations of the "
            "Ordnance Survey retriangulation programme (1935-1962). "
            "Returns relevant text passages with page numbers and any "
            "linked trig point IDs."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A natural language search query.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5).",
                },
            },
            "required": ["query"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "lookup_trig",
        "description": (
            "Look up a trig point by name, waypoint ID (e.g. TP4250), or "
            "flush bracket number. Returns verified data directly from the "
            "database. ALWAYS use this tool before mentioning any specific "
            "trig point to get its correct waypoint, FB number, location, "
            "and condition. This is faster and more reliable than "
            "query_database for simple trig lookups."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The trig point name, waypoint ID, or FB number "
                        "to search for."
                    ),
                },
            },
            "required": ["query"],
        },
        "strict": False,
    },
    {
        "type": "function",
        "name": "query_database",
        "description": (
            "Query the TrigpointingUK database for structured data about "
            "trig points, visit logs, users, photos, conditions, types, "
            "and locations. Use this for factual/statistical questions "
            "like counts, rankings, recent activity, and lookups by name "
            "or waypoint."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": (
                        "A natural language question about trig point data."
                    ),
                },
            },
            "required": ["question"],
        },
        "strict": False,
    },
]
