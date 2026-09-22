"""Raising a flat outline off the plate with casting draft.

The sides of a cast letter are not vertical. A sand-casting pattern has to
leave its mould, so every raised face leans inward, and on a flush bracket the
lean is pronounced -- the top of a letter is roughly half the area of its base.
Modelling it is most of what makes a print read as *cast* rather than milled.

Why this is done by hand rather than with ``extrude(taper=...)``
---------------------------------------------------------------
OCCT's draft and 2-D offset operations are built on ``BRepOffsetAPI`` and are
unreliable on glyph outlines: of ``O S B M`` in a plain grotesque, ``S`` and
``B`` fail outright, ``M`` fails once squeezed to its measured box, and
asymmetric chamfer fails on all three. Font outlines are spline-heavy with
near-tangent joins and sharp reflex corners, which is precisely the case that
offsetting handles worst.

So the offset is computed on a raster instead. A uniform inward offset is
exactly a threshold on the distance transform, which cannot fail, cannot
self-intersect, and handles counters (the holes in O, B, 8) in the same step --
as material leans inward going up, a counter *grows*, and eroding the mask does
that automatically.

That also puts this on the same footing as the glyph library: outlines derived
from photographs (see ``cad/fbfit``) arrive as raster masks, and will come
through this same path rather than needing a second implementation.
"""

from __future__ import annotations

import math

import cv2
import numpy as np
from build123d import Face, Vector, Wire, extrude, loft

#: Rasterisation resolution. At 40 px/mm a 24 mm letter is ~960 px tall and a
#: 1 mm draft offset is 40 px, so the offset is resolved to ~2.5% of itself.
PX_PER_MM = 40.0

#: Contour simplification, in mm. Small enough to be invisible at 1:1 and well
#: under the printer's resolution; large enough to keep the lofted wires to a
#: few hundred segments rather than a few thousand.
SIMPLIFY_MM = 0.04


def _wire_points(wire, px_per_mm: float) -> np.ndarray:
    """Sample a wire lying in the world XZ plane into a dense (x, z) polyline."""
    pts: list[tuple[float, float]] = []
    for edge in wire.edges():
        n = max(2, int(edge.length * px_per_mm / 2))
        for i in range(n):
            p = edge @ (i / n)
            pts.append((p.X, p.Z))
    return np.asarray(pts, dtype=np.float64)


def _rasterise(face, px_per_mm: float, pad_mm: float):
    """Burn a face (with its holes) into a binary mask; return mask + origin."""
    bb = face.bounding_box()
    x0, z0 = bb.min.X - pad_mm, bb.min.Z - pad_mm
    w = int(math.ceil((bb.size.X + 2 * pad_mm) * px_per_mm))
    h = int(math.ceil((bb.size.Z + 2 * pad_mm) * px_per_mm))
    mask = np.zeros((h, w), np.uint8)

    def to_px(pts: np.ndarray) -> np.ndarray:
        cols = (pts[:, 0] - x0) * px_per_mm
        rows = (pts[:, 1] - z0) * px_per_mm
        return np.stack([cols, rows], axis=1).round().astype(np.int32)

    cv2.fillPoly(mask, [to_px(_wire_points(face.outer_wire(), px_per_mm))], 255)
    for inner in face.inner_wires():
        cv2.fillPoly(mask, [to_px(_wire_points(inner, px_per_mm))], 0)
    return mask, (x0, z0)


def _contours_mm(mask: np.ndarray, origin, px_per_mm: float):
    """Trace a mask back to (outer, [holes]) polygons in millimetres."""
    cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None or not len(cnts):
        return None, []
    hier = hier[0]
    eps = SIMPLIFY_MM * px_per_mm
    x0, z0 = origin
    outers, holes = [], []
    for c, h in zip(cnts, hier):
        if cv2.contourArea(c) < (0.2 * px_per_mm) ** 2:
            continue
        ap = cv2.approxPolyDP(c, eps, True).reshape(-1, 2).astype(np.float64)
        poly = np.stack([ap[:, 0] / px_per_mm + x0, ap[:, 1] / px_per_mm + z0], 1)
        if len(poly) < 3:
            continue
        (holes if h[3] >= 0 else outers).append(poly)
    outers.sort(key=lambda p: -cv2.contourArea(p.astype(np.float32)))
    return (outers[0] if outers else None), holes


def _centroid(poly: np.ndarray) -> np.ndarray:
    return poly.mean(axis=0)


#: Vertices per lofted section. Both sections are resampled to this count so
#: the ruled loft has a clean one-to-one correspondence between them. Leaving
#: the traced vertex counts to differ makes OCCT's ThruSections fail outright
#: on acute-cornered glyphs -- M, 2, 5 and 7 all did.
LOFT_POINTS = 240


def _signed_area(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def _resample(poly: np.ndarray, n: int) -> np.ndarray:
    """Re-point a closed polygon to ``n`` vertices, evenly by arc length.

    Also normalises winding and start vertex, so that two sections of the same
    glyph -- traced independently at base and top -- correspond point for
    point rather than merely describing the same outline.
    """
    if _signed_area(poly) < 0:
        poly = poly[::-1]
    c = poly.mean(axis=0)
    ang = np.arctan2(poly[:, 1] - c[1], poly[:, 0] - c[0])
    poly = np.roll(poly, -int(np.argmin(np.abs(ang))), axis=0)

    closed = np.vstack([poly, poly[:1]])
    seg = np.hypot(*np.diff(closed, axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    if cum[-1] <= 0:
        raise ValueError("degenerate contour")
    want = np.linspace(0.0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(want, cum, closed[:, 0]),
                     np.interp(want, cum, closed[:, 1])], axis=1)


def _face_at(poly: np.ndarray, y: float) -> Face:
    """A planar face from an (x, z) polygon, standing at world y.

    ``loft`` takes faces rather than wires, so the section is built as one.
    """
    wire = Wire.make_polygon(
        [Vector(float(x), y, float(z)) for x, z in poly], close=True)
    return Face(wire)


def _loft_pair(base: np.ndarray, top: np.ndarray, y0: float, y1: float):
    base = _resample(base, LOFT_POINTS)
    top = _resample(top, LOFT_POINTS)
    return loft([_face_at(base, y0), _face_at(top, y1)], ruled=True)


def drafted(face, relief: float, draft_deg: float, embed: float = 0.0,
            px_per_mm: float = PX_PER_MM):
    """Raise ``face`` (in the world XZ plane) to ``relief`` mm with draft.

    The outline passed in is the footprint at the plate face, y = 0 -- the
    widest section, which is what the measured letter boxes describe. The
    optional ``embed`` stub below y = 0 is prismatic on purpose: drafting it
    would pull the footprint in.
    """
    if draft_deg <= 0:
        solid = extrude(face, amount=-relief)
        return solid + extrude(face, amount=embed) if embed else solid

    d = relief * math.tan(math.radians(draft_deg))
    solids = []
    for f in face.faces():
        mask, origin = _rasterise(f, px_per_mm, pad_mm=d + 1.0)
        dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        top_mask = (dist > d * px_per_mm).astype(np.uint8) * 255

        b_out, b_holes = _contours_mm(mask, origin, px_per_mm)
        t_out, t_holes = _contours_mm(top_mask, origin, px_per_mm)
        if b_out is None or t_out is None:
            raise ValueError(
                f"draft of {draft_deg} deg consumes this glyph entirely; "
                f"its strokes are narrower than {2 * d:.2f} mm")
        if len(b_holes) != len(t_holes):
            raise ValueError(
                f"draft of {draft_deg} deg closes a counter "
                f"({len(b_holes)} holes at the base, {len(t_holes)} at the top)")

        solid = _loft_pair(b_out, t_out, 0.0, relief)
        # Counters grow with height -- eroding the mask has already done that,
        # so each hole pairs base-to-top the same way the outline does.
        for bh in b_holes:
            th = min(t_holes, key=lambda p: np.hypot(*(_centroid(p) - _centroid(bh))))
            solid -= _loft_pair(bh, th, -0.001, relief + 0.001)
        if embed:
            solid += extrude(f, amount=embed)
        solids.append(solid)

    out = solids[0]
    for s in solids[1:]:
        out += s
    return out
