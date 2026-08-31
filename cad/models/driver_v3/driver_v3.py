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

from build123d import Align, Cone, Cylinder, Pos

from common.threads import keep_largest_solid
from models.driver_v1.params import DRIVER, DriverParams
from models.driver_v2.driver_v2 import build_driver_v2
from models.driver_v2.params import KEYSTORE, KeyStoreParams
from models.driver_v3.params import (
    BASETRAY,
    SCREWSTASH,
    BaseTrayParams,
    ScrewStashParams,
)
from models.plug.params import PLUG, PlugParams

# v1 starts each sighting groove this far inboard of its vent hole, so the top
# face is only clear of grooves inside (peg_x - this). Mirrors the literal in
# ``models.driver_v1.driver_v1._vent_grooves``.
_GROOVE_INSET = 2.0

# Minimum plastic left under a stash's blind end, as a sanity floor.
_MIN_FLOOR = 5.0


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


def _tray_cutter(t: BaseTrayParams):
    """The base tray + its magnet pocket at the axis, as ONE fused solid.

    Cut upward from the base (z = 0), which is the face on the build plate, so
    every surface here is an overhang in print orientation. Bottom to top:

        mouth chamfer -> straight wall -> roof chamfer -> [roof: bridged] ->
        magnet-pocket mouth chamfer -> magnet pocket -> [pocket roof: bridged]

    The three chamfers are all 45 deg (height == radial run), the steepest angle
    that still prints unsupported. The two flat roofs are bridges, which no
    amount of CAD removes -- ``roof_chamfer`` just shortens the long one.
    """
    r = t.dia / 2.0
    mr = t.magnet_pocket_dia / 2.0
    z_wall = t.depth - t.roof_chamfer  # where the wall starts closing in
    z_pocket = t.depth + t.magnet_pocket_depth

    # Mouth chamfer at the base face: takes the first-layer squish, and leaves a
    # clean lip instead of a rolled one.
    cut = Pos(0, 0, 0) * Cone(
        bottom_radius=r + t.mouth_chamfer, top_radius=r, height=t.mouth_chamfer,
        align=(Align.CENTER, Align.CENTER, Align.MIN),
    )

    # Straight wall, overshooting below the base so the boolean is clean.
    cut = cut + Pos(0, 0, (z_wall - 1.0) / 2) * Cylinder(
        radius=r, height=z_wall + 1.0
    )

    # Roof chamfer: the wall closes into the roof at 45 deg rather than meeting it
    # at a corner, and the bridge that follows is 2*roof_chamfer shorter.
    if t.roof_chamfer > 0:
        cut = cut + Pos(0, 0, z_wall) * Cone(
            bottom_radius=r, top_radius=r - t.roof_chamfer, height=t.roof_chamfer,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # Magnet-pocket mouth chamfer: lead-in, glue fillet, and -- see params -- the
    # thing that keeps the bridge layer's sagging perimeter out of the bore.
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


def build_driver_v3(
    p: DriverParams = DRIVER,
    plug: PlugParams = PLUG,
    ks: KeyStoreParams = KEYSTORE,
    s: ScrewStashParams = SCREWSTASH,
    t: BaseTrayParams = BASETRAY,
    *,
    knurl: bool = True,
    logo: bool = True,
    stash: bool = True,
    tray: bool = True,
):
    """Return the v3 driver as a build123d ``Part``.

    Everything but the stashes and the tray is
    :func:`models.driver_v2.driver_v2.build_driver_v2`; ``knurl``/``logo`` are
    forwarded to it. ``stash``/``tray`` drop either addition (useful for A/B
    comparison). The stash head-recess diameter is read from ``plug`` -- it is the
    same hole the screw passes through on the real part.
    """
    head_dia = 2.0 * plug.clr_hole_r  # Ø9: the plug's own clearance hole
    body_h = 2.0 * p.body_half_h
    peg_x = plug.clr_hole_spacing / 2.0

    if stash:
        _check(p, plug, ks, s, head_dia=head_dia, body_h=body_h, peg_x=peg_x)
    if tray:
        _check_tray(p, plug, ks, t, peg_x=peg_x)

    part = build_driver_v2(p, plug, ks, knurl=knurl, logo=logo)

    if stash:
        for x in (s.stash_x, -s.stash_x):
            part = part - _stash_cutter(x, head_dia, body_h, s)
    if tray:
        part = part - _tray_cutter(t)

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
    logo_r = p.plateau_r * 0.85
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
    r = t.dia / 2.0
    mr = t.magnet_pocket_dia / 2.0

    # In plan: stay on the flat base, and clear of the dowel bores.
    if r + t.mouth_chamfer > p.base_flat_r:
        raise ValueError(
            f"tray (Ø{t.dia} + chamfer) reaches r={r + t.mouth_chamfer:.1f}, past "
            f"the flat base's minor radius {p.base_flat_r}; it would break out "
            f"through the rounded base edge"
        )
    peg_r = p.peg_bore_dia / 2.0 + p.peg_groove_depth
    if r + t.mouth_chamfer > peg_x - peg_r:
        raise ValueError(
            f"tray reaches x={r + t.mouth_chamfer:.1f}, into the peg bore's "
            f"keying grooves (x >= {peg_x - peg_r:.1f})"
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
    roof_r = r - t.roof_chamfer
    if roof_r <= mr + t.magnet_mouth_chamfer:
        raise ValueError(
            f"roof (Ø{2 * roof_r:.1f}) is no wider than the magnet pocket mouth "
            f"(Ø{2 * (mr + t.magnet_mouth_chamfer):.1f}); nothing left to bridge from"
        )
    if t.mouth_chamfer < 0 or t.magnet_mouth_chamfer < 0 or t.roof_chamfer < 0:
        raise ValueError("tray chamfers must be >= 0 (a negative one is an undercut)")


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
