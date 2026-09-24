"""Stage 2 -- find the bracket in a photograph and flatten it.

Everything downstream depends on one thing: that a given point on the casting
lands on the same pixel in every photograph. Then the glyphs can simply be
averaged.

The target is **bead-outer plate space** -- the full rectangle the beading
bounds, (w + 2*bead_r) x (h + 2*bead_r) mm -- because that outline is the
strongest edge in almost every photograph.

Detection is deliberately **high-precision, low-recall**. There are thousands
of candidate photographs and only a few hundred are needed per style, so
anything doubtful is thrown away rather than repaired. A detection is kept only
if the flattened image actually looks like a flush bracket, scored by whether
the openings land where the model says they should:

* the two keyhole pockets and the staff slot are deep and shadowed, so dark;
* the plate face and the number panel are flat and lit, so lighter.

That test also resolves the 180-degree ambiguity for free -- the opening
pattern is asymmetric top-to-bottom -- and rejects the common false positive
of locking on to the recess in the pillar instead of the bracket, because then
the openings do not line up.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from models.flush_bracket.flush_bracket import _Layout
from models.flush_bracket.params import FB

#: Canonical resolution. 5 px/mm is a little finer than the cached photos
#: resolve, so rectification never discards detail it was given.
PX_PER_MM = 5.0

_LAY = _Layout(FB)
PLATE_W = FB.w + 2 * FB.bead_r  # 95.5 mm, bead outer
PLATE_H = FB.h + 2 * FB.bead_r  # 182.0 mm
CW = round(PLATE_W * PX_PER_MM)
CH = round(PLATE_H * PX_PER_MM)


def to_px(x_mm: float, z_mm: float) -> tuple[float, float]:
    """Model (x, z) in mm -> canonical (col, row) in px.

    Note the x flip: the model's +x points to the viewer's LEFT (see
    ``params``), and column 0 is the left of the image.
    """
    col = (PLATE_W / 2 - x_mm) * PX_PER_MM
    row = (FB.h + FB.bead_r - z_mm) * PX_PER_MM
    return col, row


def _box(x0_mm, x1_mm, z0_mm, z1_mm) -> tuple[int, int, int, int]:
    c0, r1 = to_px(max(x0_mm, x1_mm), min(z0_mm, z1_mm))
    c1, r0 = to_px(min(x0_mm, x1_mm), max(z0_mm, z1_mm))
    return (int(round(c0)), int(round(r0)), int(round(c1)), int(round(r1)))


# Regions the model says are openings (dark) and flat face (lighter).
_DARK = [
    _box(_LAY.kh_cx - FB.kh_w / 2, _LAY.kh_cx + FB.kh_w / 2,
         _LAY.kh_z_bot, _LAY.kh_z_top),
    _box(-_LAY.kh_cx - FB.kh_w / 2, -_LAY.kh_cx + FB.kh_w / 2,
         _LAY.kh_z_bot, _LAY.kh_z_top),
    _box(-FB.hole_w / 2, FB.hole_w / 2,
         _LAY.hole_z_top - 9, _LAY.hole_z_top - 1),
]
#: The number panel: flat plate, low down, and the key to which way up the
#: bracket is. The openings are all in the top half, so on an upside-down
#: detection this region lands where the keyhole shadows are and the test
#: below inverts.
_PANEL = _box(-34, 34, _LAY.num_z_bot - 4, _LAY.num_z_top)


@dataclass
class Rectified:
    image: np.ndarray       # CH x CW x 3, uint8
    score: float            # face-minus-opening contrast, 0..1-ish
    quad: np.ndarray        # source corners, float32 (4, 2)
    obliquity: float        # 0 = square on; higher = more foreshortened


def _local_contrast(gray: np.ndarray, box, grow: int = 14) -> float:
    """How much darker ``box`` is than the ring immediately around it.

    Local rather than global, because a photograph's overall exposure says
    nothing about whether this particular opening is in shadow. Returns a
    Michelson-style ratio, positive when the box is the darker of the two.
    """
    c0, r0, c1, r1 = box
    h, w = gray.shape
    c0, r0 = max(0, c0), max(0, r0)
    c1, r1 = min(w, c1), min(h, r1)
    if c1 - c0 < 4 or r1 - r0 < 4:
        return -1.0
    inner = gray[r0:r1, c0:c1]
    o0, p0 = max(0, c0 - grow), max(0, r0 - grow)
    o1, p1 = min(w, c1 + grow), min(h, r1 + grow)
    ring = gray[p0:p1, o0:o1].copy()
    ring[r0 - p0:r1 - p0, c0 - o0:c1 - o0] = np.nan
    with np.errstate(invalid="ignore"):
        outer = np.nanmean(ring)
    if not np.isfinite(outer):
        return -1.0
    i, o = float(inner.mean()), float(outer)
    return (o - i) / max(o + i, 1e-6)


def _order(quad: np.ndarray) -> np.ndarray:
    """Return the quad wound consistently, starting somewhere arbitrary."""
    c = quad.mean(axis=0)
    ang = np.arctan2(quad[:, 1] - c[1], quad[:, 0] - c[0])
    q = quad[np.argsort(ang)]
    # Match the destination quad's winding, which is clockwise in image
    # coordinates. Getting this backwards silently mirrors every rectified
    # image -- the letters still look plausible, they are just reversed.
    # With y pointing down, a positive shoelace area IS clockwise.
    area = 0.0
    for i in range(4):
        x0, y0 = q[i]
        x1, y1 = q[(i + 1) % 4]
        area += x0 * y1 - x1 * y0
    if area < 0:
        q = q[::-1]
    return q.astype(np.float32)


def _obliquity(quad: np.ndarray) -> float:
    """How far from square-on, from the disagreement of opposite edge lengths."""
    d = [np.linalg.norm(quad[i] - quad[(i + 1) % 4]) for i in range(4)]
    a = abs(d[0] - d[2]) / max(d[0] + d[2], 1e-6)
    b = abs(d[1] - d[3]) / max(d[1] + d[3], 1e-6)
    return float(max(a, b))


def _candidates(img: np.ndarray) -> list[np.ndarray]:
    """Quadrilaterals that might be the bead outline."""
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 7, 60, 60)
    area_img = h * w
    quads = []
    edges_set = []
    for lo, hi in ((30, 90), (50, 150), (80, 220)):
        edges_set.append(cv2.Canny(gray, lo, hi))
    edges_set.append(
        cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                              cv2.THRESH_BINARY_INV, 31, 7)
    )
    for e in edges_set:
        e = cv2.dilate(e, np.ones((3, 3), np.uint8), iterations=1)
        cnts, _ = cv2.findContours(e, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for c in cnts:
            a = cv2.contourArea(c)
            if a < 0.03 * area_img or a > 0.92 * area_img:
                continue
            peri = cv2.arcLength(c, True)
            for eps in (0.02, 0.035, 0.05):
                ap = cv2.approxPolyDP(c, eps * peri, True)
                if len(ap) == 4 and cv2.isContourConvex(ap):
                    quads.append(ap.reshape(4, 2).astype(np.float32))
                    break
    return quads


def rectify(img: np.ndarray, *, min_score: float = 0.055,
            max_obliquity: float = 0.22) -> Rectified | None:
    """Flatten the bracket in ``img``, or return None if unconvinced."""
    dst = np.array([[0, 0], [CW - 1, 0], [CW - 1, CH - 1], [0, CH - 1]],
                   dtype=np.float32)
    best: Rectified | None = None
    for quad in _candidates(img):
        q = _order(quad)
        ob = _obliquity(q)
        if ob > max_obliquity:
            continue
        # The winding is known but the starting corner is not: try all four.
        for k in range(4):
            src = np.roll(q, k, axis=0)
            try:
                M = cv2.getPerspectiveTransform(src, dst)
                warp = cv2.warpPerspective(img, M, (CW, CH))
            except cv2.error:
                continue
            g = cv2.cvtColor(warp, cv2.COLOR_BGR2GRAY).astype(np.float32)
            if float(g.max() - g.min()) < 25:
                continue
            # Every opening must independently read darker than its own
            # surroundings. Taking the WORST of the three, rather than their
            # mean, is what rejects the common false positives -- a patch of
            # shadowed rock can produce one convincing dark box, never three
            # in the right places at the right spacing.
            opening = min(_local_contrast(g, b) for b in _DARK)
            # Orientation: the keyhole pockets must be darker than the number
            # panel. Four cyclic corner orderings are tried, so without this
            # an upside-down detection can still win on the opening test
            # alone -- a shadowed number panel looks much like a pocket.
            kh = np.mean([g[max(0, r0):r1, max(0, c0):c1].mean()
                          for c0, r0, c1, r1 in _DARK[:2]])
            pc0, pr0, pc1, pr1 = _PANEL
            panel = g[max(0, pr0):pr1, max(0, pc0):pc1]
            if panel.size == 0:
                continue
            upright = (panel.mean() - kh) / max(panel.mean() + kh, 1e-6)
            score = min(opening, upright)
            if best is None or score > best.score:
                best = Rectified(warp, score, src, ob)
    if best is None or best.score < min_score:
        return None
    return best
