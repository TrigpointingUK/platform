"""Customisable engraved treatments for the inner plug's top face.

The inner plug's top is the one exposed, visible surface, so it is a natural
place to personalise. This module is a small **library** of "surface
treatments" plus named **presets**, selected in code when building the inner
plug (see ``build_inner_plug(..., top=...)`` and ``build.INNER_TOPS``).

Design
------
* A treatment TYPE is a function ``(part, *, z_top, radius, clearance, **opts)
  -> part`` that engraves the top face (z = ``z_top``, usable flat radius =
  ``radius``) and returns the modified part. Types live in ``TREATMENTS``.
* A ``TopSurface`` PRESET binds a treatment type to concrete options (a QR URL,
  a logo SVG, engraving depths) and a short ``label`` used in output filenames.
  Presets live in ``PRESETS``.

Adding an option is therefore: write a treatment function, register it in
``TREATMENTS``, and add a ``TopSurface`` to ``PRESETS``.

Both example engravings reuse the same "offset sketch above the face, extrude
downward, boolean-subtract" pattern as ``lettering.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import segno
from build123d import (
    BuildSketch,
    Face,
    Locations,
    Pos,
    Rectangle,
    extrude,
)
from ocpsvg import ColorAndLabel, import_svg_document
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.TopoDS import TopoDS_Face

# Cutter starts this far above the surface so the boolean cut is clean.
_OVERSHOOT = 0.4  # mm
REPO_ROOT = Path(__file__).resolve().parent.parent
LOGO_SVG = REPO_ROOT / "res" / "TUK-Logo.svg"


# ============================================================ treatment types

def engrave_flat(part, **_):
    """No treatment -- the original flat top (matches the real inner plug)."""
    return part


# TrigpointingUK logo fill colour (RGB 0-255) -> relief fraction, ported from
# the Blender model (Blender/Hotine/trig_pillar.py: build_flush_bracket_logo).
# There the fraction was proud relief height; here it is engraving depth, so the
# form is the same layering recessed into the surface. Black outline is skipped.
_LOGO_FRAC = {
    (99, 231, 16): 1.00,    # bright green (UK map) -- deepest
    (89, 157, 43): 0.60,    # dark green (grass)
    (147, 147, 147): 0.35,  # grey (trig / theodolite)
    (254, 232, 42): 0.35,   # yellow (benchmark arrow)
    (242, 242, 242): 0.20,  # near-white highlight
    (230, 230, 230): 0.20,  # light-grey highlight
    (0, 0, 0): 0.00,        # black outline -- skipped
}


def _nearest_frac(rgb: tuple[int, int, int]) -> float:
    """Relief fraction of the nearest known logo colour (Euclidean in RGB)."""
    best_d, best_f = 1e18, 0.0
    for colour, frac in _LOGO_FRAC.items():
        d = sum((a - b) ** 2 for a, b in zip(rgb, colour))
        if d < best_d:
            best_d, best_f = d, frac
    return best_f


def logo_relief(part, *, z_top, radius, clearance=0.0,
                svg_path=LOGO_SVG, amount=0.9, fill=0.85, raised=False):
    """Render the multi-colour TrigpointingUK logo as a multi-level relief.

    Each fill colour is offset by ``amount * fraction`` using the Blender relief
    table, so greens sit deepest/tallest and highlights shallowest; the black
    outline is skipped. The whole logo is scaled to ``fill`` of the top-face
    radius and centred. ``svg_path`` defaults to the repo's ``res/TUK-Logo.svg``.

    ``raised=False`` engraves the relief into the surface (recessed); ``raised=
    True`` embosses it proud of the surface.
    """
    groups: dict[float, list[Face]] = {}
    xs: list[float] = []
    ys: list[float] = []
    for shape, meta in import_svg_document(str(svg_path), metadata=ColorAndLabel):
        if not isinstance(shape, TopoDS_Face):
            continue
        fc = meta.fill_color
        rgb = (round(fc[0] * 255), round(fc[1] * 255), round(fc[2] * 255))
        frac = _nearest_frac(rgb)
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
    # Scale so the logo's bounding circle fits within `fill` of the disc.
    scale = radius * fill / (0.5 * math.hypot(w, h))

    # Deepest/tallest first, so overlapping layers resolve to the extreme. Each
    # step is validated: a few SVG paths (the near-white highlights) yield
    # degenerate faces that invalidate the solid; those are skipped, not shipped.
    for frac in sorted(groups, reverse=True):
        h = amount * frac
        for face in groups[frac]:
            # Face.scale is about the origin, so scale first then translate the
            # scaled centre to the axis.
            placed = Pos(-cx * scale, -cy * scale, 0) * face.scale(scale)
            if raised:
                # Proud of the surface: extrude up from just below it, union.
                solid = extrude(Pos(0, 0, z_top - _OVERSHOOT) * placed,
                                amount=h + _OVERSHOOT)
                trial = part + solid
                grew = trial.volume >= part.volume - 1e-6  # union must not shrink
            else:
                # Recessed: extrude down from just above the surface, subtract.
                solid = extrude(Pos(0, 0, z_top + _OVERSHOOT) * placed,
                                amount=-(h + _OVERSHOOT))
                trial = part - solid
                grew = trial.volume <= part.volume + 1e-6  # cut must not grow
            # Accept only a valid, sane result; a failed boolean (e.g. one that
            # returns just the addition) is rejected so the body survives.
            if grew and BRepCheck_Analyzer(trial.wrapped).IsValid():
                part = trial
    return part


def engrave_qr(part, *, z_top, radius, clearance=0.0,
               url, depth=0.5, error="m", border=2, fill=0.85):
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

    with BuildSketch(Pos(0, 0, z_top + _OVERSHOOT)) as sk:
        locs = []
        for i, row in enumerate(matrix):
            for j, dark in enumerate(row):
                if dark:
                    locs.append((x0 + (j + 0.5) * module, y0 - (i + 0.5) * module))
        with Locations(*locs):
            Rectangle(module, module)
    cutter = extrude(sk.sketch, amount=-(depth + _OVERSHOOT))
    return part - cutter


TREATMENTS: dict[str, Callable] = {
    "flat": engrave_flat,
    "logo": logo_relief,
    "qr": engrave_qr,
}


# ================================================================== presets

@dataclass(frozen=True)
class TopSurface:
    """A named, configured top-surface treatment."""

    treatment: str            # key into TREATMENTS
    label: str                # short slug used in output filenames
    opts: dict = field(default_factory=dict)

    def apply(self, part, *, z_top, radius, clearance=0.0):
        return TREATMENTS[self.treatment](
            part, z_top=z_top, radius=radius, clearance=clearance, **self.opts
        )


DEFAULT = "flat"

PRESETS: dict[str, TopSurface] = {
    "flat": TopSurface("flat", "flat"),
    "tuk-logo": TopSurface(
        "logo", "tuk-logo", {"svg_path": str(LOGO_SVG), "amount": 0.9}
    ),
    "tuk-logo-emboss": TopSurface(
        "logo", "tuk-logo-emboss",
        {"svg_path": str(LOGO_SVG), "amount": 0.9, "raised": True},
    ),
    "trig-5169-qr": TopSurface(
        "qr", "trig-5169-qr",
        {"url": "https://trigpointing.uk/trigs/5169", "depth": 0.5},
    ),
}


def resolve(top) -> TopSurface:
    """Accept a preset name or a TopSurface and return a TopSurface."""
    return PRESETS[top] if isinstance(top, str) else top
