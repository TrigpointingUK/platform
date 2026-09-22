"""Stage 4 -- turn an averaged glyph into a vector outline.

The output is an SVG in millimetres on the model's own scale, so importing it
into ``build123d`` (via ``ocpsvg``, already a dependency) places it at the
right size with no further fiddling.

The averaged glyph is thresholded rather than height-mapped. That is not a
compromise: the casting's relief is essentially binary -- a flat plate and a
plateau a constant height above it -- so a mask plus the known relief height
*is* the geometry. Interpreting the average as a height field would invent
detail the photographs never contained.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from fbfit.rectify import PX_PER_MM


def binarise(patch: np.ndarray, polarity: int = 1,
             blur: float = 1.2) -> np.ndarray:
    """Threshold an averaged glyph patch to a clean mask.

    ``polarity`` is +1 when the raised glyph averages *brighter* than the
    surrounding plate and -1 when it averages darker. Which it is depends on
    how the castings weather -- proud letters shed dirt and catch light, but
    painted brackets invert that -- so it is measured per style rather than
    assumed (see ``estimate_polarity``).
    """
    g = patch.astype(np.float32)
    if blur:
        g = cv2.GaussianBlur(g, (0, 0), blur)
    g = (g - g.min()) / max(g.max() - g.min(), 1e-6)
    if polarity < 0:
        g = 1.0 - g
    t, _ = cv2.threshold((g * 255).astype(np.uint8), 0, 255,
                         cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = (g * 255 >= t).astype(np.uint8) * 255
    # Tidy: drop speckle, close pinholes, keep it conservative.
    k = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=2)
    return mask


def estimate_polarity(patch: np.ndarray, margin: int = 4) -> int:
    """Decide whether the glyph reads brighter or darker than its surround.

    Compares the centre of the patch (mostly glyph) with its border (mostly
    plate). Crude, but it only has to get a sign right, and it is measured on
    an average of dozens of brackets rather than on one photograph.
    """
    g = patch.astype(np.float32)
    border = np.concatenate([
        g[:margin].ravel(), g[-margin:].ravel(),
        g[:, :margin].ravel(), g[:, -margin:].ravel()])
    h, w = g.shape
    centre = g[h // 4:3 * h // 4, w // 4:3 * w // 4]
    return 1 if centre.mean() >= border.mean() else -1


def mask_to_svg(mask: np.ndarray, path: Path, *,
                px_per_mm: float = PX_PER_MM, simplify_mm: float = 0.12,
                min_area_mm2: float = 0.5) -> int:
    """Write ``mask`` as an even-odd SVG path in millimetres.

    ``RETR_CCOMP`` separates outer boundaries from holes, which is what keeps
    the counters of O, B, 8 and so on open.
    """
    cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        raise ValueError("no contours in mask")
    eps = simplify_mm * px_per_mm
    min_area = min_area_mm2 * px_per_mm ** 2
    parts = []
    for c in cnts:
        if cv2.contourArea(c) < min_area:
            continue
        ap = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        if len(ap) < 3:
            continue
        pts = " ".join(f"{x / px_per_mm:.3f},{y / px_per_mm:.3f}" for x, y in ap)
        parts.append(f"M {pts} Z")
    if not parts:
        raise ValueError("no contours survived filtering")
    h, w = mask.shape
    wmm, hmm = w / px_per_mm, h / px_per_mm
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{wmm:.3f}mm" height="{hmm:.3f}mm" '
        f'viewBox="0 0 {wmm:.3f} {hmm:.3f}">\n'
        f'  <path fill-rule="evenodd" fill="#000" d="{" ".join(parts)}"/>\n'
        f'</svg>\n'
    )
    return len(parts)
