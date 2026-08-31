"""Outer brass plug: three stacked annular rings with a central through-bore.

- Middle ring: external thread that screws into the spider's central ring.
- Bore: internal thread that the inner plug screws into (bottom run left plain).
- Upper ring: two clearance holes for the spider shelf screws.
- Lower annulus: a diametral cotter-pin hole.

Local frame: z = 0 at the plug's bottom face, +z upward.
"""

from __future__ import annotations

import math

from build123d import (
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    Cylinder,
    Plane,
    Polyline,
    Pos,
    Rot,
    make_face,
    revolve,
)
from common.threads import (
    external_min_radius,
    external_thread_shaft,
    internal_thread_tap,
    keep_largest_solid,
)
from models.plug.lettering import engrave_plug_text
from common.specs import ThreadSpec
from models.plug.params import PLUG, PlugParams


def _revolved(profile):
    """Revolve a closed (r, z) profile 360 degrees about the Z axis."""
    with BuildPart() as bp:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline(profile, close=True)
            make_face()
        revolve(axis=Axis.Z)
    return bp.part


def _bore_chamfer_cutter(r_bore: float, chamfer: float, z_top: float):
    """A 45-degree countersink ring cutter for the top mouth of the bore.

    ``r_bore`` is the actual bore-passage radius. The resulting chamfer face is
    wide at the top surface (``r_bore + chamfer``) and narrows down to the bore
    wall at depth ``chamfer`` -- a lead-in, not an undercut.
    """
    pts = [
        (r_bore, z_top),
        (r_bore + chamfer, z_top),
        (r_bore, z_top - chamfer),
    ]
    return _revolved(pts)


def build_plug(
    p: PlugParams = PLUG,
    *,
    threads: bool = True,
    clearance: float = 0.0,
    text: bool = True,
    bore_joint: ThreadSpec | None = None,
    bore_clearance: float | None = None,
):
    """Return the outer plug as a build123d ``Part``.

    ``threads=False`` skips helix generation (plain cylinders) for a fast
    dimensional preview. ``clearance`` (mm, radial) is a printed-fit allowance:
    the external thread shrinks and the internal bore thread grows. ``text``
    engraves the OS lettering into the top surface.
    """
    # The bore joint (and its allowance) can be swapped per print process; the
    # spider joint never can -- it has to mate with a real pillar spider.
    bore = bore_joint if bore_joint is not None else p.bore_joint
    bore_clr = clearance if bore_clearance is None else bore_clearance

    total_h = p.lower_h + p.middle_h + p.upper_h
    z_mid_base = p.lower_h
    z_mid_top = p.lower_h + p.middle_h

    # Middle-ring core radius: with a real external thread the core sits at the
    # thread's minor radius and the helix adds crests out to the nominal major.
    if threads:
        mid_core_r = external_min_radius(p.spider_joint, clearance)
    else:
        mid_core_r = p.middle_r

    # ---- Outer body (solid of revolution, no bore yet) -------------------
    profile = [
        (0.0, 0.0),
        (p.lower_r, 0.0),
        (p.lower_r, p.lower_h),
        (mid_core_r, z_mid_base),
        (mid_core_r, z_mid_top),
        (p.upper_r, z_mid_top),
        (p.upper_r, total_h - p.upper_chamfer),
        (p.upper_r - p.upper_chamfer, total_h),
        (0.0, total_h),
    ]
    part = _revolved(profile)

    # External thread on the middle ring
    if threads:
        part = part + external_thread_shaft(
            p.spider_joint, p.middle_h, z_base=z_mid_base, clearance=clearance
        )

    # ---- Central bore ----------------------------------------------------
    # Threaded: drill to the thread minor diameter, then tap the grooves. The
    # thread now runs full-depth to the top face, where the mouth chamfer cuts
    # its lead-in; only the bottom is left plain (a run-out relief).
    if threads:
        z0 = p.bore_thread_plain_bottom
        relief_bot = z0 * (1 - p.bore_relief_frac)
        # Run the tap tool BEYOND the thread it is cutting, so that its faded
        # ends land where they cannot hurt.
        #
        # A fade tapers the tool's rib to nothing over roughly half a pitch. On
        # an *external* thread that is exactly right -- no knife edges, and an
        # easier start. On an *internal* thread it is a trap: a shallower rib
        # carves a shallower groove, so the bore narrows towards the drill
        # diameter and stops admitting the mating crest. The result is a
        # constriction the inner plug's full-depth thread physically cannot
        # screw past -- it is not a cosmetic run-out, it jams the assembly.
        # Measured on the first build, the bore was up to 0.9 mm under the
        # inner plug's crest for 2.2 mm below the mouth.
        #
        # A real tapped hole has full-depth thread right up to its chamfer, so
        # put the fades outside the part: above the top face, and down inside
        # the run-out relief, which is bored out to the major diameter anyway.
        tap = internal_thread_tap(
            bore, (total_h + bore.pitch) - relief_bot,
            z_base=relief_bot, clearance=bore_clr,
        )
        bore_top_r = tap.drill_radius  # the passage the mouth chamfer breaks into
        part = part - Pos(0, 0, total_h / 2) * Cylinder(
            radius=bore_top_r, height=total_h + 2
        )
        part = part - tap.tool

        # Thread run-out relief at the bottom of the bore: the plain section
        # below the thread keeps the minor (drill) diameter for its lower part,
        # but its upper part -- nearest the thread -- is bored out to the
        # thread's major (root) diameter, matching how deep the grooves reach.
        # Strictly LARGER than the tap tool's crest, not equal to it. The tool
        # now runs down into this relief, and two surfaces meeting at an exactly
        # equal radius give OCCT a valid solid whose triangulation leaks (the
        # same grazing trap as the driver_v2 bend fillet). 0.05 mm breaks it
        # and is immaterial in a clearance groove.
        relief_r = bore.major_diameter / 2 + bore_clr + 0.05
        part = part - Pos(0, 0, (relief_bot + z0) / 2) * Cylinder(
            radius=relief_r, height=z0 - relief_bot
        )
    else:
        bore_top_r = p.bore_r
        part = part - Pos(0, 0, total_h / 2) * Cylinder(
            radius=bore_top_r, height=total_h + 2
        )

    # Bore top chamfer (countersink into the actual passage, not the thread major)
    part = part - _bore_chamfer_cutter(bore_top_r, p.bore_chamfer, total_h)

    # ---- Clearance holes in the upper ring -------------------------------
    d = p.clr_hole_spacing / 2
    for ang in (0.0, 180.0):
        x = d * math.cos(math.radians(ang))
        y = d * math.sin(math.radians(ang))
        part = part - Pos(x, y, total_h - p.upper_h / 2) * Cylinder(
            radius=p.clr_hole_r, height=p.upper_h + 2
        )

    # ---- Cotter-pin hole through one side of the lower annulus ------------
    # Single-sided: from the outer surface inward to the axis only (through the
    # near wall and into the bore), not out through the far wall. It sits at
    # ``cotter_bearing``, at right angles to the upper ring's clearance holes.
    z_cotter = p.lower_h * (1.0 - p.cotter_z_frac)
    cp_len = p.lower_r + 1.0
    cb = math.radians(p.cotter_bearing)
    # Orient along the radial direction: Z->X first, THEN spin by the bearing --
    # a single Rot(0, 90, bearing) would spin the tool while still on the Z axis.
    part = part - Pos(
        (cp_len / 2) * math.cos(cb), (cp_len / 2) * math.sin(cb), z_cotter
    ) * Rot(0, 0, p.cotter_bearing) * Rot(0, 90, 0) * Cylinder(
        radius=p.cotter_r, height=cp_len
    )

    # ---- Engraved OS lettering on the top surface ------------------------
    if text:
        part = engrave_plug_text(part, total_h)

    return keep_largest_solid(part)


if __name__ == "__main__":
    import time

    t0 = time.time()
    part = build_plug()
    print(
        f"plug: volume={part.volume:.0f} mm^3  valid={part.is_valid}  "
        f"built in {time.time()-t0:.1f}s"
    )
    bb = part.bounding_box()
    print(
        f"  bbox: x[{bb.min.X:.1f},{bb.max.X:.1f}] "
        f"y[{bb.min.Y:.1f},{bb.max.Y:.1f}] z[{bb.min.Z:.1f},{bb.max.Z:.1f}]"
    )
