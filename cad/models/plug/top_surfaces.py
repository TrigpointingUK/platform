"""Customisable engraved treatments for the inner plug's top face.

The inner plug's top is the one exposed, visible surface, so it is a natural
place to personalise. This module is a small **library** of "surface
treatments" plus named **presets**, selected in code when building the inner
plug (see ``build_inner_plug(..., top=...)`` and the plug build's
``INNER_TOPS``).

The generic engraving *mechanisms* (SVG relief, QR) live in ``common.engraving``;
this module holds only the plug-specific configuration -- the logo colour->relief
table, the treatment registry and the named presets.

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
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from common.engraving import qr_cutter, svg_relief
from common.paths import REPO_ROOT

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


def logo_relief(part, *, z_top, radius, clearance=0.0,
                svg_path=LOGO_SVG, amount=0.9, fill=0.85, raised=False):
    """Render the multi-colour TrigpointingUK logo as a multi-level relief.

    Thin wrapper binding the plug's ``_LOGO_FRAC`` colour->depth table to the
    generic :func:`common.engraving.svg_relief`. ``raised=False`` engraves the
    relief (recessed); ``raised=True`` embosses it proud.
    """
    return svg_relief(
        part,
        z_top=z_top,
        radius=radius,
        frac_map=_LOGO_FRAC,
        svg_path=svg_path,
        amount=amount,
        fill=fill,
        raised=raised,
        clearance=clearance,
    )


def engrave_qr(part, *, z_top, radius, clearance=0.0,
               url, depth=0.5, error="m", border=2, fill=0.85):
    """Engrave a QR code pointing at ``url`` (thin wrapper over
    :func:`common.engraving.qr_cutter`)."""
    return qr_cutter(
        part, z_top=z_top, radius=radius, url=url, depth=depth,
        error=error, border=border, fill=fill,
    )


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
