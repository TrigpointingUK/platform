"""Engraved lettering around the plug's upper ring (plug-specific config).

Real OS plugs are cast with "TRIANGULATION STATION" arcing over the top and
"ORDNANCE SURVEY" along the bottom, letter-tops facing outward, both reading
clockwise when viewed from above. The lettering is **cut into** the top surface
(engraved), not raised.

The generic "text on an arc -> downward cutter -> subtract" mechanism lives in
``common.engraving``; this module only holds the plug's font/size/depth and the
two phrases.
"""

from __future__ import annotations

from common.engraving import engrave_arc_texts

# --- Tuneable lettering parameters -----------------------------------------
FONT = "DejaVu Sans"      # stand-in for the OS cast face; swap once identified
TEXT_RADIUS = 33.0        # mm, baseline radius (mid upper-ring annulus)
FONT_SIZE = 7.0           # mm, cap height
ENGRAVE_DEPTH = 0.6       # mm, how deep the letters cut below the surface

# (text, centre angle deg, available arc span deg). The span is the path the
# text is centred on (position_on_path=0.5); glyphs occupy their natural arc
# length within it. Both phrases sit between the two spider-screw holes at
# 0 deg / 180 deg.
TEXTS = [
    ("TRIANGULATION  STATION", 90.0, 200.0),
    ("ORDNANCE  SURVEY", 270.0, 200.0),
]


def engrave_plug_text(part, z_top: float):
    """Subtract both arcs of engraved lettering from ``part`` at height
    ``z_top`` (the plug's top surface). Returns the engraved part."""
    return engrave_arc_texts(
        part,
        TEXTS,
        z_top=z_top,
        radius=TEXT_RADIUS,
        font=FONT,
        font_size=FONT_SIZE,
        depth=ENGRAVE_DEPTH,
    )
