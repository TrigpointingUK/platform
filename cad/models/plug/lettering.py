"""Engraved lettering around the plug's upper ring (plug-specific config).

Real OS plugs are cast with "TRIANGULATION STATION" arcing over the top and
"ORDNANCE SURVEY" along the bottom, letter-tops facing outward, both reading
clockwise when viewed from above. The lettering is **cut into** the top surface
(engraved), not raised.

The letters on the brass original are 8 mm tall in a **highly condensed** face,
crammed together with what is charitably called kerning -- the consequence of
fitting 21 characters into the arc between the two spider-screw holes. That is
not a stylistic choice to be tidied up; it is what the part looks like, and it
falls out of the arithmetic. At 8 mm caps the phrase needs more arc than exists,
so the narrowest face available is used and the letters are then set on a
constant gap computed to fill the space exactly (see ``common.engraving``).

The generic mechanism lives in ``common.engraving``; this module holds only the
plug's font/size/depth and the two phrases.
"""

from __future__ import annotations

from common.engraving import cap_height_font_size, engrave_arc_texts, fit_letter_gap

# --- Tuneable lettering parameters -----------------------------------------
# The narrowest face on hand; a stand-in for the OS cast letterform, which has
# not been identified. If it is missing, the layout still fits the arc (the gap
# is computed from whatever glyphs come back) but will crowd, so build_plug
# reports the gap it ended up with.
FONT = "Nimbus Sans Narrow"
CAP_HEIGHT = 8.0  # [D] mm, measured on the brass original
# Baseline radius. Letters grow OUTWARD from here, so this plus the cap height
# (plus a little round-letter overshoot) has to stay inside the top face, which
# ends at upper_r - upper_chamfer = 43.73 mm.
TEXT_RADIUS = 35.0
WORD_SPACE = 2.0      # mm, between words -- wide enough to read as a space
ENGRAVE_DEPTH = 0.6   # mm, how deep the letters cut below the surface

# (text, centre angle deg, arc span deg). The span is what the phrase is fitted
# into, centred on the given angle. 166 deg is what the two Ø9 mm spider-screw
# holes at 0/180 leave free: each blocks +/-6.71 deg at its widest.
LETTER_SPAN = 166.0
TEXTS = [
    ("TRIANGULATION STATION", 90.0, LETTER_SPAN),
    ("ORDNANCE SURVEY", 270.0, LETTER_SPAN),
]


def plug_text_metrics():
    """``(font_size, letter_gap)`` actually used, for reporting at build time.

    The gap is fitted to the LONGEST phrase and then shared, so both arcs are
    lettered identically and the shorter one simply occupies less of its span.
    A gap at or below zero means the phrase cannot fit without glyphs colliding.
    """
    font_size = cap_height_font_size(FONT, CAP_HEIGHT)
    longest = max((t for t, _, _ in TEXTS), key=len)
    gap = fit_letter_gap(
        longest, span_deg=LETTER_SPAN, radius=TEXT_RADIUS,
        font=FONT, font_size=font_size, word_space=WORD_SPACE,
    )
    return font_size, gap


def engrave_plug_text(part, z_top: float):
    """Subtract both arcs of engraved lettering from ``part`` at height
    ``z_top`` (the plug's top surface). Returns the engraved part."""
    font_size, letter_gap = plug_text_metrics()
    if letter_gap <= 0:
        raise ValueError(
            f"lettering does not fit: {CAP_HEIGHT} mm caps in {FONT} need more "
            f"than the {LETTER_SPAN} deg available at r={TEXT_RADIUS} "
            f"(gap {letter_gap:.3f} mm). Lower CAP_HEIGHT or find a narrower face."
        )
    return engrave_arc_texts(
        part,
        TEXTS,
        z_top=z_top,
        radius=TEXT_RADIUS,
        font=FONT,
        font_size=font_size,
        depth=ENGRAVE_DEPTH,
        letter_gap=letter_gap,
        word_space=WORD_SPACE,
    )
