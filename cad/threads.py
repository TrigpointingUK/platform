"""True helical thread helpers built on bd_warehouse's ISO thread generator.

Unlike the render model (bump-maps with no helix angle) these produce real
swept-helix geometry with correct flank angle and lead, suitable for a
functional 3D print.

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
from bd_warehouse.thread import IsoThread

from params import ThreadSpec

# Fade both ends so there are no fragile partial teeth or knife-edges.
_ENDS = ("fade", "fade")


def external_thread_shaft(
    spec: ThreadSpec,
    length: float,
    z_base: float = 0.0,
    clearance: float = 0.0,
) -> Part:
    """A fully threaded external shaft (minor-diameter core + helix), spanning
    ``z_base .. z_base + length``. ``clearance`` (mm, radial) shrinks the major
    diameter for a printed running fit. Fuse onto a part with ``+``."""
    major = spec.major_diameter - 2.0 * clearance
    thread = IsoThread(
        major_diameter=major,
        pitch=spec.pitch,
        length=length,
        external=True,
        end_finishes=_ENDS,
        simple=False,
    )
    core = Cylinder(
        radius=thread.min_radius,
        height=length,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    return Pos(0, 0, z_base) * (thread + core)


def keep_largest_solid(part: Part) -> Part:
    """Return ``part`` reduced to its single largest solid.

    Boolean-cutting fine helical threads (e.g. where the radial grub-screw
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
    major = spec.major_diameter + 2.0 * clearance
    thread = IsoThread(
        major_diameter=major,
        pitch=spec.pitch,
        length=length,
        external=True,  # an external-shaped tool cuts an internal thread
        end_finishes=_ENDS,
        simple=False,
    )
    core = Cylinder(
        radius=thread.min_radius,
        height=length,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )
    tool = Pos(0, 0, z_base) * (thread + core)
    return Tap(drill_radius=thread.min_radius, tool=tool)
