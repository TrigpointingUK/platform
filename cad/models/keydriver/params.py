"""Parametric dimensions for the **key-storing driver tool**.

All dimensions in **millimetres** (build123d's native unit). Provenance tags
match the convention used by the driver and plug models:

    [D]  Dimensioned  - taken from a mating part / a measured original / a listing.
    [E]  Estimated    - a plausible guess, tune on the first print.

The tool is the ordinary driver (``models.driver``) with a 4 mm hex (allen) key
stored inside its body. The key is imagined as a *cutter*: its long arm slides
down a Ø``bore_dia`` horizontal channel driven parallel to the **major axis**,
offset in Y by ``y_offset`` so it clears the (left) dowel bore it passes over.
The short arm then sweeps a flat rectangular cavity into the **-X end** and comes
to rest just inside the elliptical rim (``inboard`` sets how far inside). A small
neodymium magnet let into the **floor** of that cavity holds the steel key down;
a spherical finger scoop at the -X end gives purchase to lift it off the magnet
and slide it out.

Only the plastic body is modelled; the magnet (like the driver's dowel pegs) is a
BOM item glued into its pocket -- the same convention the driver and plug use.

Coordinate frame is the driver's: z = 0 at the flat base, +z upward, major axis
along X (through the pegs), minor along Y.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeyStoreParams:
    # ---- Stored key (BOM item; its arms drive the cavity sizes) ----------
    # A 4 mm hex L-key. 4 mm across flats -> ~4.62 mm across corners.
    long_arm: float = 68.0  # [D] long-arm length (supplier listing)
    short_arm: float = 25.0  # [D] short-arm length (supplier listing)

    # ---- Long-arm channel ------------------------------------------------
    bore_dia: float = 5.0  # [E] Ø for a 4 mm hex (4.62 across corners): easy slide
    y_offset: float = 12.0  # [E] channel Y from the centreline; clears the left dowel
    #                           bore (y_offset - bore/2 > peg_bore/2)
    z_plane: float = 20.0  # [E] key mid-plane height above the base = tool mid-height
    #                          (= driver body_half_h; the equator, mid knurl band).
    #                          Leaves ~17 mm of solid material under the magnet pocket.
    funnel_r: float = 1.0  # [E] radius of the rounded bell-mouth lead-in at the bore
    #                          entry: a concave quarter-round flare, tangent to the bore,
    #                          that guides the key in. Nominal opening Ø ~= bore +
    #                          2*funnel_r, truncated where it runs past the tool surface
    #                          (the mouth sits near the +y tip edge, so it is one-sided).
    funnel_gap: float = 0.05  # [E] funnel narrow-end radius = bore/2 - this, a hair
    #                            inside the bore so it dodges the exact equal-radius
    #                            tangency that would leave an unmeshable sliver.

    # ---- Bend (inside-corner fillet joining the two arm cavities) ---------
    bend_radius: float = 6.0  # [E] radius of the quarter-circle rounding the concave
    #                            inside corner, tangent to the long-bore lower wall and
    #                            the short-slot inner wall (centre bend_radius from each).
    #                            Set to the key's own inner bend radius so the cavity
    #                            matches the smooth 90 deg curve on the key.

    # ---- Short-arm slot (swept by the short arm as it is pushed in) -------
    bar_slot: float = 5.0  # [E] slot thickness in X and Z (~4 mm hex bar + clearance)
    inboard: float = 2.0  # [E] short-arm outboard face this far inside the rim; this
    #                         IS the tip wall thickness -- raise to thicken the walls
    #                         (the finger scoop deepens to compensate)

    # ---- Retention magnet (BOM item; only its pocket is modelled) --------
    magnet_dia: float = 8.0  # [E] Ø8 N42 neodymium disc, axially magnetised
    magnet_thick: float = 3.0  # [E] disc thickness (grip; a 4 mm key is only ~10 g)
    magnet_pocket_dia: float = 8.3  # [E] glue clearance: ~0.3 mm epoxy annulus
    magnet_pocket_depth: float = 3.3  # [E] a touch over the disc, so it seats flush-ish
    magnet_frac: float = 0.3  # [E] pocket centre along the short arm, same convention as
    #                            scoop_frac: 0 = bend end, 0.5 = middle, 1.0 = free tip.
    #                            Held toward the bend so it clears the tip finger scoop.
    magnet_wall_clr: float = 0.5  # [E] keep the pocket's inboard edge this far short of
    #                                the slot's inboard wall. The pocket (Ø magnet_pocket)
    #                                is wider than the slot, so without this it overhangs
    #                                under the wall and traps a full-size disc; pulling it
    #                                outboard lets the magnet drop straight in.

    # ---- Finger scoop ----------------------------------------------------
    scoop_r: float = 10.0  # [E] spherical dish at the -X end for finger purchase
    scoop_frac: float = 1.0  # [E] scoop centre along the short arm: 0 = bend end,
    #                            0.5 = middle (symmetric), 1.0 = free tip. Hooking the
    #                            free tip is less symmetric but more ergonomic.


# Single shared instance; import and override fields as measurements arrive.
KEYSTORE = KeyStoreParams()
