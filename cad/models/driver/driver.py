"""Plug driver tool: an ellipsoidal knurled disc with two steel-dowel pegs.

The pegs (Ø8 mm silver-steel, epoxied into deep blind bores -- a printed peg
would shear across its layer lines at removal torque) drop into the plug's two
Ø9 mm upper-ring holes, so the whole plug can be driven in/out of the pillar
spider. The disc is gripped in the palm; its **directional sawtooth** knurls
make loosening bite and tightening slip (see ``params.py``).

Only the plastic body is modelled; the steel dowels are a BOM item, their bores
cut into the base -- the same convention the plug uses for its cotter pin and
locking screw.

Local frame: z = 0 at the flat base, +z upward.
"""

from __future__ import annotations

from math import acos, cos, pi, sin

from build123d import (
    Align,
    Axis,
    BuildLine,
    BuildPart,
    BuildSketch,
    Cone,
    Cylinder,
    Plane,
    Polyline,
    Pos,
    Spline,
    extrude,
    make_face,
    mirror,
    revolve,
    scale,
)

from common.engraving import engrave_arc_texts
from common.threads import keep_largest_solid
from models.driver.params import DRIVER, DriverParams
from models.plug.params import PLUG, PlugParams

# Top-face engraving (a nod to the directional grip; tune or disable freely).
_ENGRAVE_FONT = "DejaVu Sans"
_ENGRAVE_SIZE = 5.5
_ENGRAVE_RADIUS = 28.0
_ENGRAVE_DEPTH = 0.6


def _ellipsoid_body(p: DriverParams):
    """Revolve a truncated-ellipse profile into the discus body.

    The outer rim is an ellipse (radial semi-axis ``body_r``, equator at
    mid-height) truncated to flat top and base of radius ``base_flat_r``; the
    vertical semi-axis is sized so the truncations land exactly on z = 0 and
    z = 2*body_half_h.
    """
    body_h = 2.0 * p.body_half_h
    k = p.base_flat_r / p.body_r
    t_edge = acos(k)  # dome arc spans t in [-t_edge, +t_edge] about the equator
    c = p.body_half_h / sin(t_edge)  # vertical semi-axis (> body_half_h)

    n = 48
    dome = []
    for i in range(n + 1):
        t = -t_edge + (2.0 * t_edge) * i / n
        dome.append((p.body_r * cos(t), p.body_half_h + c * sin(t)))

    with BuildPart() as bp:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Spline(*dome)  # smooth outer rim, (flat_r, 0) -> (flat_r, body_h)
                Polyline(dome[-1], (0.0, body_h), (0.0, 0.0), dome[0])
            make_face()
        revolve(axis=Axis.Z)
    return bp.part


def _sawtooth_wheel(rc: float, rr: float, n: int, steep_frac: float,
                    z0: float, z1: float):
    """A toothed cylinder (crest radius ``rc``, root ``rr``, ``n`` asymmetric
    teeth) spanning ``z0..z1``.

    Each tooth is a shallow ramp rising from root to crest over ``1-steep_frac``
    of the pitch, then a short steep face dropping back to root over
    ``steep_frac``. As built, the steep face looks anticlockwise.
    """
    phi = 2.0 * pi / n
    ramp = 1.0 - steep_frac
    pts = []
    for i in range(n):
        a0 = i * phi
        pts.append((rr * cos(a0), rr * sin(a0)))          # root
        ac = a0 + ramp * phi
        pts.append((rc * cos(ac), rc * sin(ac)))          # crest (steep drop after)

    with BuildPart() as bp:
        with BuildSketch(Plane.XY.offset(z0)):
            with BuildLine():
                Polyline(*pts, close=True)
            make_face()
        extrude(amount=z1 - z0)
    return bp.part


def _peg_bore(part, x: float, p: DriverParams, body_h: float):
    """Cut one glued-dowel peg bore at ``(x, 0)``: a clearance blind hole with
    annular keying grooves, a mouth chamfer (lead-in + glue fillet) and a vent
    from the blind end to the top face so surplus epoxy/air escapes.
    """
    r = p.peg_bore_dia / 2
    depth = p.peg_bore_depth

    # Main blind bore: opens at the base (z=0), blind end at z=depth.
    part = part - Pos(x, 0, depth / 2 - 1.0) * Cylinder(radius=r, height=depth + 2.0)

    # Annular keying grooves spread along the bore -- the epoxy fills these and
    # keys to the plastic, so the cured plug cannot slide out.
    if p.peg_groove_n > 0 and p.peg_groove_depth > 0:
        z_lo, z_hi = 4.0, depth - 4.0
        for i in range(p.peg_groove_n):
            frac = 0.5 if p.peg_groove_n == 1 else i / (p.peg_groove_n - 1)
            zg = z_lo + (z_hi - z_lo) * frac
            part = part - Pos(x, 0, zg) * Cylinder(
                radius=r + p.peg_groove_depth, height=p.peg_groove_h
            )

    # Mouth chamfer: a lead-in for the dowel and a glue fillet that also spreads
    # the high-stress bearing load at the hole mouth.
    if p.peg_mouth_chamfer > 0:
        c = p.peg_mouth_chamfer
        part = part - Pos(x, 0, 0) * Cone(
            bottom_radius=r + c, top_radius=r, height=c,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # Vent: a thin channel from the blind end up to the top face, so pushing the
    # dowel in cannot hydraulic-lock on trapped epoxy (surplus weeps out the top).
    if p.peg_vent_dia > 0:
        z0, z1 = depth - 1.0, body_h + 1.0
        part = part - Pos(x, 0, (z0 + z1) / 2) * Cylinder(
            radius=p.peg_vent_dia / 2, height=z1 - z0
        )

    return part


def build_driver(
    p: DriverParams = DRIVER,
    plug: PlugParams = PLUG,
    *,
    knurl: bool = True,
    engrave: bool = True,
):
    """Return the driver tool as a build123d ``Part``.

    Peg spacing and a sanity clearance are read from ``plug`` (the mating part).
    ``knurl=False`` leaves a plain elliptical rim (fast preview); ``engrave``
    cuts the top-face labels.
    """
    if p.peg_dia >= 2.0 * plug.clr_hole_r:
        raise ValueError(
            f"peg Ø{p.peg_dia} does not fit the plug's Ø{2 * plug.clr_hole_r} holes"
        )

    body_h = 2.0 * p.body_half_h
    part = _ellipsoid_body(p)

    # ---- Directional sawtooth knurl band round the equator ---------------
    if knurl:
        rc = p.body_r
        rr = p.body_r - p.tooth_depth
        z0 = p.body_half_h - p.band_half_h
        z1 = p.body_half_h + p.band_half_h
        band = Pos(0, 0, (z0 + z1) / 2) * Cylinder(radius=rc + 5.0, height=z1 - z0)
        wheel = _sawtooth_wheel(rc, rr, p.n_teeth, p.steep_frac, z0 - 1.0, z1 + 1.0)
        if not p.catch_ccw:
            wheel = mirror(wheel, Plane.XZ)  # flip chirality (steep faces clockwise)
        # Within the band, keep only material inside the toothed wheel; rejoin
        # the untouched domes above and below.
        toothed = (part & band) & wheel
        part = (part - band) + toothed

    # ---- Stretch the round disc into a 2:1 ellipse in plan ---------------
    # A positive affine scale, so it stays a valid single solid and preserves
    # the knurl's rotational handedness. Done BEFORE the peg bores so those
    # stay round (Ø8) for the round dowels; the major axis (X) runs through the
    # pegs and extends beyond them.
    if p.plan_aspect != 1.0:
        part = scale(part, by=(p.plan_aspect, 1.0, 1.0))

    # ---- Peg bores in the base (steel dowels epoxied in later) -----------
    d = plug.clr_hole_spacing / 2.0
    for x in (d, -d):
        part = _peg_bore(part, x, p, body_h)

    part = keep_largest_solid(part)

    # ---- Top-face engraving ---------------------------------------------
    # Along the long (major/X) axis, where the flat top has room.
    if engrave:
        part = engrave_arc_texts(
            part,
            [("LOOSEN", 0.0, 100.0), ("TIGHTEN", 180.0, 100.0)],
            z_top=body_h,
            radius=_ENGRAVE_RADIUS,
            font=_ENGRAVE_FONT,
            font_size=_ENGRAVE_SIZE,
            depth=_ENGRAVE_DEPTH,
        )

    return keep_largest_solid(part)


if __name__ == "__main__":
    import time

    t0 = time.time()
    part = build_driver()
    print(
        f"driver: volume={part.volume:.0f} mm^3  valid={part.is_valid}  "
        f"built in {time.time()-t0:.1f}s"
    )
    bb = part.bounding_box()
    print(
        f"  bbox: x[{bb.min.X:.1f},{bb.max.X:.1f}] "
        f"y[{bb.min.Y:.1f},{bb.max.Y:.1f}] z[{bb.min.Z:.1f},{bb.max.Z:.1f}]"
    )
