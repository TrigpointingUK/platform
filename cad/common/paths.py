"""Shared filesystem anchors for the CAD build.

Resolved once from this file's location so every model and the build
orchestrator agree on where output and shared assets live, regardless of the
current working directory. Anchoring here (rather than per-module ``__file__``
arithmetic) means moving a model deeper in the tree can never silently break a
relative path.
"""

from __future__ import annotations

from pathlib import Path

CAD_DIR = Path(__file__).resolve().parents[1]  # cad/
REPO_ROOT = CAD_DIR.parent  # platform/
STEP_DIR = CAD_DIR / "step"  # shared, component-prefixed filenames
STL_DIR = CAD_DIR / "stl"


def ensure_dirs() -> None:
    """Create the shared output directories if they do not yet exist."""
    STEP_DIR.mkdir(exist_ok=True)
    STL_DIR.mkdir(exist_ok=True)
