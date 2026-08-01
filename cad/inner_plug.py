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
from params import PLUG, PlugParams
from threads import (
    external_min_radius,
    external_thread_shaft,
    internal_thread_tap,
    keep_largest_solid,
)
from top_surfaces import DEFAULT, resolve


def build_inner_plug(
    p: PlugParams = PLUG,
    *,
    threads: bool = True,
    clearance: float = 0.0,
    top: str = DEFAULT,
    grub_thread: bool = True,
):
    """Return the inner plug as a build123d ``Part``.

    ``threads=False`` skips helix generation. ``clearance`` (mm, radial)
    shrinks the external thread for a printed running fit. ``top`` selects a
    top-surface treatment preset (see ``top_surfaces.PRESETS``); ``"flat"``
    leaves the original plain top. ``grub_thread=False`` leaves the grub-screw
    hole as a plain tap-drill hole (for hand-tapping / printed parts) instead of
    modelling the fine internal thread.
    """
    ip_h = p.ip_h
    z_thread_top = ip_h - p.ip_chamfer

    # Core radius: minor diameter under the thread, or nominal without threads.
    if threads:
        core_r = external_min_radius(p.bore_joint, clearance)
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

    # ---- Radial pivot hole (single-sided, for the cotter pin) ------------
    # From the +X outer surface inward to the axis only (meeting the central
    # blind hole), aligned with the plug's cotter hole.
    pv_len = p.ip_r + 2.0
    part = part - _radial_cyl(
        p.ip_pivot_r, pv_len, pv_len / 2, p.ip_pivot_bearing, p.ip_pivot_z
    )

    # ---- Threaded grub-screw hole ----------------------------------------
    # A single radial hole from the outer face inward to the central hole,
    # internally threaded (tapped by subtracting an external tool).
    part = _radial_threaded_hole(
        part,
        p.grub_joint,
        z=p.ip_grub_z,
        bearing_deg=p.ip_grub_bearing,
        length=p.ip_r + 2.0,  # axis out to just past the surface
        central_r=p.ip_hole_r,
        clearance=clearance,
        thread=grub_thread,
    )

    # ---- Top-surface treatment (engraved logo / QR / flat) ---------------
    # Clean to a single solid first: thread booleans can leave a sliver, and an
    # embossing union onto a multi-solid compound misbehaves in OCCT.
    part = keep_largest_solid(part)
    usable_r = core_r - p.ip_chamfer  # flat top radius inside the chamfer
    part = resolve(top).apply(
        part, z_top=ip_h, radius=usable_r, clearance=clearance
    )

    return keep_largest_solid(part)


def _radial_threaded_hole(
    part, spec, *, z, bearing_deg, length, central_r, clearance=0.0, thread=True
):
    """Cut a radial hole at height ``z`` along ``bearing_deg``, from the central
    blind hole out to the surface.

    With ``thread=True`` it is internally threaded: the thread runs the full
    wall so it is visible and functional right from the mouth (only a short
    run-out is left clear of the central blind hole), with a plain minor-diameter
    passage drilled first so its intersections with the surface and the central
    hole are clean plain-cylinder cuts. Where the grub thread meets the inner
    plug's *external* thread at the mouth it sheds sub-triangle mesh slivers,
    cleaned up at STL export.

    With ``thread=False`` it is a **plain hole at the tap-drill (minor)
    diameter** -- for a part that will be hand-tapped after printing (fine
    threads like this grub do not print cleanly).
    """
    place = Pos(0, 0, z) * Rot(0, 0, bearing_deg) * Rot(0, 90, 0)
    # ``place`` maps the Z axis onto the radial direction at ``bearing``:
    # rotate Z->X first (Rot(0,90,0)), THEN spin by bearing about Z. Order
    # matters -- a single Rot(0,90,bearing) would spin the tool while still on
    # the Z axis (a no-op) and leave it along +X.

    def radial(radius, r0, r1):
        """A cylinder spanning radius r0..r1 along the hole axis."""
        return place * Pos(0, 0, r0) * Cylinder(
            radius=radius, height=r1 - r0,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    surface_r = length - 2.0  # nominal outer radius (length reaches past it)
    mouth_lead = 0.6  # shallow plain lead-in at the mouth (mm)

    minor_r = _tap_drill_radius(spec, clearance)  # thread minor = tap-drill size

    if not thread:
        # Plain tap-drill hole through the wall, to be hand-tapped after print.
        part = part - radial(minor_r, 0.0, length)
        return part

    # Plain passage drilled a touch UNDER the minor radius: drilling exactly to
    # the minor radius leaves a cylindrical face coincident with the tap core,
    # which makes OCCT's boolean silently fail for the rotated tool (it returns
    # the part unchanged, leaving an unthreaded hole). The tap core re-establishes
    # the true minor radius, so the thread is unaffected.
    part = part - radial(minor_r - 0.2, 0.0, length)

    # Thread, confined to the plain-drilled wall between a short run-out at the
    # central hole and a short lead-in at the mouth. Keeping the thread clear of
    # the central blind hole and the external thread means it only ever meets
    # plain cylinder walls -- the same clean situation as the bore thread, so it
    # stays valid and meshes watertight.
    t0 = central_r + 0.6
    t1 = surface_r - mouth_lead
    tap = internal_thread_tap(spec, t1 - t0, z_base=t0, clearance=clearance)
    part = part - place * tap.tool

    # Shallow plain lead-in at the mouth, opened to the major diameter so a
    # screw's crests can start (a plain cut through the external thread meshes
    # cleanly, unlike thread-on-thread).
    lead_r = spec.major_diameter / 2 + clearance + 0.2
    part = part - radial(lead_r, surface_r - mouth_lead, length)
    return part


def _tap_drill_radius(spec, clearance):
    """Minor radius of the tapped hole (== the plain drill size)."""
    return internal_thread_tap(spec, spec.pitch * 2, clearance=clearance).drill_radius


def _radial_cyl(radius, length, radial_offset, bearing_deg, z):
    """A cylinder lying along the radial direction at ``bearing_deg``, its
    centre ``radial_offset`` from the axis, at height ``z``."""
    a = math.radians(bearing_deg)
    cx = radial_offset * math.cos(a)
    cy = radial_offset * math.sin(a)
    # Orient along the radial direction: Z->X first, then spin by bearing.
    return Pos(cx, cy, z) * Rot(0, 0, bearing_deg) * Rot(0, 90, 0) * Cylinder(
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
