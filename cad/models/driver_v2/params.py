"""Parametric dimensions for the **key-storing driver tool**.

All dimensions in **millimetres** (build123d's native unit). Provenance tags
match the convention used by the driver and plug models:

    [D]  Dimensioned  - taken from a mating part / a measured original / a listing.
    [E]  Estimated    - a plausible guess, tune on the first print.

The tool is the v1 driver (``models.driver_v1``) with a 4 mm hex (allen) key
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
    flare_len: float = 5.0  # [E] over this final length at the -X mouth the bore widens
    flare_dia: float = 7.0  # [E] from bore_dia up to this, a straight conical lead-in.
    #                          Reamed in from outside (no flat mouth face) so it truncates
    #                          the knurl cleanly. Set flare_dia <= bore_dia to disable.
    mesh_gap: float = 0.05  # [E] shrink a round feature this far under the bore radius
    #                          where it would otherwise meet the bore (or slot) at an
    #                          exact equal radius -- that tangency is a valid solid but
    #                          leaves an unmeshable sliver. Used by the bend tube.

    # ---- O-ring retention groove (alternative to the magnet; BOM O-ring) --
    # Recommended O-ring: 4 mm ID x 1.5 mm CS NBR (free OD 7 mm). Its ID grips the
    # ~4.6 mm across-corners key with light interference. Only the groove is modelled.
    oring_groove_dia: float = 7.0  # [E] gland outer Ø (= O-ring free OD): ~1 mm deep in
    #                                 the Ø bore_dia wall, so the O-ring stands ~0.5 mm
    #                                 proud into the bore. Set <= bore_dia to disable.
    oring_groove_w: float = 2.0  # [E] groove width (axial), ~1.3x the O-ring CS so the
    #                               rubber has room to deform as the key pushes through
    oring_dist: float = 16.0  # [E] groove centre, inboard from the ideal rim. Must clear
    #                            the bend (~14 mm in): the near-mouth bore is where the key
    #                            curves, so the O-ring sits just past it on the straight
    #                            long arm, where it grips a clean round section.

    # ---- Bend (round tube swept from the long bore into the short slot) ---
    bend_radius: float = 6.0  # [E] inner-wall radius of the swept bend tube = the key's
    #                            own inner bend radius, so the cavity matches the smooth
    #                            90 deg curve on the key. (The tube centreline arc is this
    #                            + the bore radius.) The short arm thus gains a rounded
    #                            bend surface, which is what the real key would cut.

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

    # ---- Softening the -X end (both DEFAULT OFF, so v2 is unchanged) ------
    # ``scoop_r`` alone puts the sphere's centre ON the surface, so the dish is a
    # hemisphere and its rim meets the surface at 90 deg -- an edge you can feel,
    # right where a finger is meant to hook. Setting ``scoop_depth`` instead
    # pushes the centre back out along the surface normal until the cap is only
    # that deep, which for a given depth trades dish width for rim angle: the rim
    # tangent makes arcsin(rho / scoop_r) with the surface, where the cap's radius
    # is rho = sqrt(2*scoop_r*scoop_depth - scoop_depth^2). A bigger scoop_r at
    # the same depth is a wider, shallower, blunter dish. 0 = centre on the
    # surface, i.e. a hemisphere, as v2 has it.
    scoop_depth: float = 0.0  # [E] cap depth; 0 keeps the v2 hemisphere
    bar_slot_round: float = 0.0  # [E] fillet the slot CUTTER's four lengthwise
    #                                edges before subtracting it, so the slot's
    #                                mouth is a rounded rectangle rather than one
    #                                with four sharp corner points. Filleting the
    #                                cutter works where filleting the finished
    #                                solid does not -- a Box is trivial for OCCT,
    #                                the cavity's spline-bounded edges are not.


# Single shared instance; import and override fields as measurements arrive.
KEYSTORE = KeyStoreParams()
