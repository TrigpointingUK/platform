"""Engraved lettering around the plug's upper ring.

Real OS plugs are cast with "TRIANGULATION STATION" arcing over the top and
"ORDNANCE SURVEY" along the bottom, letter-tops facing outward, both reading
clockwise when viewed from above. The lettering is **cut into** the top surface
(engraved), not raised.

The text is laid along a circular arc path and extruded downward to form a
cutter that is subtracted from the plug body.
"""

from __future__ import annotations

from build123d import (
    BuildLine,
    BuildSketch,
    CenterArc,
    Plane,
    Text,
    extrude,
)

# --- Tuneable lettering parameters -----------------------------------------
FONT = "DejaVu Sans"      # stand-in for the OS cast face; swap once identified
TEXT_RADIUS = 33.0        # mm, baseline radius (mid upper-ring annulus)
FONT_SIZE = 7.0           # mm, cap height
ENGRAVE_DEPTH = 0.6       # mm, how deep the letters cut below the surface
_OVERSHOOT = 0.4          # mm, cutter starts above the surface for a clean cut

# (text, centre angle deg, available arc span deg). The span is the path the
# text is centred on (position_on_path=0.5); glyphs occupy their natural arc
# length within it. Both phrases sit between the two spider-screw holes at
# 0 deg / 180 deg.
TEXTS = [
    ("TRIANGULATION  STATION", 90.0, 200.0),
    ("ORDNANCE  SURVEY", 270.0, 200.0),
]


def _one_text_cutter(txt: str, centre_deg: float, span_deg: float, z_top: float):
    """A downward-extruded cutter solid for one arc of engraved text."""
    with BuildSketch(Plane.XY.offset(z_top + _OVERSHOOT)) as sk:
        with BuildLine():
            # Traverse the arc clockwise (negative arc_size) so the text reads
            # clockwise from above with letter-tops facing outward -- matching
            # real OS plugs and the render model's `angle = centre - t*span`.
            arc = CenterArc(
                (0, 0),
                TEXT_RADIUS,
                start_angle=centre_deg + span_deg / 2,
                arc_size=-span_deg,
            )
        Text(
            txt,
            font_size=FONT_SIZE,
            font=FONT,
            path=arc.edges()[0],
            position_on_path=0.5,  # centre the phrase on the arc midpoint
        )
    return extrude(sk.sketch, amount=-(ENGRAVE_DEPTH + _OVERSHOOT))


def engrave_plug_text(part, z_top: float):
    """Subtract both arcs of engraved lettering from ``part`` at height
    ``z_top`` (the plug's top surface). Returns the engraved part."""
    for txt, centre_deg, span_deg in TEXTS:
        part = part - _one_text_cutter(txt, centre_deg, span_deg, z_top)
    return part
