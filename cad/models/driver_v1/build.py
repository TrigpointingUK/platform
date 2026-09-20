"""Build recipe for the plug driver tool.

Exposes ``run(*, threads, skip_stl)`` for the top-level orchestrator (the
``threads`` flag is accepted for a uniform interface but the driver has no
threads). Outputs land in the shared dirs:

    step/driver_v1.step     nominal master (single solid)
    stl/driver_v1.stl       printable mesh

There are no per-process thread-clearance variants: the only fit dimension is
the peg bore, a single parameter in ``params.py`` (tune for epoxy vs press),
not a thread allowance.
"""

from __future__ import annotations

import time

from build123d import export_step

from common.export import export_watertight_stl, validate
from common.paths import CAD_DIR, STEP_DIR, STL_DIR
from models.driver_v1.driver_v1 import build_driver_v1


def run(*, threads: bool = True, skip_stl: bool = False) -> None:
    """Build, validate and export the driver tool."""
    t0 = time.time()
    master = build_driver_v1()
    validate(master, "driver_v1 (master)")
    print(f"driver_v1: master volume={master.volume:.0f} mm^3 valid "
          f"({time.time()-t0:.1f}s)")

    step_path = STEP_DIR / "driver_v1.step"
    master.label = "DriverV1"
    export_step(master, str(step_path))
    print(f"    STEP -> {step_path.relative_to(CAD_DIR)}")

    if not skip_stl:
        tv = time.time()
        stl_path = STL_DIR / "driver_v1.stl"
        note = export_watertight_stl(master, stl_path, "driver_v1")
        print(f"    STL [{note}] -> {stl_path.relative_to(CAD_DIR)}  "
              f"({time.time()-tv:.1f}s)")


if __name__ == "__main__":
    from common.paths import ensure_dirs

    ensure_dirs()
    run()
