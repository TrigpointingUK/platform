"""Build recipe for the flush-bracket component.

Exposes ``run(*, threads, skip_stl)`` for the top-level orchestrator. Outputs
land in the shared ``step/``/``stl/`` dirs with component-prefixed filenames:

    step/flush_bracket.step             the 1:1 master, full casting
    stl/flush_bracket_<variant>_<scale>.stl

``threads`` is accepted and ignored -- the bracket has none -- so the component
still satisfies the orchestrator's interface.

Scale is applied to the **B-rep**, before meshing, so the chord tolerance in
``common.export`` does the right thing without being told about scale: a 1:5
model has five-times-smaller features and therefore gets proportionally fewer
facets. Meshing one master and scaling the mesh afterwards would instead carry
1:1 facet counts into every reduction, which is where the file sizes would have
run away once there is one of these per trigpoint.
"""

from __future__ import annotations

import time

from build123d import export_step, scale

from common.export import export_watertight_stl, validate
from common.paths import CAD_DIR, STEP_DIR, STL_DIR
from models.flush_bracket.brackets import resolve as resolve_bracket
from models.flush_bracket.flush_bracket import build_flush_bracket

# Printable variants. The full casting is the honest object; the plate-only
# version drops everything behind the front plate, which is what most people
# will actually want to hang on a wall (and prints without support).
ALL_VARIANTS = {
    "full": dict(keying=True),
    "plate": dict(keying=False),
}

# Reduction ratios offered. 1 is the real bracket.
ALL_SCALES = [1, 2, 5, 10]

# Which brackets to build. None is the generic one -- style defaults and no
# number. Any other entry is looked up in brackets.toml, so it carries whatever
# has been measured for that particular casting.
#
# A specimen set covering every lettering style, so the styles can be compared
# side by side rather than one at a time:
#
#   2990    2gl          bare number, no prefix
#   S1852   s-early      lighter, smaller legend
#   S3353   bsm          North Ockendon -- B S M, bare number, measured
#   S3701   s-late       bold, S prefix
#   S7659   s-late       a second, to see a different digit set
#   10603   five-digit   no prefix, narrower digits
#   12351   five-digit   a second
NUMBERS: list[str | None] = [
    None, "2990", "S1852", "S3353", "S3701", "S7659", "10603", "12351",
]

# ---- Development setting -------------------------------------------------
# While the lettering is still being worked out there is no point re-exporting
# eight meshes on every run: the reductions are a pure function of the 1:1
# master, and the plate variant differs only behind the front face. Restrict
# the build to the one mesh worth looking at. Set to None for the full set
# before shipping anything.
DEV_ONLY = ("full", 1)

VARIANTS = ALL_VARIANTS if DEV_ONLY is None else {DEV_ONLY[0]: ALL_VARIANTS[DEV_ONLY[0]]}
SCALES = ALL_SCALES if DEV_ONLY is None else [DEV_ONLY[1]]


def run(*, threads: bool = True, skip_stl: bool = False) -> None:
    """Build, validate and export the flush bracket."""
    del threads  # no threaded features on this part

    for number in NUMBERS:
        _build_one(number, skip_stl=skip_stl)


def _build_one(number: str | None, *, skip_stl: bool) -> None:
    tag = "" if number is None else f"_{number}"
    label = "generic" if number is None else number
    resolved = resolve_bracket(number)
    p = resolved.params
    if number is not None:
        who = f" -- {resolved.name}" if resolved.name else ""
        print(f"flush_bracket [{label}]{who}: style {resolved.style.name}, "
              f"plate reads {resolved.legend!r}")
        print(f"    from {' + '.join(resolved.applied)}")

    t0 = time.time()
    master = build_flush_bracket(number=number, keying=True)
    validate(master, f"flush_bracket ({label}) master")
    bb = master.bounding_box()
    print(
        f"flush_bracket: master volume={master.volume:.0f} mm^3 valid, "
        f"{bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm "
        f"({time.time() - t0:.1f}s)"
    )
    print(
        f"    plate {p.w} x {p.h} mm, bead r{p.bead_r} "
        f"-> {p.w + 2 * p.bead_r} x {p.h + 2 * p.bead_r} mm overall"
    )

    master.label = "FlushBracket"
    step_path = STEP_DIR / f"flush_bracket{tag}.step"
    export_step(master, str(step_path))
    print(f"    master -> {step_path.relative_to(CAD_DIR)}")

    if skip_stl:
        return

    for variant, kwargs in VARIANTS.items():
        part = master if kwargs["keying"] else build_flush_bracket(
            number=number, **kwargs)
        validate(part, f"flush_bracket ({label} {variant})")
        for ratio in SCALES:
            tv = time.time()
            sized = part if ratio == 1 else scale(part, by=1 / ratio)
            stl_path = STL_DIR / f"flush_bracket{tag}_{variant}_1-{ratio}.stl"
            note = export_watertight_stl(
                sized, stl_path, f"flush_bracket ({label} {variant} 1:{ratio})"
            )
            kb = stl_path.stat().st_size / 1024
            print(
                f"    {variant} 1:{ratio}: [{note}] {kb:,.0f} kB "
                f"-> {stl_path.relative_to(CAD_DIR)}  ({time.time() - tv:.1f}s)"
            )


if __name__ == "__main__":
    from common.paths import ensure_dirs

    ensure_dirs()
    run()
