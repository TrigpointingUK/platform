"""Parametric dimensions for the Ordnance Survey flush bracket.

All dimensions in **millimetres** (build123d's native unit).

Provenance tags, as elsewhere in this collection:

    [D]  Dimensioned  - taken from a drawing or a measured original.
    [E]  Estimated    - a plausible guess, NOT yet confirmed against a real part.
    [S]  Spec         - a nominal engineering-standard value.

Values were ported from the Blender render model
(``Blender/Hotine/trig_pillar.py``, ``build_flush_bracket``), where they were
expressed in metres. The render model's own [D] tags are carried across: they
came from measuring photographs of real brackets against the known plate width,
which is good enough to look right at render scale but is NOT the same as
calipers on a real casting. Treat every [D] here as "dimensioned from imagery"
until a physical bracket is measured, then re-tag.

Published plate sizes disagree with the render model -- 90 x 175 mm is commonly
quoted, the render model says 85.5 x 172 -- which is precisely why the physical
measurement matters. Nothing downstream needs to change when it arrives: every
feature below is anchored to a plate edge or to another feature, not to an
absolute coordinate.

Coordinate frame
----------------
    x = 0   at the plate's vertical centreline
    z = 0   at the plate's BOTTOM edge, +z upward
    y = 0   at the plate's FRONT face (the flat the beading sits on), +y forward

So the plate body occupies y < 0, and everything proud of it -- beading,
lettering, broad arrow -- occupies y > 0.

**Sign convention, inherited deliberately from the render model:** viewed from
the front (from +y, looking along -y), **+x is to the LEFT**. Hence the 'O' of
OSBM sits at +x and the 'S' at -x, and 'B' at +x with 'M' at -x. Every x offset
below is transcribed straight from the render model, so keeping its handedness
avoids a whole class of mirror errors. Mirror once, at export, if a
conventional front view is ever wanted.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FlushBracketParams:
    # ---- Plate ------------------------------------------------------------
    w: float = 85.5  # [D] plate width
    h: float = 172.0  # [D] plate height
    bead_r: float = 5.0  # [D] semicircular beading radius

    # Total plate depth is set by the broad-arrow ledge behind it: the rear
    # plate's back face is flush with the back of the arrow's trapezoidal cap,
    # i.e. cap_depth - arrow protrusion. The near/rear split is 1:2.
    total_plate_d: float = 25.4 - 4.5  # [D] 20.9 mm front-to-back
    near_d_frac: float = 1 / 3  # [D] near plate is one third of the total
    rear_h_frac: float = 1902 / 3220  # [D] rear plate height / front, top-aligned

    @property
    def near_d(self) -> float:
        """Depth of the front plate (y = -near_d .. 0)."""
        return self.total_plate_d * self.near_d_frac

    @property
    def rear_d(self) -> float:
        """Depth of the rear plate, behind the front plate."""
        return self.total_plate_d * (1 - self.near_d_frac)

    @property
    def rear_h(self) -> float:
        """Height of the rear plate (top-aligned with the front plate)."""
        return self.h * self.rear_h_frac

    @property
    def hw(self) -> float:
        return self.w / 2

    # ---- Keyhole cut-outs (two, near the top) -----------------------------
    # Cuboid slot with a hemispherical/ellipsoidal scoop at its bottom, and a
    # convex rib bridging it. These take the staff bracket's fixing lugs.
    kh_w: float = 16.9  # [D] slot width
    kh_h: float = 28.0  # [D] cuboid portion height
    kh_d: float = 12.1  # [D] slot depth into the plate
    kh_gap: float = 21.1  # [D] gap between the two slots
    kh_below_bead: float = 5.0  # [D] slot top this far below the top bead's inner edge

    # Bridging rib across each slot
    rib_h: float = 11.5  # [D] rib height
    rib_d: float = 5.0  # [D] rib max thickness (front face back to rib rear)
    rib_bevel: float = 2.0  # [D] convex bevel radius on the rib's long edges
    rib_below_slot_top: float = 11.6  # [D] rib top below the slot top

    # ---- Broad arrow ------------------------------------------------------
    # The arrow is ONE solid trapezoidal mass standing proud of the plate, with
    # two V-grooves cut into its front face dividing it into three lobes. It is
    # NOT three separate legs with plate showing between them -- the grooves do
    # not part the mass, they are cut into it, and they run out before reaching
    # the top. An earlier version modelled it the other way round and was
    # wrong in a way no amount of dimension-tweaking would have fixed.
    ba_below_bead: float = 52.8  # [D] arrow top below the top bead's inner edge
    # ``ba_w_top`` and ``ba_w_bot`` describe the arrow's FRONT face -- the flat
    # top of the relief -- not its footprint on the plate. The front face is
    # the crisp trapezium you see in a photograph, and its top edge is
    # necessarily a front-face dimension because that edge is where the arrow
    # runs into the ledge. The footprint is wider, and is derived from these by
    # the draft (see ``_arrow_mass``).
    ba_h: float = 36.1  # [D] height of the front face, top edge to bottom edge
    ba_w_bot: float = 31.3  # [D] front face width at the bottom edge
    # From the ratio measured on a reference photograph (top = 0.46 x bottom),
    # a proportion that survives the photograph's perspective because the whole
    # arrow sits within a few centimetres. The absolute size does not, and
    # wants calipers.
    ba_w_top: float = 14.6  # [E] 0.465 x ba_w_bot
    ba_relief: float = 4.5  # [D] protrusion proud of the plate face

    # The two V-grooves. Each is deepest at the arrow's bottom edge, where its
    # two draft faces meet ON the plate face -- cut right through the relief,
    # with nothing flat between them -- and shallows steadily to nothing at its
    # upper end. Its width at the surface grows in step with its depth, since
    # the V's half-angle is constant, so each groove starts as a hairline near
    # the apex and opens out as it descends.
    ba_ch_width: float = 4.0  # [E] groove opening where it breaks the front
    #                              face, measured AT THE BOTTOM EDGE (it is
    #                              narrower everywhere above that)
    ba_ch_top_drop_frac: float = 0.20  # [E] groove start below the top edge,
    #                                       as a fraction of ba_h
    ba_ch_top_sep: float = 3.0  # [E] ridge left between the two groove tops
    ba_ch_bot_frac: float = 0.35  # [E] where a groove crosses the bottom edge,
    #                                   as a fraction of the half bottom width

    # The arrow's top is also the levelling datum, and it is carried back into
    # the plate as a trapezoidal ledge -- the shelf the invar staff foot sits
    # on. This is the feature that makes a flush bracket a *bracket*.
    #
    # Its width is NOT free at either end: at the front it is the arrow's own
    # top edge, and at the back it spans the full width of the rectangular
    # opening it runs into. Both are derived in ``_Layout`` rather than being
    # separate numbers that could drift out of agreement with the features they
    # have to meet.
    # Its depth is not a free number either -- it runs from the arrow's front
    # face to the back of the plate, so it is ba_relief + total_plate_d (25.4
    # mm on the current figures). Derived in ``_Layout``.
    #
    # There is deliberately no ledge THICKNESS. The ledge is not a slab: it is
    # the top surface of the same wedge the arrow is the front of. Modelling it
    # as a slab is what made its sides non-coplanar with the arrow's flanks.

    # ---- Wedge opening above the arrow ------------------------------------
    # Cut through both plates. Rectangular at the back, and extending further
    # down at the front, so the bottom slopes down toward the viewer.
    hole_w: float = 31.4  # [D] opening width
    hole_below_slots: float = 1.0  # [D] opening top below the scoop bottoms
    # How far down the arrow the opening's front edge sits -- equivalently,
    # where the plate surface closes in around the arrow, and so where the
    # arrow's flank planes first meet it. This genuinely varies between
    # brackets: on the North Ockendon pillar the flank plane meets the plate
    # right at the bottom of the arrow (1.0), while on the reference
    # photograph it does so just over halfway down (~0.55).
    hole_front_bot_frac: float = 0.55  # [E] of ba_h, below the arrow's top edge

    # ---- Keying bar and anchor (cast into the pillar concrete) ------------
    bar_r_frac: float = 477 / 667  # [D] bar dia as a fraction of the drop from
    #                                   the opening bottom to the rear plate bottom
    bar_r_scale: float = 0.80  # [D] bar drawn at 80% of that proportional value
    bar_depth: float = 25.0 * 1.25  # [D] 31.25 mm behind the rear plate
    bar_fillet_frac: float = 0.25  # [D] fillet radius as a fraction of bar radius
    # The render model sits the bar so its fillet disc exactly touches the rear
    # plate's bottom edge. That tangency is degenerate in a B-rep -- and would
    # cast (and print) as a zero-thickness knife edge -- so the bar is lifted
    # clear by this much. Invisible at 1:1; keeps the fillet well conditioned.
    bar_clearance: float = 0.5  # [E]

    anchor_h: float = 35.0  # [D] nominal anchor size; dia is 1.5x this
    anchor_dia_scale: float = 1.5  # [D]
    anchor_depth: float = 10.0  # [D]
    anchor_bevel_frac: float = 0.15  # [D] of anchor radius, capped at 25% of depth

    # ---- OSBM lettering ---------------------------------------------------
    # Each letter is placed and sized individually, because on a real casting
    # they are individually punched and are NOT a uniform typeface run. Sizes
    # are the letter's bounding box; the glyph is scaled to fill it.
    let_relief: float = 4.5  # [D] protrusion, all four letters

    os_below_bead: float = 48.4  # [D] top of O and S below the top bead inner edge
    os_w: float = 16.0  # [D]
    os_h: float = 24.0  # [D]
    os_sep: float = 56.0  # [D] O-to-S centre-to-centre

    b_w: float = 16.7  # [D]
    b_h: float = 24.9  # [D]
    b_gap_from_bead: float = 4.9  # [D] B's outer edge to the bead's inner edge
    b_below_os: float = 13.6  # [D] B's top below the bottom of O

    m_w: float = 17.6  # [D]
    m_h: float = 24.5  # [D]
    m_gap_from_bead: float = 2.9  # [D] M's outer edge to the bead's inner edge
    m_below_os: float = 14.7  # [D] M's top below the bottom of S

    # The BsM series carries a third letter, an S, between the B and the M.
    # Sized from the B and M boxes and hung from the lower of their two tops,
    # rather than measured in its own right -- so it tracks them if they are
    # re-measured. [E] until a BsM bracket is measured directly.
    bsm_s_w_frac: float = 1.0  # [E] of the mean of the B and M widths
    bsm_s_h_frac: float = 1.0  # [E] of the mean of the B and M heights

    # NB the typeface is NOT set here: it varies by era, so it belongs to the
    # bracket style (see styles.py, resolve_style). Every era's lettering is a
    # grotesque sans -- there are no serifs on any flush bracket.

    # ---- Number panel -----------------------------------------------------
    # The zone below B/M carrying the bracket number (and, on a bespoke print,
    # whatever the customer asks for). Bounded by the B/M bottoms above and the
    # bottom bead below. Not yet measured on a real bracket: the figures here
    # are derived from the render model's letter placement, so [E].
    num_relief: float = 4.5  # [E] assumed same as the OSBM letters
    num_cap_h: float = 22.0  # [E] nominal digit cap height
    num_margin_bottom: float = 12.0  # [E] baseline above the bottom bead inner edge

    # ---- Casting draft ----------------------------------------------------
    # The sides of the raised lettering and the broad arrow are not vertical:
    # a sand-casting pattern must leave its mould, so every raised face leans
    # inward. On a flush bracket the lean is pronounced -- far more than the
    # 1-3 deg of ordinary engineering draft.
    #
    # A single ANGLE is the physically meaningful parameter, since that is what
    # lets the pattern draw. The visible consequence is the top of a letter
    # being smaller than its base, and that ratio differs per glyph because it
    # depends on stroke width -- so it is an output, not a setting. At 13 deg:
    #
    #     O 0.54   S 0.58   B 0.62   M 0.49      mean 0.52
    #
    # Calibrated against the observation that the top of a letter is roughly
    # half the area of its base. ``flush_bracket.letter_draft_ratios()``
    # reports these, to re-check against a real casting. Set to 0 to disable.
    relief_draft_deg: float = 13.0  # [E] from observed top:base area ~= 0.5


# Single shared instance; import and override fields as measurements arrive.
FB = FlushBracketParams()
