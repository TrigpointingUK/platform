"""Shared TrigpointingUK brand assets.

The logo artwork and its colour->relief mapping are used by more than one model
(the inner-plug top treatment and the driver's top plateau), so they live here
rather than inside any single model. The mapping is fed to
``common.engraving.svg_relief`` as its ``frac_map``.
"""

from __future__ import annotations

from common.paths import REPO_ROOT

LOGO_SVG = REPO_ROOT / "res" / "TUK-Logo.svg"

# Fill colour (RGB 0-255) -> relief fraction, ported from the Blender model
# (Blender/Hotine/trig_pillar.py: build_flush_bracket_logo). Greens sit
# deepest/tallest, highlights shallowest; the black outline (0.0) is skipped.
LOGO_FRAC = {
    (99, 231, 16): 1.00,    # bright green (UK map) -- deepest
    (89, 157, 43): 0.60,    # dark green (grass)
    (147, 147, 147): 0.35,  # grey (trig / theodolite)
    (254, 232, 42): 0.35,   # yellow (benchmark arrow)
    (242, 242, 242): 0.20,  # near-white highlight
    (230, 230, 230): 0.20,  # light-grey highlight
    (0, 0, 0): 0.00,        # black outline -- skipped
}
