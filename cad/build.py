"""Build orchestrator for the CAD model collection.

    python build.py                 # build every component (STEP + STL)
    python build.py plug            # build only the named component(s)
    python build.py --step-only     # STEP masters only, skip STL
    python build.py --fast          # no threads (fast dimensional preview)

Each component under ``models/`` owns its own build recipe (a ``build`` module
exposing ``run(*, threads, skip_stl)``) and writes to the shared ``step/`` and
``stl/`` directories via ``common``. This script just resolves which components
to build and dispatches to them.
"""

from __future__ import annotations

import argparse

from common.paths import ensure_dirs
from models.driver_v1 import build as driver_v1_build
from models.driver_v2 import build as driver_v2_build
from models.plug import build as plug_build

# name -> component build module (each exposes run(*, threads, skip_stl))
COMPONENTS = {
    "plug": plug_build,
    "driver_v1": driver_v1_build,
    "driver_v2": driver_v2_build,
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("components", nargs="*", choices=list(COMPONENTS),
                    help="component(s) to build (default: all)")
    ap.add_argument("--step-only", action="store_true", help="skip STL export")
    ap.add_argument("--fast", action="store_true",
                    help="build without threads (fast dimensional preview)")
    args = ap.parse_args()

    names = args.components or list(COMPONENTS)
    threads = not args.fast
    skip_stl = args.step_only or args.fast

    ensure_dirs()
    for name in names:
        COMPONENTS[name].run(threads=threads, skip_stl=skip_stl)


if __name__ == "__main__":
    main()
