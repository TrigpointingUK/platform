#!/usr/bin/env python3
"""Terminal-based spot-check tool for reviewing extraction quality.

Usage:
    python 05_review.py                # random page
    python 05_review.py --page 42      # specific page
    python 05_review.py --diagrams     # only diagram pages
    python 05_review.py --unmatched    # pages with unmatched trig names
    python 05_review.py --errors       # pages with JSON parse errors
    python 05_review.py --stats        # print summary statistics only

Flagged pages are recorded in output/review_flags.json.
"""

import argparse
import json
import random
import sys
import textwrap
from pathlib import Path

from config import JPEG_DIR, LINKED_DIR, PAGES_DIR

FLAGS_FILE = LINKED_DIR.parent / "review_flags.json"
TERM_WIDTH = 80


def load_flags() -> dict:
    if FLAGS_FILE.exists():
        return json.loads(FLAGS_FILE.read_text(encoding="utf-8"))
    return {"flagged": [], "accepted": []}


def save_flags(flags: dict):
    FLAGS_FILE.write_text(
        json.dumps(flags, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def page_source_dir() -> Path:
    """Use linked pages if available, otherwise raw pages."""
    if any(LINKED_DIR.glob("*.json")):
        return LINKED_DIR
    return PAGES_DIR


def load_page(page_num: int) -> dict | None:
    src = page_source_dir()
    path = src / f"{page_num:03d}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def all_page_nums() -> list[int]:
    src = page_source_dir()
    nums = []
    for f in sorted(src.glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            nums.append(int(f.stem))
        except ValueError:
            continue
    return nums


def filter_pages(mode: str) -> list[int]:
    """Return page numbers matching the filter mode."""
    nums = all_page_nums()
    if mode == "all":
        return nums

    filtered = []
    for n in nums:
        data = load_page(n)
        if data is None:
            continue

        if mode == "diagrams":
            if data.get("page_type") in ("diagram", "map", "mixed"):
                filtered.append(n)
            elif any(
                s.get("type") in ("diagram", "map")
                for s in data.get("sections", [])
            ):
                filtered.append(n)

        elif mode == "unmatched":
            mentions = data.get("trig_points_mentioned", [])
            if any(m.get("match_type") == "unmatched" for m in mentions):
                filtered.append(n)

        elif mode == "errors":
            if data.get("_parse_error"):
                filtered.append(n)

    return filtered


def format_section(section: dict, indent: int = 2) -> str:
    """Pretty-print a single section for terminal display."""
    pad = " " * indent
    stype = section.get("type", "unknown")
    lines = [f"{pad}[{stype.upper()}]"]

    if stype == "prose":
        heading = section.get("heading")
        if heading:
            lines.append(f"{pad}  Heading: {heading}")
        text = section.get("text", "")
        # Show first 300 chars
        preview = text[:300]
        if len(text) > 300:
            preview += " …"
        for line in preview.split("\n"):
            lines.append(f"{pad}  {line}")

    elif stype == "table":
        cap = section.get("caption") or section.get("table_number", "")
        desc = section.get("description", "")
        rows = section.get("rows", [])
        lines.append(f"{pad}  Caption: {cap}")
        if desc:
            lines.append(f"{pad}  {desc}")
        lines.append(f"{pad}  {len(rows)} rows")

    elif stype in ("diagram", "map"):
        fig = section.get("figure_number", "")
        cap = section.get("caption", "")
        desc = section.get("description", "")
        annot = section.get("annotations", [])
        if fig:
            lines.append(f"{pad}  {fig}: {cap}")
        elif cap:
            lines.append(f"{pad}  {cap}")
        if desc:
            wrapped = textwrap.fill(desc, width=TERM_WIDTH - indent - 4)
            for wl in wrapped.split("\n"):
                lines.append(f"{pad}  {wl}")
        if annot:
            lines.append(f"{pad}  Annotations: {', '.join(str(a) for a in annot)}")

    elif stype == "photograph":
        cap = section.get("caption", "")
        desc = section.get("description", "")
        lines.append(f"{pad}  {cap}")
        if desc:
            lines.append(f"{pad}  {desc[:200]}")

    elif stype == "footnote":
        marker = section.get("marker", "")
        text = section.get("text", "")
        lines.append(f"{pad}  [{marker}] {text[:200]}")

    return "\n".join(lines)


def display_page(page_num: int, data: dict):
    """Print a formatted review of one page."""
    print()
    print("=" * TERM_WIDTH)
    print(f"  PAGE {page_num:03d}")
    print("=" * TERM_WIDTH)

    jpeg = JPEG_DIR / f"{page_num:03d}.jpg"
    if jpeg.exists():
        print(f"  Image: {jpeg}")
    else:
        print(f"  Image: (not found)")

    if data.get("_parse_error"):
        print()
        print("  *** JSON PARSE ERROR ***")
        raw = data.get("_raw_response", "")
        print(f"  Raw response ({len(raw)} chars):")
        print(f"    {raw[:500]}")
        return

    print(f"  Type:    {data.get('page_type', '?')}")
    print(f"  Chapter: {data.get('chapter') or '(none)'}")
    print()

    # Sections
    sections = data.get("sections", [])
    if sections:
        print(f"  Sections ({len(sections)}):")
        for sec in sections:
            print(format_section(sec))
            print()

    # Trig mentions
    mentions = data.get("trig_points_mentioned", [])
    if mentions:
        print(f"  Trig points mentioned ({len(mentions)}):")
        for m in mentions:
            name = m.get("name", "?")
            conf = m.get("confidence", "?")
            ctx = m.get("context", "")
            match_type = m.get("match_type", "")
            matched = m.get("matched_name", "")
            tid = m.get("trig_id", "")

            match_str = ""
            if match_type == "exact":
                match_str = f"  -> #{tid}"
            elif match_type == "fuzzy":
                score = m.get("match_score", 0)
                match_str = f"  ~> {matched} #{tid} ({score}%)"
            elif match_type == "unmatched":
                match_str = "  !! UNMATCHED"

            print(f"    {name} (conf={conf}, {ctx}){match_str}")
        print()

    # Connections
    connections = data.get("trig_connections", [])
    if connections:
        print(f"  Connections ({len(connections)}):")
        for c in connections:
            f_id = c.get("from_trig_id", "")
            t_id = c.get("to_trig_id", "")
            id_str = ""
            if f_id or t_id:
                id_str = f"  [#{f_id} -> #{t_id}]"
            print(f"    {c.get('from', '?')} — {c.get('to', '?')} "
                  f"({c.get('type', '?')}){id_str}")
        print()


def print_stats():
    """Print aggregate statistics across all pages."""
    nums = all_page_nums()
    type_counts: dict[str, int] = {}
    total_mentions = 0
    total_connections = 0
    pages_with_trigs = 0
    parse_errors = 0
    match_types: dict[str, int] = {}

    for n in nums:
        data = load_page(n)
        if data is None:
            continue
        if data.get("_parse_error"):
            parse_errors += 1
            continue

        ptype = data.get("page_type", "unknown")
        type_counts[ptype] = type_counts.get(ptype, 0) + 1

        mentions = data.get("trig_points_mentioned", [])
        connections = data.get("trig_connections", [])
        total_mentions += len(mentions)
        total_connections += len(connections)
        if mentions:
            pages_with_trigs += 1

        for m in mentions:
            mt = m.get("match_type", "unknown")
            match_types[mt] = match_types.get(mt, 0) + 1

    print()
    print(f"Total pages:        {len(nums)}")
    print(f"Parse errors:       {parse_errors}")
    print()
    print("Page types:")
    for pt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {pt:<15s} {count:>4d}")
    print()
    print(f"Pages with trig mentions: {pages_with_trigs}")
    print(f"Total trig mentions:      {total_mentions}")
    print(f"Total connections:        {total_connections}")
    print()
    if match_types:
        print("Match types:")
        for mt, count in sorted(match_types.items(), key=lambda x: -x[1]):
            print(f"  {mt:<15s} {count:>4d}")

    flags = load_flags()
    print()
    print(f"Flagged pages:   {len(flags.get('flagged', []))}")
    print(f"Accepted pages:  {len(flags.get('accepted', []))}")


def interactive_review(page_nums: list[int], randomise: bool = True):
    """Review pages interactively, prompting for accept/flag/skip."""
    if randomise:
        random.shuffle(page_nums)

    flags = load_flags()

    print(f"\n{len(page_nums)} pages to review.  Commands: [a]ccept, [f]lag, [s]kip, [q]uit\n")

    for page_num in page_nums:
        data = load_page(page_num)
        if data is None:
            continue

        display_page(page_num, data)

        while True:
            try:
                choice = input("\n  [a/f/s/q] > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                save_flags(flags)
                return

            if choice in ("a", "accept"):
                if page_num not in flags["accepted"]:
                    flags["accepted"].append(page_num)
                if page_num in flags["flagged"]:
                    flags["flagged"].remove(page_num)
                save_flags(flags)
                print(f"  Page {page_num} accepted.")
                break
            elif choice in ("f", "flag"):
                if page_num not in flags["flagged"]:
                    flags["flagged"].append(page_num)
                if page_num in flags["accepted"]:
                    flags["accepted"].remove(page_num)
                save_flags(flags)
                print(f"  Page {page_num} flagged for re-extraction.")
                break
            elif choice in ("s", "skip"):
                break
            elif choice in ("q", "quit"):
                save_flags(flags)
                print("  Review saved.")
                return
            else:
                print("  Unknown command. Use a/f/s/q.")


def main():
    parser = argparse.ArgumentParser(description="Review extraction quality")
    parser.add_argument("--page", type=int, help="Review a specific page")
    parser.add_argument("--diagrams", action="store_true", help="Only diagram pages")
    parser.add_argument("--unmatched", action="store_true", help="Pages with unmatched trigs")
    parser.add_argument("--errors", action="store_true", help="Pages with parse errors")
    parser.add_argument("--stats", action="store_true", help="Print summary statistics")
    args = parser.parse_args()

    if not any(page_source_dir().glob("*.json")):
        print("No page JSONs found. Run the extraction pipeline first.",
              file=sys.stderr)
        sys.exit(1)

    if args.stats:
        print_stats()
        return

    if args.page is not None:
        data = load_page(args.page)
        if data is None:
            print(f"Page {args.page} not found.", file=sys.stderr)
            sys.exit(1)
        display_page(args.page, data)
        return

    if args.diagrams:
        page_nums = filter_pages("diagrams")
        mode_label = "diagram"
    elif args.unmatched:
        page_nums = filter_pages("unmatched")
        mode_label = "unmatched"
    elif args.errors:
        page_nums = filter_pages("errors")
        mode_label = "error"
    else:
        page_nums = all_page_nums()
        mode_label = "all"

    if not page_nums:
        print(f"No {mode_label} pages found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(page_nums)} {mode_label} pages")
    interactive_review(page_nums)


if __name__ == "__main__":
    main()
