"""Inner brass plug: an externally threaded cylinder that screws into the
plug's bore, with blind holes drilled into its base.

- Outer wall: external thread mating the plug bore (Joint B).
- Top edge: 1 mm chamfer (the exposed rim, flush with the plug top).
- Base: a central blind hole and two shallower side blind holes.
- A radial pivot hole near the base (for the cotter pin).
- A stepped grub-screw hole that locks the plug against the bore.

Local frame: z = 0 at the inner plug's bottom face, +z upward.
"""

from __future__ import annotations

import math

from build123d import (
    Align,
    Axis,
    BuildPart,
    Cylinder,
    GeomType,
    Pos,
    Rot,
    chamfer,
)
from bd_warehouse.thread import IsoThread

from params import PLUG, PlugParams
from threads import external_thread_shaft


def build_inner_plug(
    p: PlugParams = PLUG, *, threads: bool = True, clearance: float = 0.0
):
    """Return the inner plug as a build123d ``Part``.

    ``threads=False`` skips helix generation. ``clearance`` (mm, radial)
    shrinks the external thread for a printed running fit.
    """
    ip_h = p.ip_h
    z_thread_top = ip_h - p.ip_chamfer

    # Core radius: minor diameter under the thread, or nominal without threads.
    if threads:
        probe = IsoThread(
            major_diameter=p.bore_joint.major_diameter - 2 * clearance,
            pitch=p.bore_joint.pitch,
            length=z_thread_top,
            external=True,
            end_finishes=("fade", "fade"),
            simple=False,
        )
        core_r = probe.min_radius
    else:
        core_r = p.ip_r

    # ---- Core cylinder with a chamfered top rim --------------------------
    with BuildPart() as bp:
        Cylinder(
            radius=core_r,
            height=ip_h,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )
        top_edge = (
            bp.edges().filter_by(GeomType.CIRCLE).group_by(Axis.Z)[-1]
        )
        chamfer(top_edge, p.ip_chamfer)
    part = bp.part

    # ---- External thread on the wall -------------------------------------
    if threads:
        part = part + external_thread_shaft(
            p.bore_joint, z_thread_top, z_base=0.0, clearance=clearance
        )

    # ---- Blind holes in the base -----------------------------------------
    # Centre hole
    part = part - Pos(0, 0, p.ip_centre_depth / 2) * Cylinder(
        radius=p.ip_hole_r, height=p.ip_centre_depth
    )
    # Two side holes
    side_d = p.ip_side_spacing / 2
    for ang in (90.0, 270.0):
        x = side_d * math.cos(math.radians(ang))
        y = side_d * math.sin(math.radians(ang))
        part = part - Pos(x, y, p.ip_side_depth / 2) * Cylinder(
            radius=p.ip_hole_r, height=p.ip_side_depth
        )

    # ---- Radial pivot hole (diametral, for the cotter pin) ---------------
    part = part - Pos(0, 0, p.ip_pivot_z) * Rot(0, 90, p.ip_pivot_bearing) * Cylinder(
        radius=p.ip_pivot_r, height=2 * core_r + 2
    )

    # ---- Stepped grub-screw hole -----------------------------------------
    gs_ang = p.ip_grub_bearing
    # Outer counterbore: from the outer surface inward.
    ob_len = p.ip_grub_outer_len
    ob_mid = p.ip_r - ob_len / 2  # centre of counterbore along the radial axis
    part = part - _radial_cyl(
        p.ip_grub_outer_r, ob_len + 1, ob_mid, gs_ang, p.ip_grub_z
    )
    # Inner drilling: from the counterbore base through to the axis.
    ib_len = p.ip_r - ob_len
    ib_mid = ib_len / 2
    part = part - _radial_cyl(
        p.ip_grub_inner_r, ib_len + 1, ib_mid, gs_ang, p.ip_grub_z
    )

    return part


def _radial_cyl(radius, length, radial_offset, bearing_deg, z):
    """A cylinder lying along the radial direction at ``bearing_deg``, its
    centre ``radial_offset`` from the axis, at height ``z``."""
    a = math.radians(bearing_deg)
    cx = radial_offset * math.cos(a)
    cy = radial_offset * math.sin(a)
    return Pos(cx, cy, z) * Rot(0, 90, bearing_deg) * Cylinder(
        radius=radius, height=length
    )


if __name__ == "__main__":
    import time

    t0 = time.time()
    part = build_inner_plug()
    print(
        f"inner plug: volume={part.volume:.0f} mm^3  valid={part.is_valid}  "
        f"built in {time.time()-t0:.1f}s"
    )
    bb = part.bounding_box()
    print(
        f"  bbox: x[{bb.min.X:.1f},{bb.max.X:.1f}] "
        f"y[{bb.min.Y:.1f},{bb.max.Y:.1f}] z[{bb.min.Z:.1f},{bb.max.Z:.1f}]"
    )
