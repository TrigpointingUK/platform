"""Parametric dimensions for the plug **driver tool**.

All dimensions in **millimetres** (build123d's native unit). Provenance tags
match the convention used by the plug model:

    [D]  Dimensioned  - taken from a mating part or a measured original.
    [E]  Estimated    - a plausible ergonomic guess, tune on the first print.

The tool is a face/pin spanner: an ellipsoidal ("discus") knurled disc from
whose flat base protrude two steel dowel pegs that drop into the plug's two
upper-ring clearance holes, so the whole plug can be screwed in/out of the
pillar spider. The **peg spacing and the mating hole size are owned by the plug**
(``models.plug.params.PLUG.clr_hole_spacing`` / ``clr_hole_r``) and read from
there at build time -- they are a physical interface, not a driver-local choice.

The knurls are a **directional sawtooth**: each tooth has a long shallow ramp
and a short near-radial steep face. With ``catch_ccw`` True the steep faces look
anticlockwise, so a hand twisting the disc anticlockwise (the loosening sense for
a right-hand thread) catches on them (high grip / torque), while twisting
clockwise to tighten runs down the ramps and slips (capped torque) -- more
mechanical advantage for loosening than tightening, in one self-contained tool.

Coordinate frame: z = 0 at the flat base, +z upward, revolved about the Z axis.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriverParams:
    # ---- Ellipsoidal body (a truncated triaxial ellipsoid / discus) ------
    # Built round (semi-minor radius ``body_r``) then stretched along X by
    # ``plan_aspect`` into an ellipse in plan view: major axis 2:1, running
    # through the two pegs so it extends well beyond them (grip leverage + bulk
    # around the pegs). The knurl teeth stretch with the plan, which is fine.
    body_r: float = 30.0  # [E] semi-MINOR (Y) equatorial radius -> Ø60 across
    plan_aspect: float = 2.0  # [D] major:minor plan ratio (2:1) -> Ø120 along X
    body_half_h: float = 20.0  # [E] half the overall height -> 40 mm tall
    base_flat_r: float = 26.0  # [E] flat top/base MINOR radius (major = x aspect;
    #                              must, once stretched, clear the pegs + bore)

    # ---- Directional sawtooth knurl band (round the equator) -------------
    n_teeth: int = 30  # [E] tooth count
    tooth_depth: float = 3.0  # [E] radial crest-to-root depth
    band_half_h: float = 12.0  # [E] knurl band spans equator +/- this
    steep_frac: float = 0.15  # [E] fraction of each tooth pitch that is the
    #                              steep (near-radial) catch face; the rest is
    #                              the shallow ramp
    catch_ccw: bool = True  # [E] steep faces look anticlockwise -> loosening
    #                            (RH thread) bites, tightening slips. Flip if the
    #                            spider thread proves left-handed.

    # ---- Steel dowel pegs (BOM item; only their bores are modelled) ------
    # The dowels are glued in (structural epoxy) -- see README. The bore is a
    # clearance fit with mechanical-keying features, not an interference/press
    # fit (a wedged dowel would split the printed layers).
    peg_dia: float = 8.0  # [D] Ø8 mm silver-steel / dowel (in the plug's Ø9 hole)
    peg_bore_dia: float = 8.3  # [E] glue clearance: ~0.3 mm over the dowel for
    #                              the epoxy annulus (raise for a looser fit)
    peg_bore_depth: float = 25.0  # [E] embedment into the body (long = low bearing)
    peg_protrusion: float = 10.0  # [D] stick-out below the base; dowel ~= depth+this
    #                                 (clears the plug's 6 mm upper ring)

    # Mechanical keying + glue management for the epoxy joint:
    peg_groove_n: int = 3  # [E] annular grooves down the bore; epoxy fills them
    #                          and keys to the plastic so the plug cannot pull out
    peg_groove_depth: float = 0.8  # [E] radial extra depth of each groove
    peg_groove_h: float = 1.5  # [E] axial height of each groove
    peg_mouth_chamfer: float = 0.75  # [E] lead-in + glue fillet at the base mouth
    peg_vent_dia: float = 1.5  # [E] vent from the blind end to the top face, so
    #                              surplus epoxy/air escapes (no hydraulic lock)


# Single shared instance; import and override fields as measurements arrive.
DRIVER = DriverParams()
