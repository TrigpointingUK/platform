"""Ordnance Survey bracket numerals, drawn rather than borrowed from a font.

No digital typeface has these letterforms, and squeezing a grotesque into the
right bounding box does not get close. The cast numerals are **geometric**:
flat horizontal bars, straight diagonals, and circular arcs, drawn with a
stroke of near-constant width. A `3` is a flat top bar, a straight diagonal,
and an almost-complete circular bowl -- not the two-curves-and-a-cusp shape
every text face gives you.

So each glyph is defined here as a **skeleton**: a centreline of lines and arcs
in units of cap height, swept with a circular pen. That is what a punch cutter
was doing, and it means the shapes stay right when the weight or the
proportions change, rather than being outlines that only work at one size.

The pen sweep is a distance transform on a raster -- the same mechanism
``relief.py`` uses for casting draft, and for the same reason: an exact offset
of a skeleton is trivially a threshold on distance, and cannot self-intersect
however the strokes are arranged.

Coordinates: x rightward, y up from the baseline, both in cap heights, so a
glyph occupies y 0..1 and x 0..``width``. Scaling is uniform -- the stroke is a
physical punch width and does not stretch with the box.

Terminals are round by default. A ``cut`` trims one flat, which is how the OS
numerals end their curved strokes: the bowl of a 3 or a 5 stops on a vertical
face rather than tapering or rounding off.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import numpy as np

# --- the little path language ----------------------------------------------
# ("L", x0, y0, x1, y1)              straight segment
# ("A", cx, cy, r, a0, a1)           circular arc, degrees, CCW positive;
#                                    a1 < a0 sweeps clockwise


def L(x0, y0, x1, y1):
    return ("L", x0, y0, x1, y1)


def A(cx, cy, r, a0, a1):
    return ("A", cx, cy, r, a0, a1)


@dataclass(frozen=True)
class Glyph:
    """One character: its drawn width, its skeleton, and any flat terminals.

    ``width`` is the width of the **ink**, in cap heights. The skeleton is
    scaled in x to reach it, so a bowl drawn as a circle becomes an ellipse if
    the glyph is narrower than it is tall -- which is what the castings do, and
    what the measured letter boxes in ``params`` say. The pen is applied after
    that scaling, so the stroke stays an even width either way.
    """

    width: float
    strokes: tuple
    #: Flat terminal cuts, each (x, y, nx, ny): everything on the +n side of
    #: the line through (x, y) is removed.
    cuts: tuple = field(default_factory=tuple)


def _arc_points(cx, cy, r, a0, a1, per_deg=0.5):
    n = max(2, int(abs(a1 - a0) * per_deg))
    return [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
            for a in np.linspace(a0, a1, n)]


def _polylines(glyph: Glyph):
    """The skeleton as polylines, in its own arbitrary coordinates."""
    out = []
    for seg in glyph.strokes:
        if seg[0] == "L":
            out.append([(seg[1], seg[2]), (seg[3], seg[4])])
        else:
            out.append(_arc_points(*seg[1:]))
    return out


def _normaliser(lines):
    """Map a skeleton's own extents onto the unit square.

    Glyphs are drawn in whatever coordinates were convenient -- a bowl as a
    circle of some radius about some centre -- and this puts them all on the
    same footing afterwards, so a declared width really is the ink width and
    every glyph stands exactly one cap high without its skeleton having to be
    written to span 0..1 by hand.
    """
    xs = [p[0] for line in lines for p in line]
    ys = [p[1] for line in lines for p in line]
    x0, y0 = min(xs), min(ys)
    dx, dy = max(xs) - x0, max(ys) - y0
    return lambda p: (((p[0] - x0) / dx if dx > 1e-9 else 0.5),
                      ((p[1] - y0) / dy if dy > 1e-9 else 0.5))


def glyph_mask(glyph: Glyph, cap_mm: float, stroke_mm: float,
               px_per_mm: float, pad_mm: float = 1.0):
    """Render one glyph to a binary mask; return (mask, origin_mm).

    ``cap_mm`` is the height of the **ink**, and ``glyph.width`` x ``cap_mm``
    its width -- so the skeleton is inset by half a stroke all round before the
    pen is applied, rather than the pen spilling outside the declared box.

    ``origin_mm`` is the (x, y) of the mask's lower-left corner in glyph
    millimetres, so the caller can place the traced outline.
    """
    ink_w, ink_h = glyph.width * cap_mm, cap_mm
    x0, y0 = -pad_mm, -pad_mm
    W = int(math.ceil((ink_w + 2 * pad_mm) * px_per_mm))
    H = int(math.ceil((ink_h + 2 * pad_mm) * px_per_mm))

    lines = _polylines(glyph)
    norm = _normaliser(lines)
    span_x, span_y = ink_w - stroke_mm, ink_h - stroke_mm

    def to_px(p):
        nx, ny = norm(p)
        xm = stroke_mm / 2 + nx * span_x
        ym = stroke_mm / 2 + ny * span_y
        # Row increases with y, matching relief.py's rasters. That makes the
        # mask upside down when viewed as an image, and round-trips correctly
        # through _contours_mm, which inverts the same way.
        return (int(round((xm - x0) * px_per_mm)),
                int(round((ym - y0) * px_per_mm)))

    skel = np.zeros((H, W), np.uint8)
    for line in lines:
        pts = np.array([to_px(p) for p in line], np.int32)
        cv2.polylines(skel, [pts], False, 255, 1, cv2.LINE_8)

    # Sweep the pen: an exact offset of the skeleton is a distance threshold.
    dist = cv2.distanceTransform(255 - skel, cv2.DIST_L2, 5)
    mask = (dist <= (stroke_mm / 2) * px_per_mm).astype(np.uint8) * 255

    # Flat terminals. The cut is deliberately LOCAL -- a band a couple of
    # stroke widths long centred on the terminal -- not a half-plane across
    # the whole glyph. A half-plane trimmed the 3's bowl correctly and then
    # took the 5's stem off with it, since the stem lies further left.
    reach = int(round(1.4 * stroke_mm * px_per_mm))
    for cx, cy, nx, ny in glyph.cuts:
        px, py = to_px((cx, cy))
        ny_img = ny
        tx, ty = -ny_img, nx
        poly = np.array([
            [px + tx * reach, py + ty * reach],
            [px - tx * reach, py - ty * reach],
            [px - tx * reach + nx * reach, py - ty * reach + ny_img * reach],
            [px + tx * reach + nx * reach, py + ty * reach + ny_img * reach],
        ], np.int32)
        cv2.fillPoly(mask, [poly], 0)

    return mask, (x0, y0)


# --- the numerals -----------------------------------------------------------
# Drawn from photographs of real brackets. Bowls are circles, joins are
# straight, and the flat top bars really are flat.

# Ink widths, in cap heights. The digits are nearly square on a BsM bracket;
# the legend letters take the aspect of their measured boxes in params.py
# (os_w/os_h and so on), so those measurements check these rather than being
# applied as a squeeze.
FULL_WIDTH = 0.87  # ink width of a full-width digit, in cap heights
_W = FULL_WIDTH
_BOWL_R = 0.285    # radius of the lower bowl shared by 3, 5, 6, 8, 9
_BOWL_Y = 0.285

GLYPHS: dict[str, Glyph] = {
    # Flat top bar, straight diagonal down to the middle, then a bowl that
    # wraps almost the whole way round and stops on a vertical face.
    "3": Glyph(_W, (
        L(0.07, 1.0, 0.70, 1.0),
        L(0.70, 1.0, 0.40, 0.60),
        A(0.40, _BOWL_Y, _BOWL_R, 90, -150),
    ), ((0.40 - _BOWL_R * math.cos(math.radians(30)), 0.0, -1.0, 0.0),)),

    # Flat top bar, vertical stem down the left, then the same bowl.
    "5": Glyph(_W, (
        L(0.10, 1.0, 0.70, 1.0),
        L(0.10, 1.0, 0.10, 0.62),
        L(0.10, 0.62, 0.30, 0.57),
        A(0.40, _BOWL_Y, _BOWL_R, 110, -150),
    ), ((0.40 - _BOWL_R * math.cos(math.radians(30)), 0.0, -1.0, 0.0),)),

    "0": Glyph(_W, (A(0.37, 0.5, 0.33, -90, 270),)),

    # A bare stem with a short flag, and no foot.
    "1": Glyph(0.22, (
        L(0.28, 1.0, 0.28, 0.0),
        L(0.28, 1.0, 0.07, 0.83),
    )),

    # Bowl over the top, straight diagonal down, flat foot.
    "2": Glyph(_W, (
        A(0.38, 0.72, 0.28, 180, -20),
        L(0.63, 0.63, 0.08, 0.0),
        L(0.08, 0.0, 0.71, 0.0),
    )),

    # Diagonal down to a flat crossbar, with the stem through it.
    "4": Glyph(_W, (
        L(0.52, 1.0, 0.05, 0.30),
        L(0.05, 0.30, 0.71, 0.30),
        L(0.52, 1.0, 0.52, 0.0),
    )),

    # Straight diagonal entry running tangentially into a full circular bowl.
    "6": Glyph(_W, (
        L(0.62, 0.97, 0.12, 0.45),
        A(0.38, 0.30, 0.30, 90, 450),
    )),

    # Flat top bar and a straight diagonal. No crossbar, no foot.
    "7": Glyph(_W, (
        L(0.05, 1.0, 0.71, 1.0),
        L(0.71, 1.0, 0.26, 0.0),
    )),

    "8": Glyph(_W, (
        A(0.38, 0.735, 0.245, -90, 270),
        A(0.38, _BOWL_Y, _BOWL_R, 90, 450),
    )),

    # The 6 turned about: a full bowl at the top, straight tail from its
    # right side down to the baseline.
    "9": Glyph(_W, (
        A(0.38, 0.70, 0.28, 90, 450),
        L(0.64, 0.55, 0.14, 0.03),
    )),

    # --- the legend letters ------------------------------------------------
    "O": Glyph(0.667, (A(0.40, 0.5, 0.35, -90, 270),)),

    # Two arcs whose ends come close enough for the pen to bridge the waist.
    # Get the sweeps the wrong way round and they finish 0.43 cap heights
    # apart, which no pen will close -- the S comes out as two detached C's.
    "S": Glyph(0.667, (
        A(0.38, 0.70, 0.27, 20, 215),
        A(0.38, 0.30, 0.27, 125, -165),
    )),

    "B": Glyph(0.671, (
        L(0.08, 0.0, 0.08, 1.0),
        L(0.08, 1.0, 0.40, 1.0),
        A(0.40, 0.75, 0.25, 90, -90),
        L(0.40, 0.50, 0.08, 0.50),
        L(0.08, 0.50, 0.44, 0.50),
        A(0.44, 0.25, 0.25, 90, -90),
        L(0.44, 0.0, 0.08, 0.0),
    )),

    "M": Glyph(0.718, (
        L(0.07, 0.0, 0.07, 1.0),
        L(0.07, 1.0, 0.46, 0.30),
        L(0.46, 0.30, 0.85, 1.0),
        L(0.85, 1.0, 0.85, 0.0),
    )),
}


#: Resolution the glyph rasters are built at. 0.05 mm is finer than any
#: printer resolves, and coarse enough to keep the lofts quick.
PX_PER_MM = 20.0


def has(ch: str) -> bool:
    return ch in GLYPHS
