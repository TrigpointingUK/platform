#!/usr/bin/env python3
"""
Count lines in first-party programmatic files under the repository root.

Excludes third-party dependencies (node_modules, venv), bundled or downloaded
data (e.g. CSV under api/data), generated lockfiles, media / HLS assets, and
common build or cache directories. Includes languages used in this monorepo
(Python, TypeScript/JavaScript, Terraform, PHP, SQL, shell, CSS, etc.).

This is a rough productivity metric, not a formal SLOC standard.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path

# Directory names to prune entirely (dependencies, caches, build output).
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        ".nox",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov",
        ".tox",
        ".ruff_cache",
        "dist",
        "build",
        ".vite",
        "storybook-static",
        "cdk.out",
        ".terraform",
        "hls",  # HLS segments (*.ts video), not TypeScript
        "site-packages",  # third-party Python (venv, .tox, etc.)
        "dist-packages",
    }
)

# Filenames to skip (generated or third-party lockfiles).
SKIP_FILENAMES: frozenset[str] = frozenset(
    {
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "Poetry.lock",
        "uv.lock",
    }
)

# Extensions treated as programmatic source for this project.
CODE_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py",
        ".pyi",
        ".tf",
        ".tfvars",
        ".hcl",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".php",
        ".sql",
        ".sh",
        ".bash",
        ".zsh",
        ".css",
        ".scss",
        ".vue",
        ".yaml",
        ".yml",
    }
)

# Exact filenames (no extension) counted as code.
CODE_NAMES: frozenset[str] = frozenset(
    {
        "Makefile",
        "Dockerfile",
        "Containerfile",
    }
)

# Data / dump extensions always skipped.
DATA_EXTENSIONS: frozenset[str] = frozenset({".csv", ".ndjson", ".parquet"})

# Minified bundles usually vendored or generated.
SKIP_SUFFIXES: tuple[str, ...] = (".min.js", ".min.css")


def _is_under_api_data(rel: Path) -> bool:
    parts = rel.parts
    return len(parts) >= 2 and parts[0] == "api" and parts[1] == "data"


def _is_web_public_content(rel: Path, suffix: str) -> bool:
    """YAML/JSON under web/public is treated as static content, not app source."""
    parts = rel.parts
    if len(parts) < 3 or parts[0] != "web" or parts[1] != "public":
        return False
    return suffix in {".yaml", ".yml", ".json"}


def should_count_file(root: Path, path: Path) -> bool:
    """Return True if this file should contribute to the line count."""
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False

    name = path.name
    if name in SKIP_FILENAMES:
        return False

    suffix = path.suffix.lower()
    if suffix in DATA_EXTENSIONS:
        return False
    if _is_under_api_data(rel):
        return False

    lower_name = name.lower()
    for suf in SKIP_SUFFIXES:
        if lower_name.endswith(suf):
            return False

    if _is_web_public_content(rel, suffix):
        return False

    if name in CODE_NAMES:
        return True
    if suffix in CODE_EXTENSIONS:
        return True
    return False


def count_lines_in_file(path: Path) -> int:
    """Count newline-terminated rows (binary-safe, UTF-8 agnostic)."""
    with path.open("rb") as f:
        return sum(1 for _ in f)


def iter_code_files(root: Path) -> list[Path]:
    """Walk the tree and return sorted paths to files that should be counted."""
    root = root.resolve()
    results: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(
        root, topdown=True, followlinks=False, onerror=None
    ):
        dirnames[:] = [
            d
            for d in dirnames
            if d not in SKIP_DIR_NAMES and not d.endswith(".egg-info")
        ]
        current = Path(dirpath)

        try:
            rel_dir = current.relative_to(root)
        except ValueError:
            rel_dir = Path()

        # Skip api/data subtree (CSV and other bundled inputs)
        if _is_under_api_data(rel_dir):
            dirnames.clear()
            continue

        for fn in filenames:
            p = current / fn
            if not p.is_file():
                continue
            if should_count_file(root, p):
                results.append(p)

    return sorted(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Count lines in first-party programmatic files (excludes deps and data).",
        epilog=(
            "Excluded: dependency trees (node_modules, site-packages, venv, .tox, …), "
            "api/data (bundled CSV and similar), HLS media trees, lockfiles, minified JS/CSS, "
            "and YAML/JSON under web/public (static content)."
        ),
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        type=Path,
        help="Repository root (default: current directory)",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 1

    files = iter_code_files(root)
    by_ext: defaultdict[str, int] = defaultdict(int)
    by_lines: defaultdict[str, int] = defaultdict(int)
    total_lines = 0

    for path in files:
        rel = path.relative_to(root)
        try:
            n = count_lines_in_file(path)
        except OSError as e:
            print(f"Skip (unreadable): {rel} ({e})", file=sys.stderr)
            continue
        ext = path.suffix.lower() or path.name
        by_ext[ext] += 1
        by_lines[ext] += n
        total_lines += n

    print(f"Root: {root}")
    print(f"Files: {len(files)}")
    print(f"Total lines: {total_lines}")
    print()
    print("By extension (lines, then files):")
    for ext in sorted(by_lines.keys(), key=lambda k: (-by_lines[k], k)):
        print(f"  {ext:12} {by_lines[ext]:8} lines  ({by_ext[ext]} files)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
