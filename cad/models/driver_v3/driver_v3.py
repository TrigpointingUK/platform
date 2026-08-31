"""Screw-stashing driver (v3): the v2 key-storing driver plus two spare screws.

Everything underneath is the v2 tool -- the sculpted elliptical sawtooth-knurled
knob with its two glued steel pegs, the embossed logo, and the 4 mm hex key
stored inside the body (``models.driver_v2``). v3 adds two things:

* **Screw stashes.** A pair of three-section blind bores sunk into the flat top
  plateau on the major axis, one each side of the logo: a head recess at the
  plug's own Ø9 clearance-hole diameter (deep enough that the head sits below
  flush), a plain shaft hole at tap-drill size that the user taps by hand so the
  screw threads in and cannot fall out, and a relief below that for the tap's
  tapered lead.
* **A magnetic parts tray** recessed into the flat base, with a pocket for a Ø8
  disc magnet in the middle of its roof.
* **A second pin spanner in the +X end**, for the *inner* plug: two Ø6 steel pins
  glued into blind bores on the ellipse's nose, spaced to the inner plug's own
  side-hole pattern. The tool is then held major-axis-vertical and turned about
  that axis, gripping the knurled waist. Each mouth opens through a **spherical
  dish** rather than a chamfer -- the plan ellipse is left whole, and the dish is
  what keeps a bore that is wider than the nose it enters from leaving a feather
  edge. See ``SidePinParams``.

Carrying the side pins made the body 8 mm thicker through the straight knurl band
and faded the knurl out at both ends -- v3 passes ``build_driver_v1`` its own
``DRIVER_V3`` for that, so v1 and v2 are untouched. See ``params.py``.

One sharp edge is NOT fixed
---------------------------
The knurl fade removes what made the -X end spiky (teeth truncated by the key
flare, the slot and the scoop), the scoop is now a shallow cap rather than a
hemisphere, and the slot mouth has lost its corner points. What remains square is
the **short-arm slot's two long mouth edges**, where its flat floor and ceiling
break the curved end. Neither cure works there:

* OCCT will not fillet them. Of the 32 edges in that region it refuses 19 --
  including every one that matters -- one at a time, at 0.8, 0.6 and 0.4 mm.
  Cavity edges bounded by trimmed spline surfaces are outside what its filleting
  algorithm handles.
* No cutter shape chamfers them either. A chamfer needs a plane to follow, and
  the slot cuts across the ellipse's nose, so its mouth wanders over ~6 mm in x
  between the middle of the opening and its ends.

They are a deburring job on the print, or a slot built some other way in a later
version. Everything else in that area is now blunt.

The two features are cut from opposite faces and never meet: the stashes bottom
out at z = 17 on the major axis, the tray's magnet pocket tops out at z = 8.3 on
the centreline.

The tool is printed **base-down**, so the tray is a cavity the printer must roof
over air. Its geometry is chamfered accordingly -- see ``BaseTrayParams`` for
why every one of those is a chamfer and not a fillet.

Only the plastic body is modelled; the screws, like the dowel pegs, the magnets
and the O-ring, are BOM items.

Local frame is the driver's: z = 0 at the flat base, +z upward, major axis = X.
"""

from __future__ import annotations

import math

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Cone,
    Cylinder,
    Ellipse,
    Plane,
    Pos,
    Rotation,
    Sphere,
    fillet,
    loft,
)

from common.threads import keep_largest_solid
from models.driver_v1.params import DRIVER, DriverParams
from models.driver_v2.driver_v2 import build_driver_v2
from models.driver_v2.params import KEYSTORE, KeyStoreParams
from models.driver_v3.params import (
    BASETRAY,
    DRIVER_V3,
    KEYSTORE_V3,
    SCREWSTASH,
    SIDEPIN,
    BaseTrayParams,
    ScrewStashParams,
    SidePinParams,
)
from models.plug.params import PLUG, PlugParams

# v1 starts each sighting groove this far inboard of its vent hole, so the top
# face is only clear of grooves inside (peg_x - this). Mirrors the literal in
# ``models.driver_v1.driver_v1._vent_grooves``.
_GROOVE_INSET = 2.0

# Minimum plastic left under a stash's blind end, as a sanity floor.
_MIN_FLOOR = 5.0

# Least plastic tolerated above/below a pin bore where it meets the end face.
# It is thin by design -- a 45 mm body has no more to give -- but it thickens
# quickly as the bore runs inboard, and the load is not carried here.
_MIN_MOUTH_WALL = 2.5

# Daylight left between a mouth dish and the ends of the straight knurl band.
_DISH_BAND_GAP = 0.25

# How blunt a pin mouth's rim has to be. 180 would be a seamless blend, 90 a
# square-cut hole; the design target is a dish you cannot feel as an edge.
_MIN_RIM_ANGLE = 130.0


def _stash_cutter(x: float, head_dia: float, z_plateau: float,
                  s: ScrewStashParams):
    """The full three-section stash void at ``(x, 0)``, as ONE fused solid.

    Sunk from the plateau (``z_plateau``) downward: head recess, then the plain
    tap-drill shaft hole, then the tap relief. Fusing the sections and cutting
    once lets OCCT resolve the coaxial annular junctions into clean edges, where
    cutting piece by piece can leave sliver faces (the same reason v2 fuses its
    key channel before subtracting).
    """
    head_r = head_dia / 2.0
    shaft_r = s.tap_drill_dia / 2.0

    z_floor = z_plateau - s.head_depth  # head recess floor
    z_shaft = z_floor - s.shaft_len  # bottom of the tapped section
    z_blind = z_shaft - (s.relief_depth if s.relief_dia > s.tap_drill_dia else 0.0)

    # 1. Head recess, overshooting into the air above so the boolean is clean.
    cut = Pos(x, 0, (z_floor + z_plateau + 1.0) / 2) * Cylinder(
        radius=head_r, height=(z_plateau + 1.0) - z_floor
    )

    # Mouth chamfer at the plateau: a lead-in for the screw head and a kinder
    # edge under the palm than a printed square corner.
    if s.mouth_chamfer > 0:
        c = s.mouth_chamfer
        cut = cut + Pos(x, 0, z_plateau - c) * Cone(
            bottom_radius=head_r, top_radius=head_r + c, height=c,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # 2. Plain shaft hole at tap-drill size (threaded by hand after printing).
    cut = cut + Pos(x, 0, (z_shaft + z_floor) / 2) * Cylinder(
        radius=shaft_r, height=z_floor - z_shaft
    )

    # Countersink where it opens into the head recess: starts the tap square and
    # stops the first thread tearing out of the printed floor.
    if s.tap_lead_chamfer > 0:
        c = s.tap_lead_chamfer
        cut = cut + Pos(x, 0, z_floor - c) * Cone(
            bottom_radius=shaft_r, top_radius=shaft_r + c, height=c,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # 3. Tap relief: wider than the screw's crest, so the tap's tapered lead
    # spins free and full-form thread reaches the bottom of section 2 (and the
    # screw tip can never bottom out before its head seats).
    if z_blind < z_shaft:
        cut = cut + Pos(x, 0, (z_blind + z_shaft) / 2) * Cylinder(
            radius=s.relief_dia / 2.0, height=z_shaft - z_blind
        )

    return cut


def _tray_axes(p: DriverParams, plug: PlugParams, t: BaseTrayParams):
    """Semi-axes ``(a, b)`` of the elliptical base tray.

    ``b`` is given (half of ``minor``); ``a`` is **derived** from the rule that
    balances the tray in the base face: it should stand off the dowel pegs by the
    same distance it stands off the tool's own edge on the minor axis. Both are
    clearances, measured edge to edge -- the tray wall to the peg BORE, and the
    tray wall to the tool's Ø60 minor rim. Deriving it keeps that balance true
    through any change to the body radius, the peg spacing or the bore size.
    """
    b = t.minor / 2.0
    gap = p.body_r - b  # clearance to the tool's minor-axis edge
    a = plug.clr_hole_spacing / 2.0 - p.peg_bore_dia / 2.0 - gap
    return a, b


def _tray_cutter(t: BaseTrayParams, a: float, b: float):
    """The base tray + its magnet pocket at the axis, as ONE fused solid.

    Cut upward from the base (z = 0), which is the face on the build plate, so
    every surface here is an overhang in print orientation. Bottom to top:

        mouth chamfer -> straight wall -> roof chamfer -> [roof: bridged] ->
        magnet-pocket mouth chamfer -> magnet pocket -> [pocket roof: bridged]

    The tray is elliptical, so its two chamfers are **lofted between ellipses**
    rather than scaled from a cone: each shrinks both semi-axes by the same amount
    over the same height, which moves every point of the section inward by exactly
    that amount and holds the slope at 45 deg or shallower in every direction. A
    round cone scaled by the plan ratio would reach 50 deg in X and quietly stop
    being self-supporting. The two flat roofs are bridges, which no amount of CAD
    removes -- ``roof_chamfer`` just shortens the long one.
    """
    mr = t.magnet_pocket_dia / 2.0
    c0, c1 = t.mouth_chamfer, t.roof_chamfer
    z_wall = t.depth - c1  # where the wall starts closing in
    z_pocket = t.depth + t.magnet_pocket_depth

    # Sections bottom to top; the first overshoots below the base so the boolean
    # is clean. Equal sections in a row loft to a straight prism.
    sections = []
    if c0 > 0:
        sections += [(-1.0, a + c0, b + c0), (0.0, a + c0, b + c0), (c0, a, b)]
    else:
        sections.append((-1.0, a, b))
    sections.append((z_wall, a, b))
    if c1 > 0:
        sections.append((t.depth, a - c1, b - c1))

    with BuildPart() as bp:
        for z, ax, by in sections:
            with BuildSketch(Plane.XY.offset(z)):
                Ellipse(ax, by)
        loft(ruled=True)
    cut = bp.part

    # Magnet-pocket mouth chamfer: lead-in, glue fillet, and -- see params -- the
    # thing that keeps the bridge layer's sagging perimeter out of the bore. The
    # pocket stays round: the magnet is.
    if t.magnet_mouth_chamfer > 0:
        c = t.magnet_mouth_chamfer
        cut = cut + Pos(0, 0, t.depth) * Cone(
            bottom_radius=mr + c, top_radius=mr, height=c,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # The pocket itself.
    cut = cut + Pos(0, 0, (t.depth + z_pocket) / 2) * Cylinder(
        radius=mr, height=z_pocket - t.depth
    )

    return cut


def _dish_rim_angle(a: float, b: float, x_c: float, R: float) -> float | None:
    """Included angle of material where a mouth dish meets the elliptical flank.

    The dish is a sphere of radius ``R`` centred on the bore axis at ``x_c``; the
    flank is the plan ellipse (semi-axes a, b). Solved in the bore's own plane,
    where the rim is furthest from the axis and the edge is at its sharpest.
    180 deg would be a perfectly smooth blend, 90 deg a square-cut hole, and 0 the
    feather edge a tangential intersection leaves. Returns None if the sphere does
    not reach the flank at all.
    """
    qa = a * a - b * b
    qb = -2.0 * a * x_c
    qc = x_c * x_c + b * b - R * R
    disc = qb * qb - 4.0 * qa * qc
    if disc < 0.0 or qa == 0.0:
        return None
    c = min((-qb - math.sqrt(disc)) / (2.0 * qa), (-qb + math.sqrt(disc)) / (2.0 * qa))
    if not -1.0 <= c <= 1.0:
        return None
    rx, ry = a * c, b * math.sqrt(1.0 - c * c)

    n1 = (rx / (a * a), ry / (b * b))  # outward flank normal
    n1l = math.hypot(*n1)
    n2 = (x_c - rx, -ry)  # into the dish, i.e. toward its centre
    n2l = math.hypot(*n2)
    if n1l == 0.0 or n2l == 0.0:
        return None
    dot = (n1[0] * n2[0] + n1[1] * n2[1]) / (n1l * n2l)
    return 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def _truncate_nose(part, p: DriverParams, sp: SidePinParams):
    """Optionally cut the last ``nose_flat_back`` mm off the +X tip, rounding the
    new rim. **Off by default** -- the spherical mouth dish makes it unnecessary,
    and the ellipse is worth keeping whole. Kept switchable because a flat also
    gives a bearing pad square to the pins, if a future pin ever wants one.
    """
    if sp.nose_flat_back <= 0:
        return part

    a = p.body_r * p.plan_aspect
    nose_x = a - sp.nose_flat_back
    reach = 4.0 * p.body_half_h  # comfortably past the body in y and z
    part = part - Pos(nose_x + reach / 2, 0, p.body_half_h) * Box(reach, reach, reach)

    if sp.nose_round > 0:
        # The flat is the only planar face whose normal runs along X; round its
        # whole rim in one go, before the bores are cut, so the edge loop is
        # simple and closed.
        face = max(part.faces().filter_by(Axis.X), key=lambda f: f.center().X)
        part = fillet(face.edges(), radius=sp.nose_round)

    return part


def _pin_bore(z: float, nose_x: float, sp: SidePinParams, body_h: float,
              vent_up: bool):
    """One glued side-pin bore at ``(nose_x, 0, z)``, drilled along -X.

    Mirrors v1's peg bores turned on their side: a clearance blind hole with
    annular keying grooves for the epoxy, a mouth chamfer (pin lead-in, glue
    fillet, and here also a blunting of the thin lip the ellipse's nose leaves
    each side of the hole), and a vent from the blind end so pushing the pin in
    cannot hydraulic-lock on trapped epoxy.

    ``vent_up`` routes the vent to whichever face is nearer: the top for the
    upper pin, the base for the lower one.
    """
    r = sp.pin_bore_dia / 2.0
    x_blind = nose_x - sp.bore_depth

    # Main blind bore, opening at the nose and overshooting into the air outside.
    cut = Pos((x_blind + nose_x + 2.0) / 2, 0, z) * Rotation(0, 90, 0) * Cylinder(
        radius=r, height=(nose_x + 2.0) - x_blind
    )

    # Annular keying grooves along the bore: cured epoxy keys into them, so the
    # pin cannot slide out however the joint is loaded.
    if sp.groove_n > 0 and sp.groove_depth > 0:
        x_lo, x_hi = x_blind + 4.0, nose_x - 4.0
        for i in range(sp.groove_n):
            frac = 0.5 if sp.groove_n == 1 else i / (sp.groove_n - 1)
            xg = x_lo + (x_hi - x_lo) * frac
            cut = cut + Pos(xg, 0, z) * Rotation(0, 90, 0) * Cylinder(
                radius=r + sp.groove_depth, height=sp.groove_h
            )

    # Mouth: a spherical countersink, centred out along the bore axis so it bites
    # mouth_dish_d deep at the nose. It does two jobs at once -- it swallows the
    # whole region where the bore is wider than the nose (so the bore wall never
    # runs out tangentially to the surface and leaves a feather edge), and its own
    # rim meets the flank at a shallow angle, ~139 deg included. See params.
    if sp.mouth_dish_r > 0 and sp.mouth_dish_d > 0:
        cut = cut + Pos(
            nose_x - sp.mouth_dish_d + sp.mouth_dish_r, 0, z
        ) * Sphere(radius=sp.mouth_dish_r)
    elif sp.mouth_chamfer > 0:
        # Fallback: a plain conical lead-in. Fine on a flat or gently curved
        # face; NOT sufficient on the bare elliptical nose.
        c = sp.mouth_chamfer
        cut = cut + Pos(nose_x - c, 0, z) * Rotation(0, 90, 0) * Cone(
            bottom_radius=r, top_radius=r + c, height=c,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # Vent from the blind end out to the nearer face.
    if sp.vent_dia > 0:
        x_vent = x_blind + sp.vent_inset
        z0, z1 = (z, body_h + 2.0) if vent_up else (-2.0, z)
        cut = cut + Pos(x_vent, 0, (z0 + z1) / 2) * Cylinder(
            radius=sp.vent_dia / 2.0, height=z1 - z0
        )

    return cut


def build_driver_v3(
    p: DriverParams = DRIVER_V3,
    plug: PlugParams = PLUG,
    ks: KeyStoreParams = KEYSTORE_V3,
    s: ScrewStashParams = SCREWSTASH,
    t: BaseTrayParams = BASETRAY,
    sp: SidePinParams = SIDEPIN,
    *,
    knurl: bool = True,
    logo: bool = True,
    stash: bool = True,
    tray: bool = True,
    pins: bool = True,
):
    """Return the v3 driver as a build123d ``Part``.

    The body underneath is :func:`models.driver_v2.driver_v2.build_driver_v2`,
    built from v3's own thicker, end-faded ``DRIVER_V3``; ``knurl``/``logo`` are
    forwarded to it. ``stash``/``tray``/``pins`` drop any addition (useful for A/B
    comparison). Both interfaces to the plug -- the stash head-recess diameter and
    the side-pin spacing -- are read from ``plug``, never restated here.
    """
    head_dia = 2.0 * plug.clr_hole_r  # Ø9: the plug's own clearance hole
    body_h = 2.0 * p.body_half_h
    peg_x = plug.clr_hole_spacing / 2.0
    nose_x = p.body_r * p.plan_aspect - sp.nose_flat_back  # +X end (the tip, unless truncated)

    if ks.z_plane != p.body_half_h:
        raise ValueError(
            f"key channel z_plane={ks.z_plane} is no longer the tool's equator "
            f"(body_half_h={p.body_half_h}); it would sit off-centre"
        )
    if stash:
        _check(p, plug, ks, s, head_dia=head_dia, body_h=body_h, peg_x=peg_x)
    if tray:
        _check_tray(p, plug, ks, t, peg_x=peg_x)
    if pins:
        _check_pins(p, plug, ks, sp, body_h=body_h, peg_x=peg_x, nose_x=nose_x)

    part = build_driver_v2(p, plug, ks, knurl=knurl, logo=logo)

    if pins:
        part = _truncate_nose(part, p, sp)  # a no-op unless nose_flat_back > 0

    if stash:
        for x in (s.stash_x, -s.stash_x):
            part = part - _stash_cutter(x, head_dia, body_h, s)
    if tray:
        part = part - _tray_cutter(t, *_tray_axes(p, plug, t))
    if pins:
        half = plug.ip_side_spacing / 2.0  # owned by the inner plug
        for z, vent_up in ((p.body_half_h + half, True),
                           (p.body_half_h - half, False)):
            part = part - _pin_bore(z, nose_x, sp, body_h, vent_up)

    return keep_largest_solid(part)


def _check(p: DriverParams, plug: PlugParams, ks: KeyStoreParams,
           s: ScrewStashParams, *, head_dia: float, body_h: float,
           peg_x: float) -> None:
    """Fail loudly if a stash would foul the body it is sunk into.

    Everything here is a *derived* relationship between params owned by three
    different modules, so a plausible-looking edit in any one of them can quietly
    break the others; these are the checks that would otherwise have to be done
    by eye on the render.
    """
    head_r = head_dia / 2.0
    x_in, x_out = s.stash_x - head_r, s.stash_x + head_r

    # Inboard: the embossed logo. Its true extent comes from the SVG, but it is
    # bounded by the fill circle svg_relief uses, so this is a safe proxy.
    logo_r = p.plateau_r * p.logo_fill
    if x_in < logo_r:
        raise ValueError(
            f"stash recess (Ø{head_dia} at x={s.stash_x}) reaches x={x_in:.1f}, "
            f"inside the logo's Ø{2 * logo_r:.1f} envelope; raise stash_x"
        )

    # Outboard: the sighting groove (and, just past it, the peg vent hole).
    x_limit = min(peg_x - _GROOVE_INSET, peg_x - p.peg_vent_dia / 2.0)
    if x_out > x_limit:
        raise ValueError(
            f"stash recess reaches x={x_out:.1f}, into the sighting groove / "
            f"vent at x={x_limit:.1f}; lower stash_x or head clearance"
        )

    # Keep the recess on the FLAT plateau, so its floor is a true flat
    # counterbore and the tap starts square on a level face.
    plateau_x = p.plateau_r * p.plan_aspect
    if x_out > plateau_x:
        raise ValueError(
            f"stash recess reaches x={x_out:.1f}, past the flat plateau edge at "
            f"x={plateau_x:.1f}; its floor would be cut into the sculpted shoulder"
        )

    # Deeper down: the peg bore and its epoxy keying grooves.
    z_shaft = body_h - s.head_depth - s.shaft_len
    z_blind = z_shaft - (s.relief_depth if s.relief_dia > s.tap_drill_dia else 0.0)
    if z_blind < p.peg_bore_depth:  # z ranges overlap, so X must not
        peg_r = p.peg_bore_dia / 2.0 + p.peg_groove_depth
        deep_r = max(s.relief_dia, s.tap_drill_dia) / 2.0
        if s.stash_x + deep_r > peg_x - peg_r:
            raise ValueError(
                f"stash bore reaches x={s.stash_x + deep_r:.1f} at z={z_blind:.1f}, "
                f"into the peg bore's keying grooves (x >= {peg_x - peg_r:.1f})"
            )

    # Across the tool: v2's hex-key channel runs parallel to the major axis at
    # y = ks.y_offset, at a height the stash passes straight through.
    key_clear = ks.y_offset - ks.bore_dia / 2.0 - head_r
    if key_clear <= 0:
        raise ValueError(
            f"stash recess (Ø{head_dia}) fouls the key channel (y={ks.y_offset}, "
            f"Ø{ks.bore_dia}); raise y_offset or lower the head diameter"
        )

    # And leave some plastic under the blind end.
    if z_blind < _MIN_FLOOR:
        raise ValueError(
            f"stash bottoms at z={z_blind:.1f}, leaving under {_MIN_FLOOR} mm of "
            f"floor; shorten relief_depth or the tool is too shallow for it"
        )


def _check_tray(p: DriverParams, plug: PlugParams, ks: KeyStoreParams,
                t: BaseTrayParams, *, peg_x: float) -> None:
    """Fail loudly if the base tray would foul the body, or print badly.

    The printability checks are here rather than left to the slicer because the
    tool is printed base-down without support: an edit that turns a 45 deg
    chamfer into a 60 deg one produces a part that still looks fine in CAD and
    droops on the plate.
    """
    a, b = _tray_axes(p, plug, t)
    mr = t.magnet_pocket_dia / 2.0
    # The mouth chamfer is the widest section, c0 outside the nominal ellipse.
    a_out, b_out = a + t.mouth_chamfer, b + t.mouth_chamfer

    if a <= 0 or b <= 0:
        raise ValueError(
            f"derived tray semi-axes are ({a:.1f}, {b:.1f}); the minor axis "
            f"{t.minor} leaves no room for a major one. Shrink it"
        )
    if a < b:
        raise ValueError(
            f"derived tray major {2*a:.1f} is under its minor {2*b:.1f}: the "
            f"balance rule has inverted the ellipse. Shrink minor, or the pegs "
            f"are too close in for a tray this wide"
        )

    # In plan: stay on the FLAT base (an ellipse of its own, semi-axes
    # base_flat_r * plan_aspect by base_flat_r -- concentric and axis-aligned, so
    # comparing semi-axes settles containment), and clear the dowel bores.
    if b_out > p.base_flat_r or a_out > p.base_flat_r * p.plan_aspect:
        raise ValueError(
            f"tray ({2*a_out:.1f} x {2*b_out:.1f} at its widest) does not fit the "
            f"flat base ({2*p.base_flat_r*p.plan_aspect:.0f} x "
            f"{2*p.base_flat_r:.0f}); it would break out through the rounded edge"
        )
    peg_r = p.peg_bore_dia / 2.0 + p.peg_groove_depth
    if a_out > peg_x - peg_r:
        raise ValueError(
            f"tray reaches x={a_out:.1f}, into the peg bore's keying grooves "
            f"(x >= {peg_x - peg_r:.1f})"
        )

    # In section: leave plastic between the magnet pocket and v2's key channel,
    # which crosses over the tray in plan.
    z_pocket = t.depth + t.magnet_pocket_depth
    key_floor = ks.z_plane - ks.bore_dia / 2.0
    if z_pocket >= key_floor:
        raise ValueError(
            f"magnet pocket tops out at z={z_pocket:.1f}, into v2's key channel "
            f"(underside z={key_floor:.1f}); shallower tray or a thinner magnet"
        )

    # Printability, base-down and unsupported.
    if t.roof_chamfer > t.depth:
        raise ValueError(
            f"roof_chamfer {t.roof_chamfer} exceeds the tray depth {t.depth}"
        )
    roof_b = b - t.roof_chamfer  # the roof's narrow way, and the bridge that counts
    if roof_b <= mr + t.magnet_mouth_chamfer:
        raise ValueError(
            f"roof is {2 * roof_b:.1f} mm across its narrow way, no wider than the "
            f"magnet pocket mouth (Ø{2 * (mr + t.magnet_mouth_chamfer):.1f}); "
            f"nothing left to bridge from"
        )
    if t.mouth_chamfer < 0 or t.magnet_mouth_chamfer < 0 or t.roof_chamfer < 0:
        raise ValueError("tray chamfers must be >= 0 (a negative one is an undercut)")


def _check_pins(p: DriverParams, plug: PlugParams, ks: KeyStoreParams,
                sp: SidePinParams, *, body_h: float, peg_x: float,
                nose_x: float) -> None:
    """Fail loudly if a side-pin bore would foul the body or break out of it."""
    r = sp.pin_bore_dia / 2.0
    half = plug.ip_side_spacing / 2.0
    z_lo, z_hi = p.body_half_h - half, p.body_half_h + half
    x_blind = nose_x - sp.bore_depth

    if sp.pin_dia >= 2.0 * plug.ip_side_r:
        raise ValueError(
            f"pin Ø{sp.pin_dia} does not fit the inner plug's "
            f"Ø{2 * plug.ip_side_r} side holes"
        )
    if sp.protrusion >= plug.ip_side_depth:
        raise ValueError(
            f"pin protrusion {sp.protrusion} bottoms out in the inner plug's "
            f"{plug.ip_side_depth} mm deep side holes"
        )

    # Both mouths must land on the STRAIGHT knurl band. Off it the nose is
    # curving away in z as well as in plan, so the bore would meet the surface
    # obliquely and its lip would run out to nothing.
    z_band_bot = p.body_half_h - p.band_half_h
    z_band_top = p.body_half_h + p.band_half_h + p.top_lip
    wall_dn = (z_lo - r) - z_band_bot
    wall_up = z_band_top - (z_hi + r)
    if min(wall_dn, wall_up) < _MIN_MOUTH_WALL:
        raise ValueError(
            f"pin bores (z={z_lo}, {z_hi}, Ø{sp.pin_bore_dia}) leave only "
            f"{min(wall_dn, wall_up):.2f} mm of wall at the mouth "
            f"(band z={z_band_bot}..{z_band_top}); the tool needs to be thicker"
        )

    # The lower bore passes straight over the +X dowel peg bore.
    peg_r = p.peg_bore_dia / 2.0 + p.peg_groove_depth
    if z_lo - r < p.peg_bore_depth and x_blind < peg_x + peg_r:
        raise ValueError(
            f"lower pin bore ends at x={x_blind:.1f}, into the +X peg bore's "
            f"keying grooves (x <= {peg_x + peg_r:.2f}); shorten bore_depth"
        )

    # ... and both vents drop/rise past the peg bore's neighbourhood.
    x_vent = x_blind + sp.vent_inset
    if abs(x_vent - peg_x) < peg_r + sp.vent_dia / 2.0:
        raise ValueError(
            f"pin vent at x={x_vent:.1f} runs into the peg bore at x={peg_x}"
        )

    # The mouth needs a treatment that swallows the stretch of nose that is
    # NARROWER than the bore -- otherwise the bore wall runs out tangentially to
    # the surface there and leaves a feather edge round each mouth.
    a, b = p.body_r * p.plan_aspect, p.body_r
    x_break = a * math.sqrt(1.0 - (r / b) ** 2) if r < b else 0.0

    if sp.nose_flat_back > 0:
        # Truncated instead: the flat must be wide enough to hold a mouth
        # chamfer with wall to spare, after nose_round eats into its rim.
        half_w = b * math.sqrt(1.0 - (nose_x / a) ** 2)
        side = half_w - sp.nose_round - (r + sp.mouth_chamfer)
        if side < 3.0:
            raise ValueError(
                f"nose flat is {2*half_w:.1f} mm wide, leaving only {side:.2f} mm "
                f"each side of a pin mouth; cut further back (nose_flat_back) or "
                f"shrink nose_round / mouth_chamfer"
            )
    elif sp.mouth_dish_r > 0 and sp.mouth_dish_d > 0:
        # The dish must contain the whole breakout region. Its furthest corner
        # from the dish centre is (x_break, 0, z +/- r) -- equivalently
        # (x_break, r, z) -- so one distance settles it.
        x_c = nose_x - sp.mouth_dish_d + sp.mouth_dish_r
        need = math.hypot(x_c - x_break, r)
        if need > sp.mouth_dish_r - 0.5:
            raise ValueError(
                f"mouth dish (r={sp.mouth_dish_r}, {sp.mouth_dish_d} deep) reaches "
                f"{sp.mouth_dish_r - need:.2f} mm past the region where the Ø"
                f"{sp.pin_bore_dia} bore is wider than the nose (x > {x_break:.2f}); "
                f"it must clear it by 0.5 mm or each mouth keeps a feather edge. "
                f"Deepen mouth_dish_d or enlarge mouth_dish_r"
            )
        # On a 45 mm body the dish is also boxed in vertically: it reaches
        # sqrt(2rd - d^2) up and down the nose, and beyond the straight band the
        # surface is already curving away. Touching that junction exactly is the
        # kind of tangency v2's mesh_gap exists to avoid.
        reach = math.sqrt(max(0.0, 2 * sp.mouth_dish_r * sp.mouth_dish_d
                              - sp.mouth_dish_d ** 2))
        room = p.band_half_h - plug.ip_side_spacing / 2.0
        if reach > room - _DISH_BAND_GAP:
            raise ValueError(
                f"mouth dish reaches {reach:.2f} mm up and down the nose but there "
                f"is only {room:.2f} mm of straight band above each bore; it would "
                f"run into the sculpted top / base edge. Shrink mouth_dish_r or "
                f"mouth_dish_d, or give the tool more band"
            )

        # Swallowing the tangency is necessary but not sufficient: the dish's own
        # rim then has to be blunt, which is the whole point of using one.
        rim = _dish_rim_angle(a, b, x_c, sp.mouth_dish_r)
        if rim is None:
            raise ValueError(
                f"mouth dish (r={sp.mouth_dish_r}, {sp.mouth_dish_d} deep) does not "
                f"reach the flank; it cannot blend the mouth"
            )
        if rim < _MIN_RIM_ANGLE:
            raise ValueError(
                f"mouth dish (r={sp.mouth_dish_r}, {sp.mouth_dish_d} deep) meets the "
                f"flank at {rim:.0f} deg, under the {_MIN_RIM_ANGLE:.0f} deg this "
                f"design asks for. A bigger radius at the same depth is blunter"
            )
    elif sp.mouth_chamfer > 0:
        # A conical chamfer can do the job too -- but only if it is big enough,
        # and "big enough" is not what intuition suggests. The cone has to reach
        # the CORNER of the breakout region, where a point sits at the full bore
        # radius in y AND in z at once, i.e. r*sqrt(2) from the axis. Anything
        # less and slivers of nose survive between the cone and the flank.
        # Measured: 1.0 mm leaves 8 such points in a 1331-point sample, 2.0 mm
        # leaves none. The cost is a blunter-but-not-as-blunt rim than the dish,
        # about 121 deg against 136 deg.
        need = r * (math.sqrt(2.0) - 1.0) + (a - x_break)
        if sp.mouth_chamfer < need + 0.2:
            raise ValueError(
                f"a {sp.mouth_chamfer} mm chamfer does not clear the region where "
                f"the Ø{sp.pin_bore_dia} bore is wider than the nose (x > "
                f"{x_break:.2f}): it must reach r*sqrt(2) = {r*math.sqrt(2):.2f} mm "
                f"from the bore axis there, so it needs to be at least "
                f"{need + 0.2:.2f} mm. Enlarge it, or use a mouth dish (blunter)"
            )
    else:
        raise ValueError(
            f"the Ø{sp.pin_bore_dia} bore is wider than the nose for "
            f"x > {x_break:.2f}, so a bare mouth leaves feather edges round it. "
            f"Set a mouth dish (mouth_dish_r / mouth_dish_d), a mouth_chamfer big "
            f"enough to clear it, or truncate the nose"
        )

    # Keying grooves must stay separate rings: merged, they are one counterbore
    # with no shoulders for the cured epoxy to bear against.
    if sp.groove_n > 1 and sp.groove_depth > 0:
        span = (sp.bore_depth - 8.0) / (sp.groove_n - 1)
        if span <= sp.groove_h:
            raise ValueError(
                f"{sp.groove_n} keying grooves {sp.groove_h} mm tall are spaced "
                f"{span:.2f} mm apart in an {sp.bore_depth} mm bore: they merge "
                f"into one counterbore. Use fewer grooves or a shorter groove_h"
            )

    # The teeth must be gone where the mouths break the rim, or each mouth is
    # cut through a row of sawteeth and ringed with spikes.
    if p.knurl_fade_end > 1.0:
        raise ValueError(
            "knurl_fade_end > 1.0: the teeth never fade, so the pin mouths would "
            "be cut through them; v3 needs an end-faded knurl"
        )


if __name__ == "__main__":
    import time

    t0 = time.time()
    part = build_driver_v3()
    print(
        f"driver_v3: volume={part.volume:.0f} mm^3  valid={part.is_valid}  "
        f"built in {time.time()-t0:.1f}s"
    )
    bb = part.bounding_box()
    print(
        f"  bbox: x[{bb.min.X:.1f},{bb.max.X:.1f}] "
        f"y[{bb.min.Y:.1f},{bb.max.Y:.1f}] z[{bb.min.Z:.1f},{bb.max.Z:.1f}]"
    )
