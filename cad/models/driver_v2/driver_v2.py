"""Key-storing driver: the driver tool with a 4 mm hex key stored inside.

Reuses the driver body / pegs / knurl / logo unchanged (``build_driver``) and
subtracts the key-storage cavities: a horizontal long-arm channel parallel to the
major axis (offset in Y to clear the left dowel), a flat short-arm slot swept into
the -X end, a magnet pocket in that slot's floor, and a finger scoop. See
``params.py`` for the concept and dimensions.

Local frame is the driver's: z = 0 at the flat base, +z upward, major axis = X.
"""

from __future__ import annotations

from math import hypot, sqrt

from build123d import (
    Axis,
    Box,
    Cylinder,
    Line,
    Pos,
    Rotation,
    Sphere,
    Torus,
    fillet,
    make_face,
    revolve,
)

from common.threads import keep_largest_solid
from models.driver_v1.driver_v1 import build_driver_v1
from models.driver_v1.params import DRIVER, DriverParams
from models.driver_v2.params import KEYSTORE, KeyStoreParams
from models.plug.params import PLUG, PlugParams


def build_driver_v2(
    p: DriverParams = DRIVER,
    plug: PlugParams = PLUG,
    ks: KeyStoreParams = KEYSTORE,
    *,
    knurl: bool = True,
    logo: bool = True,
):
    """Return the key-storing driver as a build123d ``Part``.

    Everything below the key cavities is the ordinary driver; ``knurl``/``logo``
    are forwarded to :func:`build_driver_v1`.
    """
    # The long-arm channel passes over the left dowel bore -- keep it clear.
    peg_clear = ks.y_offset - ks.bore_dia / 2 - p.peg_bore_dia / 2
    if peg_clear <= 0:
        raise ValueError(
            f"key channel (y={ks.y_offset}, Ø{ks.bore_dia}) fouls the dowel bore "
            f"(Ø{p.peg_bore_dia}); raise y_offset"
        )

    part = build_driver_v1(p, plug, knurl=knurl, logo=logo)

    # ---- Key rest geometry in the driver frame ---------------------------
    a = p.body_r * p.plan_aspect  # ellipse semi-axes at the knurl crest (X, Y)
    b = p.body_r
    y_hi = ks.y_offset
    y_lo = ks.y_offset - ks.short_arm  # short arm runs -Y from the bend
    y_mid = 0.5 * (y_hi + y_lo)
    # Rest position: the short arm's outboard (-X) face sits ``inboard`` inside the
    # rim. The binding point is the largest |y| it spans (where the rim is nearest
    # the axis), so the whole short arm stays within the elliptical extent.
    y_bind = max(abs(y_hi), abs(y_lo))
    x_edge_bind = a * sqrt(1.0 - (y_bind / b) ** 2)
    x_face = -(x_edge_bind - ks.inboard)  # -X face of the short arm at rest
    x_bend = x_face + ks.bar_slot / 2  # long/short arm junction (bar centre)
    x_tip = x_bend + ks.long_arm  # blind end of the long-arm channel

    r = ks.bore_dia / 2.0
    x_beyond = -(a + 6.0)  # a plane safely outboard of the -X rim
    x_mouth = -a * sqrt(1.0 - (y_hi / b) ** 2)  # bore crosses the rim here (ideal)

    # ---- Key channel: long-arm bore + short-arm slot + smooth bend -------
    # Everything is Ø bore_dia / bar_slot, so the bend fillet ends up tangent to
    # both the bore and the flat slot faces. Build all three cavities as ONE fused
    # void and subtract once: fusing lets OCCT resolve those grazing tangencies
    # into clean edges, where a piece-by-piece cut leaves sliver faces that leak.
    length = x_tip - x_beyond
    bore = Pos((x_beyond + x_tip) / 2, y_hi, ks.z_plane) * Rotation(
        0, 90, 0
    ) * Cylinder(radius=r, height=length)

    x_slot_hi = x_face + ks.bar_slot  # inboard wall (short arm +X face at rest)
    slot = Pos((x_beyond + x_slot_hi) / 2, y_mid, ks.z_plane) * Box(
        x_slot_hi - x_beyond, ks.short_arm, ks.bar_slot
    )
    # Round the cutter's lengthwise edges, so the slot's mouth has no sharp
    # corner points. Done on the Box, before it is used: OCCT fillets a Box
    # happily and refuses the same edges once they are spline-bounded cavity
    # edges in the finished solid.
    if ks.bar_slot_round > 0:
        slot = fillet(slot.edges().filter_by(Axis.X), radius=ks.bar_slot_round)

    channel = bore + slot

    # Smooth bend: sweep a round tube (the key arm itself) along a quarter-circle
    # from the long bore into the short slot. A round cross-section matches the round
    # bore, so -- unlike a flat prism extruded through the slot height -- it leaves no
    # burrs where the two meet. The tube is a hair under the bore radius (mesh_gap) to
    # dodge the exact equal-radius tangency (an unmeshable sliver); its centreline arc
    # has radius bend_radius + tube, so the inner wall sits at bend_radius -- the key's
    # own inner bend. Tangent to the long-bore centreline at A=(cx, y_hi) and the
    # short-slot centreline at B=(x_bend, cy); fused in, keeping only the corner
    # quadrant of the ring (x <= cx and y >= cy).
    if ks.bend_radius > 0:
        tube = r - ks.mesh_gap
        R = ks.bend_radius + tube  # centreline arc radius (inner wall = bend_radius)
        cx, cy = x_bend + R, y_hi - R
        ring = Pos(cx, cy, ks.z_plane) * Torus(R, tube)
        reach = R + tube + 1.0
        quadrant = Pos(cx - reach / 2.0, cy + reach / 2.0, ks.z_plane) * Box(
            reach, reach, 2 * tube + 2.0
        )
        channel = channel + (ring & quadrant)

    # ---- Flared bore mouth (conical lead-in) -----------------------------
    # Over the final flare_len at the -X mouth the bore widens from bore_dia to
    # flare_dia, a simple straight cone. As with a cutter reamed in from outside,
    # the flare-diameter shaft is extended out past the rim into free air so there
    # is no flat mouth face to gouge the knurl -- the crests are reamed back cleanly
    # to the cone. Profile in a radial-axial half-plane (X = axial in, Y = radius).
    if ks.flare_dia > ks.bore_dia and ks.flare_len > 0:
        fr2 = ks.flare_dia / 2.0
        ext = x_mouth - x_beyond  # reach out to the bore's outer plane (air)
        prof = make_face([
            Line((-ext, 0.0), (-ext, fr2)),                # outer face, past the rim (air)
            Line((-ext, fr2), (0.0, fr2)),                 # reamed shaft at flare radius
            Line((0.0, fr2), (ks.flare_len, r)),           # the cone: flare_dia -> bore_dia
            Line((ks.flare_len, r), (ks.flare_len, 0.0)),  # inboard end (meets the bore)
            Line((ks.flare_len, 0.0), (-ext, 0.0)),        # back along the axis
        ])
        flare = Pos(x_mouth, y_hi, ks.z_plane) * revolve(prof, Axis.X, 360)
        channel = channel + flare

    # ---- O-ring retention groove (alternative to the magnet; BOM O-ring) --
    # An internal annular gland in the bore wall near the mouth. A soft O-ring
    # (recommended 4 x 1.5 mm NBR) seats in it and stands ~0.5 mm proud into the
    # bore, gripping the key as it passes. Only the groove is modelled (the O-ring
    # is a BOM item, like the magnet). Placed oring_dist in from the ideal rim, so
    # it clears the flare and the short-arm slot wall; a coaxial fat band on the
    # bore, so no tangency to dodge. Push the O-ring in through the mouth to fit.
    if ks.oring_groove_dia > ks.bore_dia and ks.oring_groove_w > 0:
        x_or = x_mouth + ks.oring_dist
        groove = Pos(x_or, y_hi, ks.z_plane) * Rotation(0, 90, 0) * Cylinder(
            radius=ks.oring_groove_dia / 2.0, height=ks.oring_groove_w
        )
        channel = channel + groove

    part = part - channel

    # ---- Retention magnet pocket in the slot floor (magnet is a BOM item) -
    # Sit it toward the bend end (magnet_frac) so it clears the tip finger scoop.
    # Pull it outboard so its inboard edge stays clear of the slot's inboard wall:
    # the pocket is wider than the slot, and if its back projects under the wall the
    # overhang traps a full-size disc dropped in from above.
    floor_z = ks.z_plane - ks.bar_slot / 2
    y_magnet = y_hi + (y_lo - y_hi) * ks.magnet_frac
    x_magnet = min(
        x_bend, x_slot_hi - ks.magnet_pocket_dia / 2 - ks.magnet_wall_clr
    )
    part = part - Pos(
        x_magnet, y_magnet, floor_z - ks.magnet_pocket_depth / 2
    ) * Cylinder(radius=ks.magnet_pocket_dia / 2, height=ks.magnet_pocket_depth)

    # ---- Finger scoop at the -X end --------------------------------------
    # Centre the dish along the short arm: frac 0 = bend, 1 = free tip. Hooking the
    # free tip is less symmetric than the middle but easier for a finger to catch.
    if ks.scoop_r > 0:
        y_scoop = y_hi + (y_lo - y_hi) * ks.scoop_frac
        x_scoop = -a * sqrt(1.0 - (y_scoop / b) ** 2)
        # With scoop_depth set, back the sphere's centre off along the outward
        # surface normal so the dish is a shallow cap rather than a hemisphere:
        # same purchase for a finger, but the rim meets the surface at a slope
        # instead of square on. See params for the geometry.
        off = 0.0
        if 0.0 < ks.scoop_depth < ks.scoop_r:
            off = ks.scoop_r - ks.scoop_depth
        nx, ny = x_scoop / (a * a), y_scoop / (b * b)  # outward ellipse normal
        nl = hypot(nx, ny)
        part = part - Pos(
            x_scoop + off * nx / nl, y_scoop + off * ny / nl, ks.z_plane
        ) * Sphere(radius=ks.scoop_r)

    return keep_largest_solid(part)


if __name__ == "__main__":
    import time

    t0 = time.time()
    part = build_driver_v2()
    print(
        f"driver_v2: volume={part.volume:.0f} mm^3  valid={part.is_valid}  "
        f"built in {time.time()-t0:.1f}s"
    )
    bb = part.bounding_box()
    print(
        f"  bbox: x[{bb.min.X:.1f},{bb.max.X:.1f}] "
        f"y[{bb.min.Y:.1f},{bb.max.Y:.1f}] z[{bb.min.Z:.1f},{bb.max.Z:.1f}]"
    )
