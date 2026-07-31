"""Build, validate and export the plug and inner plug.

    python build.py                 # STEP masters + all STL variants
    python build.py --step-only     # just the nominal STEP masters
    python build.py --fast          # no threads (quick dimensional preview)

Outputs:
    step/plug.step, step/inner_plug.step        nominal masters (zero clearance)
    stl/plug_<variant>.stl, ...                 per-process printable meshes

STL variants apply a radial thread clearance for a running fit. Values are
starting points for the first Bondar Labs test prints; refine once real prints
are trial-fitted. The STEP master is always nominal so the "true" geometry is
never contaminated by a print allowance.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from build123d import export_step, export_stl
from OCP.BRepCheck import BRepCheck_Analyzer

from inner_plug import build_inner_plug
from params import PLUG
from plug import build_plug

HERE = Path(__file__).parent
STEP_DIR = HERE / "step"
STL_DIR = HERE / "stl"

# Radial thread clearance per process (mm). Tune after trial fits.
STL_VARIANTS = {
    "resin": 0.10,   # SLA resolves fine threads well -> tight
    "fdm": 0.25,     # FDM is coarser -> generous
}

# Mesh quality for STL (mm / degrees). Fine enough that helix flanks stay smooth.
STL_LINEAR_TOL = 0.05
STL_ANGULAR_TOL = 0.5

PARTS = {
    "plug": build_plug,
    "inner_plug": build_inner_plug,
}


def _validate(part, label: str) -> None:
    if not BRepCheck_Analyzer(part.wrapped).IsValid():
        raise RuntimeError(f"{label}: BRepCheck reports invalid geometry")
    n = len(part.solids())
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 solid, got {n}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--step-only", action="store_true", help="skip STL export")
    ap.add_argument(
        "--fast",
        action="store_true",
        help="build without threads (fast dimensional preview)",
    )
    args = ap.parse_args()

    STEP_DIR.mkdir(exist_ok=True)
    STL_DIR.mkdir(exist_ok=True)
    threads = not args.fast

    for name, builder in PARTS.items():
        t0 = time.time()
        # ---- STEP master: nominal, zero clearance ------------------------
        master = builder(PLUG, threads=threads, clearance=0.0)
        _validate(master, f"{name} (master)")
        step_path = STEP_DIR / f"{name}.step"
        export_step(master, str(step_path))
        vol = master.volume
        print(
            f"{name}: master volume={vol:.0f} mm^3 valid  "
            f"-> {step_path.relative_to(HERE)}  ({time.time()-t0:.1f}s)"
        )

        if args.step_only or args.fast:
            continue

        # ---- STL variants: per-process clearance -------------------------
        for variant, clr in STL_VARIANTS.items():
            tv = time.time()
            part = builder(PLUG, threads=True, clearance=clr)
            _validate(part, f"{name} ({variant})")
            stl_path = STL_DIR / f"{name}_{variant}.stl"
            export_stl(
                part,
                str(stl_path),
                tolerance=STL_LINEAR_TOL,
                angular_tolerance=STL_ANGULAR_TOL,
            )
            print(
                f"    {variant}: clearance={clr} mm radial "
                f"-> {stl_path.relative_to(HERE)}  ({time.time()-tv:.1f}s)"
            )


if __name__ == "__main__":
    main()
