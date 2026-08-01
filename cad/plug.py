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
from lettering import engrave_plug_text
from params import PLUG, PlugParams
from threads import (
    external_min_radius,
    external_thread_shaft,
    internal_thread_tap,
    keep_largest_solid,
)


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
):
    """Return the outer plug as a build123d ``Part``.

    ``threads=False`` skips helix generation (plain cylinders) for a fast
    dimensional preview. ``clearance`` (mm, radial) is a printed-fit allowance:
    the external thread shrinks and the internal bore thread grows. ``text``
    engraves the OS lettering into the top surface.
    """
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
    # bottom run and the top chamfer region are left plain (run-outs).
    if threads:
        z0 = p.bore_thread_plain_bottom
        z1 = total_h - p.bore_chamfer
        tap = internal_thread_tap(
            p.bore_joint, z1 - z0, z_base=z0, clearance=clearance
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
        relief_r = p.bore_joint.major_diameter / 2 + clearance
        relief_bot = z0 * (1 - p.bore_relief_frac)
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
    # Single-sided: from the +X outer surface inward to the axis only (through
    # the near wall and into the bore), not out through the far wall.
    z_cotter = z_mid_top - p.cotter_z_from_shelf
    cp_len = p.lower_r + 1.0
    part = part - Pos(cp_len / 2, 0, z_cotter) * Rot(0, 90, 0) * Cylinder(
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
