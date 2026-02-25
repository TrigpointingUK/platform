#!/usr/bin/env python3
"""Convert raw TIFF page scans to JPEGs sized for the Claude Vision API.

Usage:
    python 01_convert_tiffs.py --input-dir /path/to/tiffs

The TIFFs are expected to be named in a way that sorts into page order
(e.g. page_001.tif, 001.tif, or any naming where lexicographic sort
gives the correct sequence).

Output:  extraction/output/jpeg/001.jpg … 441.jpg
"""

import argparse
import sys
import time
from pathlib import Path

from PIL import Image

from config import JPEG_DIR, JPEG_QUALITY, MAX_IMAGE_EDGE

TIFF_EXTENSIONS = {".tif", ".tiff"}


def collect_tiffs(input_dir: Path) -> list[Path]:
    """Return TIFF files from *input_dir*, sorted by name."""
    files = sorted(
        f for f in input_dir.iterdir()
        if f.suffix.lower() in TIFF_EXTENSIONS and f.is_file()
    )
    return files


def convert_one(src: Path, dst: Path) -> tuple[int, int, int]:
    """Convert a single TIFF to JPEG, returning (width, height, file_bytes)."""
    with Image.open(src) as img:
        img = img.convert("RGB")

        w, h = img.size
        long_edge = max(w, h)
        if long_edge > MAX_IMAGE_EDGE:
            scale = MAX_IMAGE_EDGE / long_edge
            new_w = int(w * scale)
            new_h = int(h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        img.save(dst, "JPEG", quality=JPEG_QUALITY)

    size_bytes = dst.stat().st_size
    return img.size[0], img.size[1], size_bytes


def main():
    parser = argparse.ArgumentParser(
        description="Convert TIFF page scans to JPEG for Claude Vision API"
    )
    parser.add_argument(
        "--input-dir", required=True, type=Path,
        help="Directory containing the raw TIFF files",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-convert even if the JPEG already exists",
    )
    args = parser.parse_args()

    input_dir = args.input_dir.expanduser().resolve()
    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    tiffs = collect_tiffs(input_dir)
    if not tiffs:
        print(f"No TIFF files found in {input_dir}", file=sys.stderr)
        sys.exit(1)

    JPEG_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(tiffs)} TIFF files in {input_dir}")
    print(f"Output: {JPEG_DIR}")
    print(f"Max edge: {MAX_IMAGE_EDGE}px, JPEG quality: {JPEG_QUALITY}")
    print()

    converted = 0
    skipped = 0
    failed = 0
    total_bytes = 0
    t0 = time.monotonic()

    for i, tiff_path in enumerate(tiffs, start=1):
        page_num = f"{i:03d}"
        dst = JPEG_DIR / f"{page_num}.jpg"

        if dst.exists() and not args.force:
            skipped += 1
            continue

        try:
            w, h, nbytes = convert_one(tiff_path, dst)
            converted += 1
            total_bytes += nbytes
            print(f"  [{page_num}/{len(tiffs)}] {tiff_path.name} → {dst.name}  "
                  f"{w}×{h}  {nbytes / 1024:.0f} KB")
        except Exception as exc:
            failed += 1
            print(f"  [{page_num}/{len(tiffs)}] FAILED {tiff_path.name}: {exc}",
                  file=sys.stderr)

    elapsed = time.monotonic() - t0
    print()
    print(f"Done in {elapsed:.1f}s")
    print(f"  Converted: {converted}")
    print(f"  Skipped:   {skipped} (already exist)")
    print(f"  Failed:    {failed}")
    print(f"  Total size: {total_bytes / (1024 * 1024):.1f} MB")


if __name__ == "__main__":
    main()
