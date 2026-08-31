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
and a short near-radial steep face. A gripping hand drives the knob by *pushing*
against tooth faces, so it bites hardest in the direction whose drive face is the
steep one. With ``catch_ccw`` True the steep faces look clockwise, so twisting
anticlockwise (the loosening sense for a right-hand thread) drives against them
(high grip / torque) while twisting clockwise to tighten pushes the shallow ramps
and slips (capped torque) -- more mechanical advantage for loosening than
tightening, in one self-contained tool.

Coordinate frame: z = 0 at the flat base, +z upward, revolved about the Z axis.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriverParams:
    # ---- Sculpted knob body ----------------------------------------------
    # A profile revolved round, then stretched along X by ``plan_aspect`` into a
    # 2:1 ellipse in plan (major axis through the pegs, so it extends well beyond
    # them for grip leverage + bulk). Vertical profile: a flat base with a
    # rounded edge, a straight knurled band, then a *sculpted* top -- a flat
    # central plateau (for the logo) blending smoothly out and down to just above
    # the knurl. The knurl teeth stretch with the plan, which is fine.
    body_r: float = 30.0  # [E] semi-MINOR (Y) radius = knurl crest -> Ø60 across
    plan_aspect: float = 2.0  # [D] major:minor plan ratio (2:1) -> Ø120 along X
    body_half_h: float = 20.0  # [E] half the overall height -> 40 mm tall
    base_flat_r: float = 26.0  # [E] flat base MINOR radius (seating + peg support;
    #                              major = x aspect; must clear the pegs + bore)
    plateau_r: float = 14.0  # [E] flat top plateau MINOR radius (the logo sits
    #                            here; major = x aspect -> ~Ø56 x Ø28 flat)
    top_lip: float = 1.0  # [E] straight lip above the knurl before the sculpt
    #                         starts ("a little bit above the knurling")

    # ---- Directional sawtooth knurl band (round the rim) -----------------
    # Teeth are laid out at equal ARC LENGTH round the ellipse, so each is the
    # same linear size; the pitch is (perimeter / n_teeth).
    n_teeth: int = 46  # [E] tooth count (~6 mm pitch on the ~290 mm perimeter)
    tooth_depth: float = 3.0  # [E] crest-to-root depth (inset along the normal)
    band_half_h: float = 12.0  # [E] knurl band spans equator +/- this
    steep_frac: float = 0.15  # [E] fraction of each tooth pitch that is the
    #                              steep (near-radial) catch face; the rest is
    #                              the shallow ramp
    catch_ccw: bool = True  # [E] steep faces look CLOCKWISE, so an anticlockwise
    #                            (loosening, RH thread) turn drives against them
    #                            and bites while tightening slips. Flip if the
    #                            spider thread proves left-handed.

    # Fading the teeth out toward the two ENDS of the ellipse. Anything that
    # breaks the rim there -- a bore mouth, a scoop, a slot -- truncates whatever
    # teeth it lands on into thin sharp spikes, so a tool with end features wants
    # smooth end caps. Both thresholds are |x| / semi-major, measured on the
    # crest ellipse: teeth are full depth inside ``knurl_fade_start`` and gone
    # beyond ``knurl_fade_end``, smoothstepped between. The DEFAULTS DISABLE THE
    # FADE (start = end = 1.0), so v1 and v2 are unchanged; v3 overrides them.
    knurl_fade_start: float = 1.0  # [E] |x|/a where the teeth begin to shallow
    knurl_fade_end: float = 1.0  # [E] |x|/a where they vanish altogether
    knurl_crest_out: float = 0.0  # [E] lift the cutting wheel's crests this far
    #                                 OUTSIDE the body. The knurl is made by
    #                                 intersecting the wheel with the body, so a
    #                                 crest that pokes out is clipped back to the
    #                                 body's own surface -- which (a) lets the
    #                                 faded end caps stay exactly, smoothly
    #                                 elliptical instead of picking up the
    #                                 wheel's polygon facets, and (b) takes the
    #                                 knife edge off every tooth crest, replacing
    #                                 it with a narrow flat of the true surface.
    #                                 Must exceed the polygon's worst sagitta
    #                                 (~0.24 mm at 46 teeth). 0 = off.

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

    # ---- Top-face detail -------------------------------------------------
    # A shallow groove runs along the major axis from each vent hole out to the
    # rim: it marks the peg axis, so the user can sight it against the plug's two
    # holes when offering the tool up (improves alignment accuracy).
    vent_groove_w: float = 2.5  # [E] groove width
    vent_groove_depth: float = 1.0  # [E] groove depth (follows the sculpted top)
    # Embossed TrigpointingUK logo on the flat plateau.
    logo_amount: float = 0.9  # [E] emboss height proud of the plateau
    logo_fill: float = 0.85  # [E] the artwork is scaled so its bounding circle is
    #                            this fraction of the plateau's MINOR radius. It is
    #                            a knob of its own because plateau_r is set by the
    #                            body's shape, not by how big the badge should be:
    #                            a version that needs a wider plateau (v3, whose
    #                            shallow sculpt would otherwise bulge) can drop
    #                            this to keep the logo the same physical size.


# Single shared instance; import and override fields as measurements arrive.
DRIVER = DriverParams()
