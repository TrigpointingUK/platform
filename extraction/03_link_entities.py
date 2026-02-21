#!/usr/bin/env python3
"""Link extracted trig point names to database records.

Usage:
    python 03_link_entities.py

Requires DATABASE_URL in the environment (or .env file).

Reads:   extraction/output/pages/*.json
Writes:  extraction/output/linked/*.json
         extraction/output/linked/_match_report.json
"""

import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from rapidfuzz import fuzz, process

from config import FUZZY_MATCH_THRESHOLD, LINKED_DIR, PAGES_DIR

load_dotenv()


def load_trig_names() -> list[dict]:
    """Fetch all trig records (id, waypoint, name, stn_number) from the DB."""
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("Error: DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)

    import psycopg2

    # Convert SQLAlchemy URL to psycopg2 format if needed
    conn_str = db_url.replace("postgresql+psycopg2://", "postgresql://")

    conn = psycopg2.connect(conn_str)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, waypoint, name, stn_number FROM trig ORDER BY id"
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "id": row[0],
            "waypoint": row[1],
            "name": row[2],
            "stn_number": row[3],
        }
        for row in rows
    ]


def build_lookup(trigs: list[dict]) -> dict:
    """Build lookup structures for exact and fuzzy matching."""
    # Exact name → list of trig records (names are not unique)
    by_name: dict[str, list[dict]] = defaultdict(list)
    for t in trigs:
        by_name[t["name"].strip().lower()].append(t)

    # Also index by waypoint and station number
    by_waypoint: dict[str, dict] = {}
    by_stn: dict[str, dict] = {}
    for t in trigs:
        wp = t["waypoint"].strip().upper()
        if wp:
            by_waypoint[wp] = t
        stn = (t["stn_number"] or "").strip()
        if stn:
            by_stn[stn] = t

    # All names for fuzzy matching
    all_names = [t["name"] for t in trigs]

    return {
        "by_name": by_name,
        "by_waypoint": by_waypoint,
        "by_stn": by_stn,
        "all_names": all_names,
        "all_trigs": trigs,
    }


def match_name(name: str, lookup: dict) -> dict:
    """Match a single extracted name against the database.

    Returns a dict with match_type, candidates, and best match info.
    """
    clean = name.strip()
    lower = clean.lower()

    # 1. Exact match on name
    if lower in lookup["by_name"]:
        matches = lookup["by_name"][lower]
        return {
            "extracted_name": clean,
            "match_type": "exact",
            "trig_id": matches[0]["id"],
            "trig_waypoint": matches[0]["waypoint"],
            "trig_name": matches[0]["name"],
            "score": 100,
            "candidates": [
                {"id": m["id"], "waypoint": m["waypoint"], "name": m["name"]}
                for m in matches
            ],
        }

    # 2. Exact match on waypoint (e.g. "TP1234")
    upper = clean.upper()
    if upper in lookup["by_waypoint"]:
        t = lookup["by_waypoint"][upper]
        return {
            "extracted_name": clean,
            "match_type": "waypoint",
            "trig_id": t["id"],
            "trig_waypoint": t["waypoint"],
            "trig_name": t["name"],
            "score": 100,
            "candidates": [],
        }

    # 3. Station number match
    if clean in lookup["by_stn"]:
        t = lookup["by_stn"][clean]
        return {
            "extracted_name": clean,
            "match_type": "station_number",
            "trig_id": t["id"],
            "trig_waypoint": t["waypoint"],
            "trig_name": t["name"],
            "score": 100,
            "candidates": [],
        }

    # 4. Fuzzy match on name
    results = process.extract(
        clean,
        lookup["all_names"],
        scorer=fuzz.token_sort_ratio,
        limit=3,
    )

    if results and results[0][1] >= FUZZY_MATCH_THRESHOLD:
        # Find the trig record for the best match
        best_name = results[0][0]
        best_score = results[0][1]
        best_trigs = lookup["by_name"].get(best_name.lower(), [])

        candidates = []
        for matched_name, score, _idx in results:
            if score >= FUZZY_MATCH_THRESHOLD:
                for t in lookup["by_name"].get(matched_name.lower(), []):
                    candidates.append({
                        "id": t["id"],
                        "waypoint": t["waypoint"],
                        "name": t["name"],
                        "score": score,
                    })

        return {
            "extracted_name": clean,
            "match_type": "fuzzy",
            "trig_id": best_trigs[0]["id"] if best_trigs else None,
            "trig_waypoint": best_trigs[0]["waypoint"] if best_trigs else None,
            "trig_name": best_name,
            "score": best_score,
            "candidates": candidates,
        }

    # 5. No match
    return {
        "extracted_name": clean,
        "match_type": "unmatched",
        "trig_id": None,
        "trig_waypoint": None,
        "trig_name": None,
        "score": results[0][1] if results else 0,
        "candidates": [
            {
                "id": None,
                "name": r[0],
                "score": r[1],
            }
            for r in (results or [])
        ],
    }


def main():
    t0 = time.monotonic()

    # Load page JSONs
    page_files = sorted(PAGES_DIR.glob("*.json"))
    page_files = [f for f in page_files if not f.name.startswith("_")]
    if not page_files:
        print(f"No page JSONs found in {PAGES_DIR}", file=sys.stderr)
        print("Run 02_extract_pages.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(page_files)} page JSON files")

    # Load trig database
    print("Loading trig records from database …")
    trigs = load_trig_names()
    print(f"  {len(trigs)} trig records loaded")
    lookup = build_lookup(trigs)

    LINKED_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all unique extracted names across all pages
    all_mentions: dict[str, dict] = {}  # name → best match result
    total_mentions = 0
    pages_with_trigs = 0

    for page_file in page_files:
        page_data = json.loads(page_file.read_text(encoding="utf-8"))

        # Skip parse-error pages
        if page_data.get("_parse_error"):
            out_path = LINKED_DIR / page_file.name
            out_path.write_text(
                json.dumps(page_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            continue

        mentions = page_data.get("trig_points_mentioned", [])
        connections = page_data.get("trig_connections", [])

        if mentions:
            pages_with_trigs += 1

        # Match each mention
        linked_mentions = []
        for mention in mentions:
            name = mention.get("name", "")
            if not name:
                continue
            total_mentions += 1

            # Cache match results for repeated names
            if name not in all_mentions:
                all_mentions[name] = match_name(name, lookup)

            result = all_mentions[name]
            linked_mention = {
                **mention,
                "trig_id": result["trig_id"],
                "trig_waypoint": result["trig_waypoint"],
                "matched_name": result["trig_name"],
                "match_type": result["match_type"],
                "match_score": result["score"],
            }
            linked_mentions.append(linked_mention)

        # Enrich connections with trig IDs
        linked_connections = []
        for conn in connections:
            from_name = conn.get("from", "")
            to_name = conn.get("to", "")
            from_match = all_mentions.get(from_name, {})
            to_match = all_mentions.get(to_name, {})
            linked_connections.append({
                **conn,
                "from_trig_id": from_match.get("trig_id"),
                "to_trig_id": to_match.get("trig_id"),
            })

        # Write enriched page JSON
        enriched = {
            **page_data,
            "trig_points_mentioned": linked_mentions,
            "trig_connections": linked_connections,
        }
        out_path = LINKED_DIR / page_file.name
        out_path.write_text(
            json.dumps(enriched, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # Build match report
    exact = sum(1 for m in all_mentions.values() if m["match_type"] == "exact")
    fuzzy = sum(1 for m in all_mentions.values() if m["match_type"] == "fuzzy")
    waypoint = sum(1 for m in all_mentions.values() if m["match_type"] == "waypoint")
    stn = sum(1 for m in all_mentions.values() if m["match_type"] == "station_number")
    unmatched = sum(1 for m in all_mentions.values() if m["match_type"] == "unmatched")

    report = {
        "summary": {
            "total_pages": len(page_files),
            "pages_with_trig_mentions": pages_with_trigs,
            "total_mentions": total_mentions,
            "unique_names": len(all_mentions),
            "exact_matches": exact,
            "fuzzy_matches": fuzzy,
            "waypoint_matches": waypoint,
            "station_number_matches": stn,
            "unmatched": unmatched,
        },
        "unmatched_names": sorted(
            [
                {
                    "name": m["extracted_name"],
                    "best_candidate": m["candidates"][0]["name"] if m["candidates"] else None,
                    "best_score": m["candidates"][0].get("score", 0) if m["candidates"] else 0,
                }
                for m in all_mentions.values()
                if m["match_type"] == "unmatched"
            ],
            key=lambda x: x["name"],
        ),
        "fuzzy_matches": sorted(
            [
                {
                    "extracted": m["extracted_name"],
                    "matched_to": m["trig_name"],
                    "trig_id": m["trig_id"],
                    "score": m["score"],
                }
                for m in all_mentions.values()
                if m["match_type"] == "fuzzy"
            ],
            key=lambda x: x["score"],
        ),
    }

    report_path = LINKED_DIR / "_match_report.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    elapsed = time.monotonic() - t0
    print()
    print(f"Done in {elapsed:.1f}s")
    print(f"  Pages processed:    {len(page_files)}")
    print(f"  Pages with trigs:   {pages_with_trigs}")
    print(f"  Total mentions:     {total_mentions}")
    print(f"  Unique names:       {len(all_mentions)}")
    print(f"    Exact matches:    {exact}")
    print(f"    Fuzzy matches:    {fuzzy}")
    print(f"    Waypoint matches: {waypoint}")
    print(f"    Stn num matches:  {stn}")
    print(f"    Unmatched:        {unmatched}")
    print()
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
