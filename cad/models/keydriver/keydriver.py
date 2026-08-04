"""Key-storing driver: the driver tool with a 4 mm hex key stored inside.

Reuses the driver body / pegs / knurl / logo unchanged (``build_driver``) and
subtracts the key-storage cavities: a horizontal long-arm channel parallel to the
major axis (offset in Y to clear the left dowel), a flat short-arm slot swept into
the -X end, a magnet pocket in that slot's floor, and a finger scoop. See
``params.py`` for the concept and dimensions.

Local frame is the driver's: z = 0 at the flat base, +z upward, major axis = X.
"""

from __future__ import annotations

from math import sqrt

from build123d import (
    Align,
    Box,
    Cone,
    Cylinder,
    Pos,
    Rotation,
    Sphere,
)

from common.threads import keep_largest_solid
from models.driver.driver import build_driver
from models.driver.params import DRIVER, DriverParams
from models.keydriver.params import KEYSTORE, KeyStoreParams
from models.plug.params import PLUG, PlugParams


def build_keydriver(
    p: DriverParams = DRIVER,
    plug: PlugParams = PLUG,
    ks: KeyStoreParams = KEYSTORE,
    *,
    knurl: bool = True,
    logo: bool = True,
):
    """Return the key-storing driver as a build123d ``Part``.

    Everything below the key cavities is the ordinary driver; ``knurl``/``logo``
    are forwarded to :func:`build_driver`.
    """
    # The long-arm channel passes over the left dowel bore -- keep it clear.
    peg_clear = ks.y_offset - ks.bore_dia / 2 - p.peg_bore_dia / 2
    if peg_clear <= 0:
        raise ValueError(
            f"key channel (y={ks.y_offset}, Ø{ks.bore_dia}) fouls the dowel bore "
            f"(Ø{p.peg_bore_dia}); raise y_offset"
        )

    part = build_driver(p, plug, knurl=knurl, logo=logo)

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

    # ---- Long-arm channel: horizontal Ø bore along X, open at the -X rim -
    length = x_tip - x_beyond
    part = part - Pos((x_beyond + x_tip) / 2, y_hi, ks.z_plane) * Rotation(
        0, 90, 0
    ) * Cylinder(radius=r, height=length)

    # Lead-in funnel where the channel crosses the rim (at y_hi).
    if ks.mouth_chamfer > 0:
        c = ks.mouth_chamfer
        x_mouth = -a * sqrt(1.0 - (y_hi / b) ** 2)
        part = part - Pos(x_mouth, y_hi, ks.z_plane) * Rotation(0, 90, 0) * Cone(
            bottom_radius=r + c,
            top_radius=r,
            height=c,
            align=(Align.CENTER, Align.CENTER, Align.MIN),
        )

    # ---- Short-arm slot: flat rectangular cavity swept in from the -X end -
    x_slot_hi = x_face + ks.bar_slot  # inboard wall (short arm +X face at rest)
    part = part - Pos((x_beyond + x_slot_hi) / 2, y_mid, ks.z_plane) * Box(
        x_slot_hi - x_beyond, ks.short_arm, ks.bar_slot
    )

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
        part = part - Pos(x_scoop, y_scoop, ks.z_plane) * Sphere(radius=ks.scoop_r)

    return keep_largest_solid(part)


if __name__ == "__main__":
    import time

    t0 = time.time()
    part = build_keydriver()
    print(
        f"keydriver: volume={part.volume:.0f} mm^3  valid={part.is_valid}  "
        f"built in {time.time()-t0:.1f}s"
    )
    bb = part.bounding_box()
    print(
        f"  bbox: x[{bb.min.X:.1f},{bb.max.X:.1f}] "
        f"y[{bb.min.Y:.1f},{bb.max.Y:.1f}] z[{bb.min.Z:.1f},{bb.max.Z:.1f}]"
    )
