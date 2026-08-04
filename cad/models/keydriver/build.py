"""Build recipe for the key-storing driver tool.

Same interface as the driver (``run(*, threads, skip_stl)``; the ``threads`` flag
is accepted for a uniform interface but this tool has no threads). Outputs land in
the shared dirs:

    step/keydriver.step     nominal master (single solid)
    stl/keydriver.stl       printable mesh
"""

from __future__ import annotations

import time

from build123d import export_step

from common.export import export_watertight_stl, validate
from common.paths import CAD_DIR, STEP_DIR, STL_DIR
from models.keydriver.keydriver import build_keydriver


def run(*, threads: bool = True, skip_stl: bool = False) -> None:
    """Build, validate and export the key-storing driver tool."""
    t0 = time.time()
    master = build_keydriver()
    validate(master, "keydriver (master)")
    print(f"keydriver: master volume={master.volume:.0f} mm^3 valid "
          f"({time.time()-t0:.1f}s)")

    step_path = STEP_DIR / "keydriver.step"
    master.label = "KeyDriver"
    export_step(master, str(step_path))
    print(f"    STEP -> {step_path.relative_to(CAD_DIR)}")

    if not skip_stl:
        tv = time.time()
        stl_path = STL_DIR / "keydriver.stl"
        note = export_watertight_stl(master, stl_path, "keydriver")
        print(f"    STL [{note}] -> {stl_path.relative_to(CAD_DIR)}  "
              f"({time.time()-tv:.1f}s)")


if __name__ == "__main__":
    from common.paths import ensure_dirs

    ensure_dirs()
    run()
