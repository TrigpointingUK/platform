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
    BuildLine,
    BuildSketch,
    CenterArc,
    Face,
    Locations,
    Plane,
    Pos,
    Rectangle,
    Text,
    extrude,
)
from ocpsvg import ColorAndLabel, import_svg_document
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopoDS import TopoDS_Face

# Cutters/adders start this far above the surface so the boolean is clean.
_OVERSHOOT = 0.4  # mm


# ================================================================== arc text

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
):
    """A downward-extruded cutter solid for one arc of engraved text.

    The arc is traversed clockwise (negative ``arc_size``) so the text reads
    clockwise from above with letter-tops facing outward.
    """
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
