"""True helical thread helpers, form-aware (Whitworth, ISO or printable).

Unlike the render model (bump-maps with no helix angle) these produce real
swept-helix geometry with correct flank angle and lead, suitable for a
functional 3D print.

Thread form is taken from ``ThreadSpec.form``:

* ``"whitworth"`` -- 55 deg BSW form. Built with bd_warehouse's generic
  ``Thread`` from an explicit tooth profile: depth 0.6403 x pitch, with the
  rounded crest/root approximated by flats of ~pitch/6. This is what the real
  OS plug threads measured as.
* ``"iso"`` -- 60 deg ISO metric, via bd_warehouse ``IsoThread``.
* ``"trapezoid"`` -- a 90 deg symmetric form with 45 deg flanks, sized by
  ``ThreadSpec.crest_flat``. Not a real fastener thread: it exists because a
  V-form thread's flanks are a 62.5 deg overhang at *any* pitch, which FDM
  cannot print. See ``_trapezoid_depth``.

Two robustness lessons are baked in here:

* An external thread is created as ``thread + core`` (the helix fused to its
  minor-diameter core). This fuses reliably.
* An internal thread is *not* built by unioning thin helical teeth onto a bore
  wall -- with OCCT that boolean is numerically unstable and can collapse to an
  empty solid. Instead we tap it the way a machinist would: drill to the minor
  diameter, then **subtract an external-thread "tap" tool** to carve the
  grooves. Subtraction of the fused tap is stable.

Printing clearance is applied here, not in ``params.py``: the STEP master is
nominal (zero clearance) and each STL variant dials in a radial allowance so
external threads shrink and tapped holes grow, giving a running fit.
"""

from __future__ import annotations

from dataclasses import dataclass

from build123d import Align, Cylinder, Part, Pos
from bd_warehouse.thread import IsoThread, Thread

from common.specs import ThreadSpec

# Fade both ends so there are no fragile partial teeth or knife-edges.
_ENDS = ("fade", "fade")

# Whitworth (BSW) 55 deg form, as fractions of pitch. Depth 0.6403p; the rib is
# a symmetric trapezoid with a p/6 crest flat and a 5p/6 base, which gives 55 deg
# flanks ((5p/6 - p/6)/2 = p/3 = 0.6403p * tan(27.5 deg)). The crest/root flats
# approximate Whitworth's 0.1373p rounding.
_WHIT_DEPTH = 0.6403
_WHIT_APEX_W = 1.0 / 6.0   # crest flat (narrow, at the major diameter)
_WHIT_ROOT_W = 5.0 / 6.0   # rib base width (at the minor diameter)


def _trapezoid_depth(spec: ThreadSpec) -> float:
    """Radial depth of a ``trapezoid``-form thread.

    The form is a symmetric trapezoid with **45 degree flanks**, defined by the
    pitch and one crest flat ``f``. Ribs and the gaps between them are both
    ``f`` wide at their tips, so the rib base is ``pitch - f`` and each flank
    runs ``(pitch - 2f)/2`` axially -- which, at 45 degrees, is also the depth.

    Why 45 degrees: printed with the axis vertical, a thread flank is an
    overhang, and 45 deg is the steepest an FDM machine holds without support.
    It puts the radial step per layer equal to the layer height, so each
    perimeter lands on roughly half the bead below it. A Whitworth flank is
    62.5 deg *at every pitch* -- depth and axial run both scale with pitch, so
    coarsening a V-form thread never fixes it. Making both flats a whole number
    of extrusion widths keeps crest and root printable too.
    """
    return (spec.pitch - 2.0 * spec.crest_flat) / 2.0


def _external_thread(spec: ThreadSpec, major: float, length: float):
    """Build an external-form thread solid for ``spec`` at the given (already
    clearance-adjusted) ``major`` diameter. Returns ``(thread, min_radius)``."""
    if spec.form == "trapezoid":
        apex_r = major / 2.0
        root_r = apex_r - _trapezoid_depth(spec)
        thread = Thread(
            apex_radius=apex_r,
            apex_width=spec.crest_flat,
            root_radius=root_r,
            root_width=spec.pitch - spec.crest_flat,
            pitch=spec.pitch,
            length=length,
            end_finishes=_ENDS,
        )
        return thread, root_r
    if spec.form == "whitworth":
        apex_r = major / 2.0
        root_r = apex_r - _WHIT_DEPTH * spec.pitch
        thread = Thread(
            apex_radius=apex_r,
            apex_width=_WHIT_APEX_W * spec.pitch,
            root_radius=root_r,
            root_width=_WHIT_ROOT_W * spec.pitch,
            pitch=spec.pitch,
            length=length,
            end_finishes=_ENDS,
        )
        return thread, root_r
    thread = IsoThread(
        major_diameter=major,
        pitch=spec.pitch,
        length=length,
        external=True,
        end_finishes=_ENDS,
        simple=False,
    )
    return thread, thread.min_radius


def external_min_radius(spec: ThreadSpec, clearance: float = 0.0) -> float:
    """Minor radius of the external thread (the core cylinder radius) for
    ``spec`` at the given radial ``clearance``."""
    major = spec.major_diameter - 2.0 * clearance
    if spec.form == "trapezoid":
        return major / 2.0 - _trapezoid_depth(spec)
    if spec.form == "whitworth":
        return major / 2.0 - _WHIT_DEPTH * spec.pitch
    # ISO: cheap probe (min_radius depends only on major & pitch).
    return IsoThread(
        major_diameter=major, pitch=spec.pitch, length=spec.pitch * 2,
        external=True, end_finishes=_ENDS, simple=False,
    ).min_radius


def external_thread_shaft(
    spec: ThreadSpec,
    length: float,
    z_base: float = 0.0,
    clearance: float = 0.0,
) -> Part:
    """A fully threaded external shaft (minor-diameter core + helix), spanning
    ``z_base .. z_base + length``. ``clearance`` (mm, radial) shrinks the major
    diameter for a printed running fit. Fuse onto a part with ``+``."""
    thread, min_r = _external_thread(spec, spec.major_diameter - 2.0 * clearance, length)
    core = Cylinder(
        radius=min_r,
        height=length,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return Pos(0, 0, z_base) * (thread + core)


def keep_largest_solid(part: Part) -> Part:
    """Return ``part`` reduced to its single largest solid.

    Boolean-cutting fine helical threads (e.g. where the radial locking-screw
    thread crosses the inner plug's external thread) can shed sub-micron
    detached slivers. These are numerical chips, not real geometry; dropping
    them leaves a clean single watertight solid. No-op when already one solid.
    """
    solids = part.solids()
    if len(solids) <= 1:
        return part
    largest = max(solids, key=lambda s: s.volume)
    # NB: Part(largest.wrapped) would zero the .volume property; rebuild via
    # addition so volume/BRep queries stay correct.
    return Part() + largest


@dataclass
class Tap:
    """A tool for cutting an internal (tapped) thread by subtraction.

    ``drill_radius`` is the plain bore to open first (the thread's minor
    radius); ``tool`` is the external-thread solid to subtract afterwards to
    carve the grooves out to the major diameter.
    """

    drill_radius: float
    tool: Part


def internal_thread_tap(
    spec: ThreadSpec,
    length: float,
    z_base: float = 0.0,
    clearance: float = 0.0,
) -> Tap:
    """Build a :class:`Tap` for an internal thread. ``clearance`` (mm, radial)
    enlarges the tapped hole for a printed running fit."""
    # An external-shaped tool cuts an internal thread.
    thread, min_r = _external_thread(spec, spec.major_diameter + 2.0 * clearance, length)
    core = Cylinder(
        radius=min_r,
        height=length,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    tool = Pos(0, 0, z_base) * (thread + core)
    return Tap(drill_radius=min_r, tool=tool)
