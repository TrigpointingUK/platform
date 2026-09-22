"""Ordnance Survey flush bracket: cast plate with beading, keying and lettering.

Ported from the Blender render model's ``build_flush_bracket`` (see
``Blender/Hotine/trig_pillar.py``), re-cut as an exact B-rep so it can be
dimensioned, measured and printed rather than merely rendered.

Local frame (see ``params`` for the full note):

    x = 0 at the plate centreline, **+x to the LEFT when viewed from the front**
    z = 0 at the plate's bottom edge, +z up
    y = 0 at the plate's front face, +y forward (out of the pillar)

Two variants are offered, selected by ``keying``:

    keying=True   the full casting, including the rear plate, keying bar and
                  anchor block that lock it into the pillar concrete
    keying=False  the front plate only, with a flat back -- a wall-hangable
                  replica, and much the easier print

Order of operations matters. The keyhole slots and the wedge opening are cut
**before** the broad arrow and its ledge are added, so the arrow is never
truncated by them. The render model needed extra fill volumes precisely because
it cut in the other order.
"""

from __future__ import annotations

import math

from build123d import (
    Box,
    BuildLine,
    BuildPart,
    BuildSketch,
    Cylinder,
    GeomType,
    Line,
    Plane,
    Polyline,
    Pos,
    Rectangle,
    Rot,
    Face,
    Text,
    ThreePointArc,
    Transition,
    Vector,
    Vertex,
    Wire,
    extrude,
    fillet,
    loft,
    make_face,
    mirror,
    scale,
    sweep,
)

from models.flush_bracket.params import FB, FlushBracketParams
from models.flush_bracket.relief import drafted
from models.flush_bracket.styles import (
    DEFAULT_STYLE,
    BracketStyle,
    resolve_style,
)

# How far a raised feature is sunk into the plate face before it starts
# protruding. Nothing structural: it just guarantees the union always bites,
# rather than relying on two faces being exactly coincident.
EMBED = 0.5


def _yz_plane(y: float) -> Plane:
    """A plane at ``y`` whose local axes are world (+x, +z).

    Sketches drawn on it therefore read as a front elevation, which is how
    every dimension in ``params`` is expressed.
    """
    return Plane(origin=(0, y, 0), x_dir=(1, 0, 0), z_dir=(0, -1, 0))


def _front_section(y: float, width: float, z_lo: float, z_hi: float):
    """An axis-aligned rectangle of the given extent, standing at ``y``."""
    return _yz_plane(y) * Pos(0, (z_lo + z_hi) / 2) * Rectangle(width, z_hi - z_lo)


# --------------------------------------------------------------------------
# Derived geometry. Everything anchors to a plate edge or another feature, so
# a change to w/h/bead_r propagates without any absolute coordinate moving.
# --------------------------------------------------------------------------
class _Layout:
    """Resolved feature positions for one parameter set."""

    def __init__(self, p: FlushBracketParams,
                 style: BracketStyle = DEFAULT_STYLE):
        self.p = p
        self.style = style
        self.hw = p.hw
        self.z_top = p.h
        self.bead_inner_z = p.h - p.bead_r  # inner edge of the top bead
        self.bead_inner_x = p.hw - p.bead_r  # inner edge of the left bead (+x)

        # Keyhole slots
        self.kh_z_top = self.bead_inner_z - p.kh_below_bead
        self.kh_z_bot = self.kh_z_top - p.kh_h
        self.kh_scoop_r = p.kh_w / 2
        self.kh_scoop_bot = self.kh_z_bot - self.kh_scoop_r
        self.kh_cx = p.kh_gap / 2 + p.kh_w / 2  # centre offset, mirrored in x

        # Bridging rib
        self.rib_z_top = self.kh_z_top - p.rib_below_slot_top
        self.rib_z_mid = self.rib_z_top - p.rib_h / 2

        # Broad arrow
        self.ba_z_top = self.bead_inner_z - p.ba_below_bead
        self.ba_z_bot = self.ba_z_top - p.ba_h

        # The ledge is bounded by the features it runs between, not by numbers
        # of its own: at the front it is the arrow's top edge, at the back it
        # spans the full width of the opening it meets.
        self.ledge_front_w = p.ba_w_top
        self.ledge_back_w = p.hole_w
        # The ledge runs from the arrow's front face to the back of the plate,
        # so its depth is not a free number either.
        self.ledge_depth = p.ba_relief + p.total_plate_d

        # Wedge opening: rectangular at the back, dropping to the arrow bottom
        # at the front.
        self.hole_z_top = self.kh_scoop_bot - p.hole_below_slots
        self.hole_z_bot_back = self.ba_z_top
        self.hole_z_bot_front = (
            self.ba_z_top - p.ba_h * p.hole_front_bot_frac
        )

        # Plate depths
        self.y_near_back = -p.near_d
        self.y_rear_back = -(p.near_d + p.rear_d)
        self.rear_z_bot = p.h - p.rear_h

        # Keying bar and anchor
        drop = self.hole_z_bot_back - self.rear_z_bot
        self.bar_r = (drop * p.bar_r_frac / 2) * p.bar_r_scale
        self.bar_fillet = self.bar_r * p.bar_fillet_frac
        self.bar_z_mid = (
            self.rear_z_bot + self.bar_r + self.bar_fillet + p.bar_clearance
        )
        self.bar_y_back = self.y_rear_back - p.bar_depth
        self.anchor_r = p.anchor_h * p.anchor_dia_scale / 2
        self.anchor_bevel = min(self.anchor_r * p.anchor_bevel_frac,
                                p.anchor_depth * 0.25)

        # OSBM letters: (glyph, centre x, width, height, top z).
        # The style's letter_scale carries the era difference: early brackets
        # have a visibly smaller, lighter legend than S3700+ and the 5-digit
        # series, where O S B M nearly fill the plate width.
        k = style.letter_scale
        os_z_top = self.bead_inner_z - p.os_below_bead
        os_z_bot = os_z_top - p.os_h
        b_outer_x = self.bead_inner_x - p.b_gap_from_bead
        m_outer_x = -self.bead_inner_x + p.m_gap_from_bead
        b_z_top = os_z_bot - p.b_below_os
        m_z_top = os_z_bot - p.m_below_os
        self.letters = [
            ("O", p.os_sep / 2, p.os_w * k, p.os_h * k, os_z_top),
            ("S", -p.os_sep / 2, p.os_w * k, p.os_h * k, os_z_top),
            ("B", b_outer_x - p.b_w / 2, p.b_w * k, p.b_h * k, b_z_top),
            ("M", m_outer_x + p.m_w / 2, p.m_w * k, p.m_h * k, m_z_top),
        ]
        if style.legend_has_middle_s:
            # BsM: the number font was enlarged until the prefix no longer
            # fitted, so the S moved up between the B and the M. Centred on the
            # plate, hung from the lower of the B/M tops.
            self.letters.append((
                "S",
                0.0,
                (p.b_w + p.m_w) / 2 * p.bsm_s_w_frac * k,
                (p.b_h + p.m_h) / 2 * p.bsm_s_h_frac * k,
                min(b_z_top, m_z_top),
            ))
        # The free panel below B/M, where the bracket number goes.
        self.num_z_top = min(os_z_bot - p.b_below_os - p.b_h,
                             os_z_bot - p.m_below_os - p.m_h)
        self.num_z_bot = p.bead_r + p.num_margin_bottom


# --------------------------------------------------------------------------
# Feature builders
# --------------------------------------------------------------------------
def _beading(p: FlushBracketParams):
    """Half-round moulding swept round the front face perimeter.

    The section is a semicircle centred *on* the plate edge line -- so the bead
    overhangs the plate outline by ``bead_r`` all round and the bracket's
    overall footprint is (w + 2*bead_r) x (h + 2*bead_r). ``Transition.RIGHT``
    mitres the corners, which is what the render model built by hand.
    """
    hw, h, br = p.hw, p.h, p.bead_r
    with BuildPart() as bp:
        with BuildLine() as path:
            Polyline(
                [(-hw, 0, 0), (hw, 0, 0), (hw, 0, h), (-hw, 0, h)], close=True
            )
        # Section plane: normal along the path's start tangent (+x), local +y
        # forward (+world y) so the dome faces out of the pillar.
        sec_plane = Plane(origin=(-hw, 0, 0), x_dir=(0, 0, -1), z_dir=(1, 0, 0))
        with BuildSketch(sec_plane):
            with BuildLine():
                Line((-br, 0), (br, 0))
                ThreePointArc((br, 0), (0, br), (-br, 0))
            make_face()
        sweep(path=path.line, transition=Transition.RIGHT)
    return bp.part


def _raise(face, relief: float, draft_deg: float):
    """Stand a flat outline proud of the plate face, with casting draft.

    The sides of a cast letter are not vertical: the pattern has to leave the
    sand, so every raised face leans inward and the top of a letter is
    markedly smaller than its base. Modelling that is most of what makes a
    print read as *cast* rather than milled.

    The draft is measured from the plate face, so the outline passed in is the
    letter's footprint at ``y = 0`` -- its widest section, which is what the
    measured letter boxes in ``params`` describe. The short prismatic stub
    below that is only there so the union with the plate always bites, and is
    deliberately not drafted: drafting it would pull the footprint in.

    See ``relief.drafted`` for why the offset is computed on a raster rather
    than with ``extrude(taper=...)``.
    """
    return drafted(face, relief=relief, draft_deg=draft_deg, embed=EMBED)


def _keyhole_cutter(p: FlushBracketParams, lay: _Layout, cx: float):
    """One keyhole pocket: a U-shaped profile lofted back into the plate.

    The pocket is **one** solid, not a cuboid unioned with a rounded bottom.
    That matters more than it sounds. Unioning them leaves the trough tangent
    to the pocket's side walls and its end cap coplanar with the back wall --
    two of the cases OCCT's booleans handle worst -- and the result is a ring
    of sliver faces lying in the junction plane, which reads as a step exactly
    where the rectangular and rounded parts meet. Tangency cannot be designed
    out, because a rounded bottom meeting a flat wall smoothly *is* tangency.
    So the union goes instead: the profile is a single closed wire, straight
    sides running into an arc, and the junction is an edge within one face
    rather than a boolean between two.

    ``kh_scoop_angle_deg`` raises the arc's centre on the back profile, so the
    trough shallows toward the back. At 0 the two profiles are identical and
    the loft is a plain prism.
    """
    r = lay.kh_scoop_r
    rise = p.kh_d * math.tan(math.radians(p.kh_scoop_angle_deg))

    def _profile(z_centre: float):
        with BuildSketch(Plane.XZ) as sk:
            with BuildLine():
                Line((cx - r, lay.kh_z_top), (cx - r, z_centre))
                ThreePointArc((cx - r, z_centre), (cx, z_centre - r),
                              (cx + r, z_centre))
                Line((cx + r, z_centre), (cx + r, lay.kh_z_top))
                Line((cx + r, lay.kh_z_top), (cx - r, lay.kh_z_top))
            make_face()
        return sk.sketch.faces()[0]

    front = _profile(lay.kh_z_bot)
    back = Pos(0, -p.kh_d, 0) * _profile(lay.kh_z_bot + rise)
    return loft([back, front], ruled=True)


def _bridging_rib(p: FlushBracketParams, lay: _Layout, cx: float):
    """The convex rib spanning one keyhole slot, flush with the front face.

    Built as a rounded-rectangle YZ profile extruded along x, so the rib's ends
    stay flat where they meet the slot walls (a swept bevel would round them).
    """
    yf, yb = 0.0, -p.rib_d
    zt = lay.rib_z_mid + p.rib_h / 2
    zb = lay.rib_z_mid - p.rib_h / 2
    bv = p.rib_bevel
    n = 6
    pts: list[tuple[float, float]] = []
    for cy, cz, a0 in (
        (yf - bv, zt - bv, 0.0),
        (yb + bv, zt - bv, math.pi / 2),
        (yb + bv, zb + bv, math.pi),
        (yf - bv, zb + bv, 3 * math.pi / 2),
    ):
        for k in range(n + 1):
            a = a0 + (math.pi / 2) * k / n
            pts.append((cy + bv * math.cos(a), cz + bv * math.sin(a)))
    with BuildPart() as bp:
        with BuildSketch(Plane.YZ):
            with BuildLine():
                Polyline(pts, close=True)
            make_face()
        extrude(amount=p.kh_w / 2 + 0.5, both=True)
    return Pos(cx, 0, 0) * bp.part


def _slot_cutter(p: FlushBracketParams, lay: _Layout):
    """The rectangular opening the staff foot locates in.

    A plain rectangular cut through the plate. It used to be lofted with a
    sloping floor, which was an attempt to model in the *opening* something
    that actually belongs to the arrow: the ledge's top surface is the floor at
    the back, and the arrow fills the rest from below. With the arrow and ledge
    built as one wedge, the opening has nothing left to do but be a hole.
    """
    # Overshoot the FRONT face only. Carrying the cut past the back face as
    # well clips the top of the keying bar where it lands on the rear plate,
    # which breaks its fillet -- the sloping floor the opening used to have
    # was incidentally keeping the cut clear of it.
    over = 1.0
    z_lo, z_hi = lay.hole_z_bot_front, lay.hole_z_top
    depth = p.total_plate_d + over
    return Pos(0, over - depth / 2, (z_lo + z_hi) / 2) * Box(
        p.hole_w, depth, z_hi - z_lo)


def _arrow_channel(p: FlushBracketParams, lay: _Layout, sign: int):
    """One V-groove cutter for the broad arrow.

    The groove's vertex line lies **on the plate face**, so its two draft faces
    meet exactly where they reach the plate rather than leaving a flat floor
    between them. Its cross-section is therefore a triangle with its apex at
    y = 0, widening forward to break the arrow's front surface.

    The groove is **not** of constant depth. It is deepest at the bottom edge,
    where it reaches the plate, and shallows steadily to nothing at its upper
    end, which is why the two grooves fade out near the apex rather than
    stopping.

    That falls out of lofting from a single point **on the arrow's front
    surface** to the full section at the bottom. The apex of the intermediate
    sections then slides from ``y = ba_relief`` down to ``y = 0``, so the depth
    below the surface grows linearly from nothing to the full relief. Because
    the V's half-angle is unchanged along the way, the width where the groove
    breaks the surface grows in step, from nothing to ``ba_ch_width``.

    Anchoring the tip to the plate instead -- the obvious reading of "the
    faces meet at the plate" -- would be wrong: the cutter would then sit
    *below* the surface near the top and hollow out the arrow rather than
    grooving it.
    """
    z_start = lay.ba_z_top - p.ba_h * p.ba_ch_top_drop_frac
    x_start = sign * p.ba_ch_top_sep / 2
    x_end = sign * (p.ba_w_bot / 2) * p.ba_ch_bot_frac
    z_end = lay.ba_z_bot

    dx, dz = x_end - x_start, z_end - z_start
    length = math.hypot(dx, dz)
    if length < 1e-6:
        raise ValueError("degenerate arrow channel")
    ux, uz = dx / length, dz / length

    # A plane whose normal runs along the groove and whose local +y is world
    # +y, so the section can be drawn as (across-groove, out-of-plate).
    plane = Plane(origin=(x_start, 0, z_start), x_dir=(uz, 0, -ux),
                  z_dir=(ux, 0, uz))
    # Carry the cutter past the front surface so it breaks through cleanly;
    # the opening width is specified AT the front face, so scale up in
    # proportion to how far past it the cutter runs.
    y_max = p.ba_relief + 1.5
    hw = (p.ba_ch_width / 2) * (y_max / p.ba_relief)
    with BuildSketch(plane) as sec:
        with BuildLine():
            Polyline([(0.0, 0.0), (-hw, y_max), (hw, y_max)], close=True)
        make_face()

    tip = Vertex(x_start, p.ba_relief, z_start)
    # ``BuildSketch(plane)`` has already placed the section in world
    # coordinates on that plane, so it is moved along the groove with a plain
    # translation. Multiplying by the plane again would compound the transform
    # and send the cutter off at a tangent -- which, being a subtraction that
    # merely misses, shows up as an arrow with no grooves rather than as an
    # error.
    full = Pos(ux * length, 0, uz * length) * sec.sketch.faces()[0]
    cutter = loft([tip, full], ruled=True)
    # Carry the full section a little past the bottom edge so the groove is
    # cut cleanly there. This part keeps its apex at y = 0, so it runs along
    # the plate face without biting into it.
    cutter += extrude(full, amount=2.0)
    return cutter


def _arrow_and_ledge(p: FlushBracketParams, lay: _Layout):
    """The arrow and its ledge, as one wedge with continuous planar flanks.

    These cannot be built separately. The arrow's flank and the ledge's side
    are one face on the casting, and the ledge's own geometry is what sets its
    angle: the flank plane is pinned by two edges meeting at the arrow's
    top-front corner -- the arrow's front-face flank edge running down, and the
    ledge's side edge running back. Everything else follows from those.

    Built as a slab of constant-thickness ledge, coplanarity is not merely
    inconvenient but *impossible*: that ledge's side edges are vertical, and a
    plane containing both a vertical edge and the arrow's flank edge would have
    to be ``y = const`` -- a flank with no draft at all. Modelling them apart is
    what left two non-coplanar patches with a void between.

    Note the consequence: the flank's draft is **derived, not chosen**. With the
    ledge opening from ``ba_w_top`` at the front to the full opening width at
    the back, the flanks lean at ``atan((hole_w/2 - ba_w_top/2) / ledge_depth)``
    -- about 18 degrees on the current numbers, appreciably more than the 13
    degrees the lettering uses. ``relief_draft_deg`` still drafts the arrow's
    bottom edge, which is a free edge and so genuinely unconstrained.
    """
    R, D = p.ba_relief, p.total_plate_d
    hw_top, hw_bot = p.ba_w_top / 2, p.ba_w_bot / 2
    z_top, z_bot = lay.ba_z_top, lay.ba_z_bot

    # The flank plane, as x(y, z). Linear in both, so it is a plane, and every
    # section's side edge lies in it by construction.
    s_z = (hw_bot - hw_top) / (z_bot - z_top)   # widening down the arrow
    s_y = (p.hole_w / 2 - hw_top) / lay.ledge_depth  # widening back to the opening
    tan_bot = math.tan(math.radians(p.relief_draft_deg))

    def _section(y: float):
        back = R - y                       # how far behind the front face
        z_b = z_bot - back * tan_bot       # bottom edge, drafted
        x_t = hw_top + back * s_y
        x_b = hw_top + (z_b - z_top) * s_z + back * s_y
        return [(-x_t, z_top), (x_t, z_top), (x_b, z_b), (-x_b, z_b)]

    def _face(poly, y):
        return Face(Wire.make_polygon(
            [Vector(x, y, z) for x, z in poly], close=True))

    return loft([_face(_section(-D), -D), _face(_section(R), R)], ruled=True)


def _broad_arrow(p: FlushBracketParams, lay: _Layout):
    """The Government broad arrow, with its ledge, and its two V-grooves.

    The front face is an isoceles trapezium, ``ba_w_top`` across the top and
    ``ba_w_bot`` across the bottom, carried on two planar flanks that run
    continuously back to the ledge (see ``_arrow_and_ledge``). The V-grooves
    then divide its lower part into three lobes without ever parting it --
    which is what makes this an arrow rather than three legs, and why the plate
    is not visible between the lobes.
    """
    body = _arrow_and_ledge(p, lay)
    for sign in (1, -1):
        body -= _arrow_channel(p, lay, sign)
    return body


def _letter(p: FlushBracketParams, style: BracketStyle, glyph: str, cx: float,
            w: float, h: float, z_top: float):
    """One raised letter, scaled to its individually measured box.

    The glyph is drawn at a nominal size then squeezed to the measured width
    and height, because on a real casting the letters are individually punched
    and are NOT a uniform typeface run. The face comes from the bracket's style
    (every era is a grotesque sans; the weight and size differ) and is an
    approximation -- replacing it with traced outlines is the whole point of
    the glyph-library work.

    The squeeze is applied to the flat **outline**, before the extrusion, not
    to the finished solid. Scaling a drafted solid by different factors in x
    and z would leave the draft angle different on a letter's vertical strokes
    than on its horizontal ones, which no casting pattern does.
    """
    with BuildSketch(Plane.XZ) as sk:
        Text(glyph, font_size=100.0, font=style.font,
             font_style=style.font_style)
    # Plane.XZ's local +x is world +x, which this frame shows to the LEFT, so a
    # glyph drawn on it comes out mirrored on the casting. Flip it back. (The
    # render model does the same thing, by negating each vertex's x.)
    face = mirror(sk.sketch, about=Plane.YZ)
    bb = face.bounding_box()
    face = scale(face, by=(w / bb.size.X, 1.0, h / bb.size.Z))
    bb = face.bounding_box()
    face = Pos(cx - bb.center().X, 0, (z_top - h / 2) - bb.center().Z) * face
    return _raise(face, p.let_relief, p.relief_draft_deg)


def _keying(p: FlushBracketParams, lay: _Layout):
    """Rear plate, keying bar and anchor block -- the parts cast into concrete."""
    rear = Pos(
        0,
        (lay.y_near_back + lay.y_rear_back) / 2,
        (lay.rear_z_bot + p.h) / 2,
    ) * Box(p.w, p.rear_d, p.rear_h)

    bar_len = p.bar_depth
    bar = Pos(0, lay.y_rear_back - bar_len / 2, lay.bar_z_mid) * Rot(90, 0, 0) * (
        Cylinder(lay.bar_r, bar_len)
    )
    anchor = Pos(
        0, lay.bar_y_back - p.anchor_depth / 2, lay.bar_z_mid
    ) * Rot(90, 0, 0) * Cylinder(lay.anchor_r, p.anchor_depth)
    return rear, bar, anchor


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
def build_flush_bracket(
    p: FlushBracketParams = FB,
    *,
    keying: bool = True,
    lettering: bool = True,
    number: str | None = None,
    style: BracketStyle | None = None,
):
    """Build the bracket as a single solid.

    ``keying`` includes the rear plate, bar and anchor (the full casting).
    ``lettering`` adds the raised legend and the broad arrow.

    ``number`` is the bracket's number, e.g. "S1852". It selects the lettering
    style -- which controls the face, its weight and size, and whether the
    legend reads ``B M`` or the BsM series' ``B S M``. Pass ``style`` to
    override that choice. The number itself is not yet cast onto the plate.
    """
    style = style or (resolve_style(number) if number else DEFAULT_STYLE)
    lay = _Layout(p, style)

    # The plate body. With the keying structure it is the thin front plate,
    # backed by the part-height rear plate. Without it, the body is a full
    # slab of the same TOTAL depth with a flat back -- not merely the front
    # plate on its own, which at 6.97 mm is thinner than the 12.1 mm keyhole
    # slots and would let them perforate the back of a wall-hung replica.
    body_d = p.near_d if keying else p.total_plate_d
    part = Pos(0, -body_d / 2, p.h / 2) * Box(p.w, body_d, p.h)

    if keying:
        rear, bar, anchor = _keying(p, lay)
        part += rear
        part += bar
        part += anchor

    # Cut the openings BEFORE adding anything raised.
    for sign in (1, -1):
        part -= _keyhole_cutter(p, lay, sign * lay.kh_cx)
    part -= _slot_cutter(p, lay)

    # Now the raised work.
    for sign in (1, -1):
        part += _bridging_rib(p, lay, sign * lay.kh_cx)
    part += _beading(p)
    if lettering:
        part += _broad_arrow(p, lay)
        for glyph, cx, w, h, z_top in lay.letters:
            part += _letter(p, style, glyph, cx, w, h, z_top)

    # Fillet the bar's two junctions the way the casting's own radii run.
    if keying and lay.bar_fillet > 0:
        edges = [
            e
            for e in part.edges().filter_by(GeomType.CIRCLE)
            if abs(e.radius - lay.bar_r) < 1e-6
        ]
        if edges:
            part = fillet(edges, lay.bar_fillet)

    return part


def letter_draft_ratios(p: FlushBracketParams = FB,
                        style: BracketStyle | None = None) -> dict[str, float]:
    """Top-face area / base-face area for each raised letter.

    A single draft *angle* is the physically meaningful parameter -- that is
    what lets a pattern leave the sand -- but the area ratio is what is
    actually visible on a bracket, and it varies per glyph because it depends
    on stroke width. This reports the ratio the current angle produces so it
    can be checked against a real casting.
    """
    style = style or DEFAULT_STYLE
    lay = _Layout(p, style)
    out: dict[str, float] = {}
    seen: dict[str, int] = {}
    for glyph, cx, w, h, z_top in lay.letters:
        seen[glyph] = seen.get(glyph, 0) + 1
        key = glyph if seen[glyph] == 1 else f"{glyph}{seen[glyph]}"
        solid = _letter(p, style, glyph, cx, w, h, z_top)
        bb = solid.bounding_box()
        # The base is the bottom of the prismatic stub, which carries exactly
        # the nominal footprint: the drafted part starts at the plate face.
        top = sum(f.area for f in solid.faces()
                  if abs(f.center().Y - bb.max.Y) < 1e-6)
        base = sum(f.area for f in solid.faces()
                   if abs(f.center().Y - bb.min.Y) < 1e-6)
        out[key] = top / base if base else float("nan")
    return out


if __name__ == "__main__":
    part = build_flush_bracket()
    bb = part.bounding_box()
    print(f"volume = {part.volume:.0f} mm^3")
    print(
        f"bbox   = {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm "
        f"(x {bb.min.X:.2f}..{bb.max.X:.2f}, "
        f"y {bb.min.Y:.2f}..{bb.max.Y:.2f}, "
        f"z {bb.min.Z:.2f}..{bb.max.Z:.2f})"
    )
    print(f"solids = {len(part.solids())}")
