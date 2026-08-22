"""Generic surface-engraving mechanisms, shared across models.

These are the *config-free* techniques extracted from the plug's ``lettering``
and ``top_surfaces`` modules so any model (e.g. the driver tool) can reuse them:

* :func:`arc_text_cutter` / :func:`engrave_arc_texts` -- text laid along a
  circular arc, extruded downward into a cutter and subtracted.
* :func:`svg_relief` -- a multi-level relief from a colour-mapped SVG, engraved
  (recessed) or embossed (raised). The colour -> depth-fraction table is a
  *passed-in* ``frac_map`` so this stays model-agnostic.
* :func:`qr_cutter` -- a QR code (generated in-process by segno) engraved as
  recessed modules.

Each engraving starts its cutter/adder slightly above the target face
(``overshoot``) so the boolean is clean. Geometry is identical to the original
plug implementation; only the configuration is now parameterised.
"""

from __future__ import annotations

import math
from typing import Iterable

import segno
from build123d import (
    Align,
    BuildLine,
    BuildSketch,
    CenterArc,
    Face,
    Locations,
    Plane,
    Pos,
    Rectangle,
    Rot,
    Text,
    extrude,
)
from ocpsvg import ColorAndLabel, import_svg_document
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopoDS import TopoDS_Face

# Cutters/adders start this far above the surface so the boolean is clean.
_OVERSHOOT = 0.4  # mm


# ================================================================== arc text

def cap_height_font_size(font: str, cap_height: float) -> float:
    """``font_size`` that renders capitals ``cap_height`` mm tall.

    ``Text``'s ``font_size`` is the em size, not the cap height -- for most
    faces caps are only ~0.7 em, so asking for 7 mm gets letters barely 5 mm
    tall. Measure the face rather than assume the ratio.
    """
    cap = Text("H", font_size=10.0, font=font, align=(Align.CENTER, Align.MIN))
    bb = cap.bounding_box()
    return cap_height * 10.0 / (bb.max.Y - bb.min.Y)


def _glyph_items(txt, *, font, font_size, word_space):
    """``[(glyph_sketch | None, width), ...]`` -- ``None`` marks a word space."""
    items = []
    for ch in txt:
        if ch == " ":
            items.append((None, word_space))
        else:
            g = Text(ch, font_size=font_size, font=font,
                     align=(Align.CENTER, Align.MIN))
            bb = g.bounding_box()
            items.append((g, bb.max.X - bb.min.X))
    return items


def fit_letter_gap(txt, *, span_deg, radius, font, font_size, word_space) -> float:
    """The constant letter gap that makes ``txt`` exactly fill ``span_deg``.

    Negative means the phrase cannot be made to fit without the glyphs
    overlapping -- the caller should treat that as a design error.
    """
    items = _glyph_items(txt, font=font, font_size=font_size, word_space=word_space)
    ink = sum(w for _, w in items)
    return (math.radians(span_deg) * radius - ink) / (len(items) - 1)


def _laid_out_glyphs(txt, *, centre_deg, radius, font, font_size,
                     letter_gap, word_space):
    """Place each glyph individually along the arc on a constant gap.

    ``Text(path=...)`` lays text out on the font's own metrics, which for the
    plug's phrases overruns the space between the spider-screw holes once the
    letters are the height the original casts them. The original solves this the
    way the caster did -- keep the letters full height and jam them together --
    so glyphs are positioned here on a constant *ink* gap. That also reproduces
    the original's kerning, which is not so much bad as absent: every pair is
    spaced identically regardless of shape, so "AT" gapes and "II" crowds.
    """
    items = _glyph_items(txt, font=font, font_size=font_size, word_space=word_space)
    total = sum(w for _, w in items) + letter_gap * (len(items) - 1)
    placed, s = None, 0.0
    for glyph, w in items:
        if glyph is not None:
            # Clockwise from above (decreasing angle), letter-tops outward.
            ang = centre_deg + math.degrees((total / 2 - (s + w / 2)) / radius)
            here = Rot(0, 0, ang - 90) * Pos(0, radius, 0) * glyph
            placed = here if placed is None else placed + here
        s += w + letter_gap
    return placed


def arc_text_cutter(
    txt: str,
    *,
    centre_deg: float,
    span_deg: float,
    z_top: float,
    radius: float,
    font: str,
    font_size: float,
    depth: float,
    overshoot: float = _OVERSHOOT,
    letter_gap: float | None = None,
    word_space: float | None = None,
):
    """A downward-extruded cutter solid for one arc of engraved text.

    The arc is traversed clockwise (negative ``arc_size``) so the text reads
    clockwise from above with letter-tops facing outward.

    With ``letter_gap`` given, glyphs are placed individually on that constant
    ink gap instead of using the font's own metrics -- see
    :func:`_laid_out_glyphs`. ``span_deg`` is then only the centring reference.
    """
    if letter_gap is not None:
        placed = _laid_out_glyphs(
            txt, centre_deg=centre_deg, radius=radius, font=font,
            font_size=font_size, letter_gap=letter_gap,
            word_space=word_space if word_space is not None else font_size * 0.25,
        )
        return extrude(Pos(0, 0, z_top + overshoot) * placed,
                       amount=-(depth + overshoot))
    with BuildSketch(Plane.XY.offset(z_top + overshoot)) as sk:
        with BuildLine():
            arc = CenterArc(
                (0, 0),
                radius,
                start_angle=centre_deg + span_deg / 2,
                arc_size=-span_deg,
            )
        Text(
            txt,
            font_size=font_size,
            font=font,
            path=arc.edges()[0],
            position_on_path=0.5,  # centre the phrase on the arc midpoint
        )
    return extrude(sk.sketch, amount=-(depth + overshoot))


def engrave_arc_texts(
    part,
    texts: Iterable[tuple[str, float, float]],
    *,
    z_top: float,
    radius: float,
    font: str,
    font_size: float,
    depth: float,
    overshoot: float = _OVERSHOOT,
    letter_gap: float | None = None,
    word_space: float | None = None,
):
    """Subtract each ``(text, centre_deg, span_deg)`` arc from ``part`` at
    height ``z_top``. Returns the engraved part."""
    for txt, centre_deg, span_deg in texts:
        part = part - arc_text_cutter(
            txt,
            centre_deg=centre_deg,
            span_deg=span_deg,
            z_top=z_top,
            radius=radius,
            font=font,
            font_size=font_size,
            depth=depth,
            overshoot=overshoot,
            letter_gap=letter_gap,
            word_space=word_space,
        )
    return part


# ================================================================ SVG relief

def _nearest_frac(rgb: tuple[int, int, int], frac_map: dict) -> float:
    """Relief fraction of the nearest known colour in ``frac_map`` (Euclidean
    in RGB)."""
    best_d, best_f = 1e18, 0.0
    for colour, frac in frac_map.items():
        d = sum((a - b) ** 2 for a, b in zip(rgb, colour))
        if d < best_d:
            best_d, best_f = d, frac
    return best_f


def svg_relief(
    part,
    *,
    z_top,
    radius,
    frac_map: dict[tuple[int, int, int], float],
    svg_path,
    amount,
    fill=0.85,
    raised=False,
    overshoot: float = _OVERSHOOT,
    clearance=0.0,
):
    """Render a colour-mapped SVG as a multi-level relief on the top face.

    Each fill colour is offset by ``amount * frac_map[colour]`` (nearest match),
    so the deepest/tallest fractions dominate where layers overlap; a fraction
    of ``0`` (e.g. an outline colour) is skipped. The artwork is scaled so its
    bounding circle fits within ``fill`` of ``radius`` and centred.

    ``raised=False`` engraves the relief into the surface (recessed);
    ``raised=True`` embosses it proud. Each boolean is volume-checked and
    validated, so a degenerate SVG face (which would invalidate the solid) is
    skipped rather than shipped.
    """
    groups: dict[float, list[Face]] = {}
    xs: list[float] = []
    ys: list[float] = []
    for shape, meta in import_svg_document(str(svg_path), metadata=ColorAndLabel):
        if not isinstance(shape, TopoDS_Face):
            continue
        fc = meta.fill_color
        rgb = (round(fc[0] * 255), round(fc[1] * 255), round(fc[2] * 255))
        frac = _nearest_frac(rgb, frac_map)
        if frac <= 0:
            continue
        face = Face(shape)
        groups.setdefault(round(frac, 3), []).append(face)
        bb = face.bounding_box()
        xs += [bb.min.X, bb.max.X]
        ys += [bb.min.Y, bb.max.Y]
    if not groups:
        return part

    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    # Scale so the artwork's bounding circle fits within `fill` of the disc.
    scale = radius * fill / (0.5 * math.hypot(w, h))

    # Deepest/tallest first, so overlapping layers resolve to the extreme. Each
    # step is validated: a few SVG paths (near-white highlights) yield
    # degenerate faces that invalidate the solid; those are skipped, not shipped.
    for frac in sorted(groups, reverse=True):
        h = amount * frac
        for face in groups[frac]:
            # Face.scale is about the origin, so scale first then translate the
            # scaled centre to the axis.
            placed = Pos(-cx * scale, -cy * scale, 0) * face.scale(scale)
            if raised:
                # Proud of the surface: extrude up from just below it, union.
                solid = extrude(Pos(0, 0, z_top - overshoot) * placed,
                                amount=h + overshoot)
                trial = part + solid
                grew = trial.volume >= part.volume - 1e-6  # union must not shrink
            else:
                # Recessed: extrude down from just above the surface, subtract.
                solid = extrude(Pos(0, 0, z_top + overshoot) * placed,
                                amount=-(h + overshoot))
                trial = part - solid
                grew = trial.volume <= part.volume + 1e-6  # cut must not grow
            # Accept only a valid, sane result; a failed boolean (e.g. one that
            # returns just the addition) is rejected so the body survives.
            if grew and BRepCheck_Analyzer(trial.wrapped).IsValid():
                part = trial
    return part


# ======================================================================= QR

def qr_cutter(
    part,
    *,
    z_top,
    radius,
    url,
    depth=0.5,
    error="m",
    border=2,
    fill=0.85,
    overshoot: float = _OVERSHOOT,
):
    """Engrave a QR code (generated in-process by segno) pointing at ``url``.

    Dark modules are recessed by ``depth``. The code square is scaled to fit
    within ``fill`` of the disc (inscribed in the circle) with a ``border``
    quiet zone of flat modules. ``error`` is the segno error-correction level
    ('l'/'m'/'q'/'h').

    Note: an *engraved* (recessed) QR reads by shadow/contrast, which depends on
    the print finish and lighting -- it is not guaranteed to scan on bare metal.
    """
    matrix = [[bool(c) for c in row] for row in segno.make(url, error=error).matrix]
    n = len(matrix)
    total = n + 2 * border
    # Largest square inscribed in the (fill-scaled) disc.
    side = 2 * radius * fill / math.sqrt(2)
    module = side / total
    x0 = -side / 2 + border * module  # left edge of the module grid
    y0 = side / 2 - border * module   # top edge of the module grid

    with BuildSketch(Pos(0, 0, z_top + overshoot)) as sk:
        locs = []
        for i, row in enumerate(matrix):
            for j, dark in enumerate(row):
                if dark:
                    locs.append((x0 + (j + 0.5) * module, y0 - (i + 0.5) * module))
        with Locations(*locs):
            Rectangle(module, module)
    cutter = extrude(sk.sketch, amount=-(depth + overshoot))
    return part - cutter
