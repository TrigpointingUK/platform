"""Plug driver tool: a sculpted, 2:1 elliptical knurled knob with two pegs.

The pegs (Ø8 mm silver-steel, glued into deep blind bores -- a printed peg would
shear across its layer lines at removal torque) drop into the plug's two Ø9 mm
upper-ring holes, so the whole plug can be driven in/out of the pillar spider.
The knob is gripped in the palm; its **directional sawtooth** knurls make
loosening bite and tightening slip (see ``params.py``). The top is sculpted --
a flat central plateau carrying an embossed TrigpointingUK logo, blending
smoothly down to just above the knurl -- with a shallow groove along the major
axis at each peg to sight the tool against the plug's holes.

Only the plastic body is modelled; the steel dowels are a BOM item, their bores
cut into the base -- the same convention the plug uses for its cotter pin and
locking screw.

Local frame: z = 0 at the flat base, +z upward.
"""

from __future__ import annotations

import bisect
from math import cos, hypot, pi, sin

from build123d import (
    Align,
    Axis,
    Box,
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

from common.engraving import svg_relief
from common.threads import keep_largest_solid
from common.tuk import LOGO_FRAC, LOGO_SVG
from models.driver_v1.params import DRIVER, DriverParams
from models.plug.params import PLUG, PlugParams

_LOGO_FILL = 0.85  # logo scaled to this fraction of the plateau's minor radius


def _body(p: DriverParams):
    """Revolve the sculpted knob profile (round; stretched to an ellipse later).

    Profile, bottom to top: a flat base (radius ``base_flat_r``) with a rounded
    edge out to the knurl crest radius ``body_r``; a straight knurled band with a
    short lip; then a *sculpted* top -- a smooth shoulder rolling up and in to a
    flat central plateau (radius ``plateau_r``) that carries the logo. Endpoint
    tangents make the base, band and plateau meet the curves smoothly (no
    creases).
    """
    body_h = 2.0 * p.body_half_h
    z_band_bot = p.body_half_h - p.band_half_h
    z_band_top = p.body_half_h + p.band_half_h
    z_sculpt = z_band_top + p.top_lip  # sculpt starts a little above the knurl

    with BuildPart() as bp:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline((0.0, 0.0), (p.base_flat_r, 0.0))  # flat base
                Spline((p.base_flat_r, 0.0), (p.body_r, z_band_bot),
                       tangents=((1, 0), (0, 1)))  # rounded base edge
                Polyline((p.body_r, z_band_bot), (p.body_r, z_sculpt))  # band + lip
                Spline((p.body_r, z_sculpt), (p.plateau_r, body_h),
                       tangents=((0, 1), (-1, 0)))  # sculpted shoulder
                Polyline((p.plateau_r, body_h), (0.0, body_h), (0.0, 0.0))  # plateau + axis
            make_face()
        revolve(axis=Axis.Z)
    return bp.part


def _ellipse_arclen_table(a: float, b: float, m: int = 4000):
    """Cumulative arc length round the ellipse (semi-axes a=X, b=Y), sampled at
    ``m + 1`` equal-angle stations. Returns ``(phis, cum)`` with
    ``cum[-1]`` = perimeter."""
    step = 2.0 * pi / m
    phis = [step * k for k in range(m + 1)]
    cum = [0.0]
    f_prev = hypot(a * sin(0.0), b * cos(0.0))
    for k in range(1, m + 1):
        f = hypot(a * sin(phis[k]), b * cos(phis[k]))
        cum.append(cum[-1] + 0.5 * (f_prev + f) * step)  # trapezoidal integral
        f_prev = f
    return phis, cum


def _phi_at_arclen(s: float, phis, cum) -> float:
    """Ellipse angle at arc length ``s`` (wraps), by interpolating the table."""
    s %= cum[-1]
    k = min(max(bisect.bisect_right(cum, s) - 1, 0), len(cum) - 2)
    span = cum[k + 1] - cum[k]
    t = 0.0 if span == 0 else (s - cum[k]) / span
    return phis[k] + t * (phis[k + 1] - phis[k])


def _elliptical_sawtooth_wheel(a: float, b: float, n: int, depth: float,
                               steep_frac: float, z0: float, z1: float):
    """A toothed elliptical prism spanning ``z0..z1``: ``n`` sawteeth of equal
    *arc length* round the ellipse (semi-axes a=X, b=Y), so every tooth is the
    same linear size regardless of the ellipse's varying curvature.

    Crests sit on the ellipse, roots are inset ``depth`` along the inward normal.
    Each tooth rises steeply from root to crest over ``steep_frac`` of its pitch,
    then ramps gently back down to the next root. The steep face is thus on the
    clockwise (decreasing arc-length) side of the crest, so a gripping hand turning
    the knob **anticlockwise** drives against those near-radial faces and bites,
    while a clockwise (tightening) turn pushes the shallow ramps and slips.
    """
    phis, cum = _ellipse_arclen_table(a, b)
    pitch = cum[-1] / n
    pts = []
    for i in range(n):
        # Root: inset along the outward ellipse normal at this arc-length station.
        ph = _phi_at_arclen(i * pitch, phis, cum)
        ex, ey = a * cos(ph), b * sin(ph)
        nx, ny = cos(ph) / a, sin(ph) / b  # gradient of (x/a)^2+(y/b)^2, outward
        nl = hypot(nx, ny)
        pts.append((ex - depth * nx / nl, ey - depth * ny / nl))
        # Crest: on the ellipse, a short steep rise later (steep face on the
        # clockwise side); the gentle ramp then runs on to the next root.
        ph = _phi_at_arclen(i * pitch + steep_frac * pitch, phis, cum)
        pts.append((a * cos(ph), b * sin(ph)))

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


def _vent_grooves(part, smooth, p: DriverParams, plug: PlugParams, body_h: float):
    """Cut a shallow sighting groove along the major axis from each vent hole out
    to the rim, hugging the sculpted top at constant depth.

    ``smooth`` is the (already stretched) body *before* knurling -- above the
    band its top surface equals the finished top, and it makes a much cheaper,
    cleaner boolean than the knurled part. Subtracting a downward-shifted copy of
    it leaves a thin shell that follows every top-facing surface; intersecting
    that with a narrow outboard slab on each side isolates the two grooves.
    """
    if p.vent_groove_depth <= 0 or p.vent_groove_w <= 0:
        return part
    d = plug.clr_hole_spacing / 2.0
    z_band_top = p.body_half_h + p.band_half_h
    shell = smooth - Pos(0, 0, -p.vent_groove_depth) * smooth  # depth-thick top layer
    x_edge = p.body_r * p.plan_aspect + 3.0  # a touch past the rim
    slab_h = (body_h + 2.0) - z_band_top
    for sign in (1.0, -1.0):
        x_lo = sign * (d - 2.0)  # start just inboard of the vent to join it
        x_hi = sign * x_edge
        slab = Pos((x_lo + x_hi) / 2, 0.0, (z_band_top + body_h + 2.0) / 2) * Box(
            abs(x_hi - x_lo), p.vent_groove_w, slab_h
        )
        part = part - (shell & slab)
    return part


def build_driver_v1(
    p: DriverParams = DRIVER,
    plug: PlugParams = PLUG,
    *,
    knurl: bool = True,
    logo: bool = True,
):
    """Return the driver tool as a build123d ``Part``.

    Peg spacing and a sanity clearance are read from ``plug`` (the mating part).
    ``knurl=False`` leaves a plain rim (fast preview); ``logo=False`` leaves the
    plateau bare.
    """
    if p.peg_dia >= 2.0 * plug.clr_hole_r:
        raise ValueError(
            f"peg Ø{p.peg_dia} does not fit the plug's Ø{2 * plug.clr_hole_r} holes"
        )

    body_h = 2.0 * p.body_half_h
    part = _body(p)

    # ---- Stretch the round knob into a 2:1 ellipse in plan ---------------
    # A positive affine scale, exact and undistorted for the smooth body. Done
    # BEFORE the knurl and bores so the teeth are laid out directly on the
    # *ellipse* (uniform arc-length, not smeared by the scale) and the peg bores
    # stay round for the dowels. The major axis (X) runs through the pegs.
    if p.plan_aspect != 1.0:
        part = scale(part, by=(p.plan_aspect, 1.0, 1.0))
    smooth = part  # elliptical smooth body, reused as the sighting-groove tool

    # ---- Directional sawtooth knurl: equal tooth size round the rim ------
    if knurl:
        a = p.body_r * p.plan_aspect  # ellipse semi-axes at the crest
        b = p.body_r
        z0 = p.body_half_h - p.band_half_h
        z1 = p.body_half_h + p.band_half_h
        band = Pos(0, 0, (z0 + z1) / 2) * Cylinder(radius=a + 5.0, height=z1 - z0)
        wheel = _elliptical_sawtooth_wheel(
            a, b, p.n_teeth, p.tooth_depth, p.steep_frac, z0 - 1.0, z1 + 1.0
        )
        if not p.catch_ccw:
            wheel = mirror(wheel, Plane.XZ)  # flip chirality (steep faces anticlockwise)
        # Within the band, keep only material inside the toothed ellipse; rejoin
        # the untouched body above and below.
        toothed = (part & band) & wheel
        part = (part - band) + toothed

    # ---- Peg bores in the base (steel dowels glued in later) -------------
    d = plug.clr_hole_spacing / 2.0
    for x in (d, -d):
        part = _peg_bore(part, x, p, body_h)

    # ---- Sighting grooves along the major axis, one per vent -------------
    part = _vent_grooves(part, smooth, p, plug, body_h)

    part = keep_largest_solid(part)

    # ---- Embossed TrigpointingUK logo on the flat plateau ----------------
    if logo:
        part = svg_relief(
            part, z_top=body_h, radius=p.plateau_r, frac_map=LOGO_FRAC,
            svg_path=LOGO_SVG, amount=p.logo_amount, fill=_LOGO_FILL, raised=True,
        )

    return keep_largest_solid(part)


if __name__ == "__main__":
    import time

    t0 = time.time()
    part = build_driver_v1()
    print(
        f"driver_v1: volume={part.volume:.0f} mm^3  valid={part.is_valid}  "
        f"built in {time.time()-t0:.1f}s"
    )
    bb = part.bounding_box()
    print(
        f"  bbox: x[{bb.min.X:.1f},{bb.max.X:.1f}] "
        f"y[{bb.min.Y:.1f},{bb.max.Y:.1f}] z[{bb.min.Z:.1f},{bb.max.Z:.1f}]"
    )
