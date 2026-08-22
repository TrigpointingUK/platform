"""Engraved lettering around the plug's upper ring (plug-specific config).

Real OS plugs are cast with "TRIANGULATION STATION" arcing over the top and
"ORDNANCE SURVEY" along the bottom, letter-tops facing outward, both reading
clockwise when viewed from above. The lettering is **cut into** the top surface
(engraved), not raised.

Measured on the brass original: the letters are 8 mm tall, their bottoms on a
Ø59 mm circle and their tops on Ø75 mm. They are set in a **highly condensed**
face and crammed together, which is not a style choice but arithmetic --
"TRIANGULATION STATION" at 8 mm caps wants about 96 mm of ink, and the arc
between the two spider-screw holes at that radius offers roughly 84 mm. The
caster squeezed; so do we.

So the letters here are laid out rather than typeset: each glyph is narrowed
horizontally (height untouched) by a factor solved to fill the available arc,
and they are set on a constant ink gap. That reproduces both traits at once --
condensed letterforms, and kerning that is absent rather than merely bad, every
pair spaced identically however the shapes fit together.

The generic mechanism lives in ``common.engraving``; this module holds only the
plug's font/size/placement and the two phrases.
"""

from __future__ import annotations

import math

from common.engraving import cap_height_font_size, engrave_arc_texts, fit_condense
from models.plug.params import PLUG

# --- Tuneable lettering parameters -----------------------------------------
# The narrowest face on hand, then condensed further. A stand-in: the OS cast
# letterform has not been identified.
FONT = "Nimbus Sans Narrow"

# [D] Measured on the brass original: bottoms on Ø59, tops on Ø75.
TEXT_RADIUS = 29.5    # mm, baseline (letter bottoms); letters grow OUTWARD
CAP_HEIGHT = 8.0      # mm = (75 - 59) / 2

LETTER_GAP = 0.25     # mm of bare metal between adjacent glyphs
WORD_SPACE = 1.8      # mm between words -- wide enough to still read as a space
HOLE_MARGIN = 1.5     # deg of clear air to leave either side of a screw hole
ENGRAVE_DEPTH = 0.6   # mm, how deep the letters cut below the surface


def usable_span_deg() -> float:
    """Arc between the two spider-screw holes that the lettering may occupy.

    The holes sit at 0/180 deg. What matters is the widest angle a hole subtends
    anywhere in the radial band the letters actually cross -- at the top of the
    letters, not at the hole's own centre radius -- so scan the band.
    """
    c, hole_r = PLUG.clr_hole_spacing / 2, PLUG.clr_hole_r
    worst = 0.0
    for i in range(201):
        r = TEXT_RADIUS + CAP_HEIGHT * i / 200
        if abs(r - c) < hole_r:
            worst = max(worst, math.degrees(
                math.acos((r * r + c * c - hole_r * hole_r) / (2 * r * c))))
    return 180.0 - 2.0 * (worst + HOLE_MARGIN)


# (text, centre angle deg, arc span deg) -- each phrase is fitted into the span
# and centred on the angle.
TEXTS = [
    ("TRIANGULATION STATION", 90.0, usable_span_deg()),
    ("ORDNANCE SURVEY", 270.0, usable_span_deg()),
]


def plug_text_metrics():
    """``(font_size, condense)`` actually used, for reporting at build time.

    ``condense`` is fitted to the LONGEST phrase and then shared, so both arcs
    are lettered identically and the shorter one simply occupies less of its
    span. It is an output of the geometry, not a setting.
    """
    font_size = cap_height_font_size(FONT, CAP_HEIGHT)
    longest = max((t for t, _, _ in TEXTS), key=len)
    condense = fit_condense(
        longest, span_deg=usable_span_deg(), radius=TEXT_RADIUS, font=FONT,
        font_size=font_size, word_space=WORD_SPACE, letter_gap=LETTER_GAP,
    )
    return font_size, condense


def engrave_plug_text(part, z_top: float):
    """Subtract both arcs of engraved lettering from ``part`` at height
    ``z_top`` (the plug's top surface). Returns the engraved part."""
    font_size, condense = plug_text_metrics()
    if condense <= 0.5:
        raise ValueError(
            f"lettering will not fit legibly: {CAP_HEIGHT} mm caps in {FONT} "
            f"need squeezing to {condense:.2f} of natural width in the "
            f"{usable_span_deg():.1f} deg available at r={TEXT_RADIUS}."
        )
    return engrave_arc_texts(
        part,
        TEXTS,
        z_top=z_top,
        radius=TEXT_RADIUS,
        font=FONT,
        font_size=font_size,
        depth=ENGRAVE_DEPTH,
        letter_gap=LETTER_GAP,
        word_space=WORD_SPACE,
        condense=condense,
    )
