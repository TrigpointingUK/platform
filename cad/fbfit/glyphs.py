"""Stage 5 -- cut the stack into individual glyphs and average each one.

Two different jobs, because the plate carries two kinds of lettering.

**The legend** (``O S B M``) is identical on every bracket of a style, so the
stack mean already *is* a clean image of it. The glyphs are simply cropped out
at the boxes the model already holds in ``params``.

**The number** differs from bracket to bracket, which is what makes it
findable: the per-pixel standard deviation across the stack is near zero over
the plate and the fixed legend, and large exactly where the digits are. So the
number band is measured, not specified.

Within the band the characters sit on a regular pitch -- they were struck from
a punch set on a jig -- so the band is divided into equal cells. Each bracket
then contributes its cell images to the accumulator for the character it
actually carries, which is known from ``trig.fb_number``. No OCR anywhere: the
corpus already tells us the answer, and the averaging is what recovers the
shape.
"""

from __future__ import annotations

import json
from collections import defaultdict

import cv2
import numpy as np

from fbfit.corpus import WORK
from fbfit.rectify import PX_PER_MM, to_px
from models.flush_bracket.flush_bracket import _Layout
from models.flush_bracket.params import FB
from models.flush_bracket.styles import STYLES, legend_number

_LAY = _Layout(FB)


def legend_boxes(style: str) -> dict[str, tuple[int, int, int, int]]:
    """Canonical-pixel crop boxes for O, S, B, M (and the BsM middle S)."""
    lay = _Layout(FB, STYLES[style])
    pad = 2.0  # mm of margin so the averaged glyph is never clipped
    out: dict[str, tuple[int, int, int, int]] = {}
    seen: defaultdict[str, int] = defaultdict(int)
    for glyph, cx, w, h, z_top in lay.letters:
        seen[glyph] += 1
        key = glyph if seen[glyph] == 1 else f"{glyph}{seen[glyph]}"
        c0, r0 = to_px(cx + w / 2 + pad, z_top + pad)
        c1, r1 = to_px(cx - w / 2 - pad, z_top - h - pad)
        out[key] = (int(c0), int(r0), int(c1), int(r1))
    return out


def number_band(std: np.ndarray, floor: float = 0.35) -> tuple[int, int, int, int]:
    """Locate the number from where the stack disagrees with itself.

    Searched only below the legend, so the keyhole shadows and the staff slot
    -- which also vary between photographs -- cannot be mistaken for digits.
    """
    _, r_lo = to_px(0, _LAY.num_z_top + 6)
    _, r_hi = to_px(0, 0.0)
    r_lo, r_hi = int(r_lo), int(min(r_hi, std.shape[0]))
    band = std[r_lo:r_hi]
    s = band / max(band.max(), 1e-6)

    rows = s.mean(axis=1)
    rows = rows / max(rows.max(), 1e-6)
    hot_r = np.where(rows > floor)[0]
    cols = s.mean(axis=0)
    cols = cols / max(cols.max(), 1e-6)
    hot_c = np.where(cols > floor)[0]
    if len(hot_r) < 3 or len(hot_c) < 3:
        raise ValueError("no number band found -- too few images, or misaligned")
    return (int(hot_c[0]), r_lo + int(hot_r[0]),
            int(hot_c[-1]) + 1, r_lo + int(hot_r[-1]) + 1)


def _cells(box, n: int) -> list[tuple[int, int, int, int]]:
    c0, r0, c1, r1 = box
    edges = np.linspace(c0, c1, n + 1).round().astype(int)
    return [(edges[i], r0, edges[i + 1], r1) for i in range(n)]


def extract(style: str, min_per_glyph: int = 6) -> dict:
    """Average every glyph of one style out of its stack."""
    base = WORK / style
    arr = np.load(base / "stack.npy").astype(np.float32)
    meta = json.loads((base / "stack.json").read_text())
    std = arr.std(0)

    out_dir = base / "glyphs"
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}

    # ---- the fixed legend, straight off the mean -------------------------
    mean = arr.mean(0)
    for key, (c0, r0, c1, r1) in legend_boxes(style).items():
        patch = mean[max(r0, 0):r1, max(c0, 0):c1]
        if patch.size == 0:
            continue
        cv2.imwrite(str(out_dir / f"legend_{key}.png"),
                    (patch / max(patch.max(), 1e-6) * 255).astype(np.uint8))
        results[f"legend_{key}"] = {"n": len(arr), "shape": list(patch.shape)}

    # ---- the number, grouped by character count --------------------------
    band = number_band(std)
    groups: defaultdict[int, list[int]] = defaultdict(list)
    for i, m in enumerate(meta):
        txt = legend_number(m.get("fb_number"))
        if txt:
            groups[len(txt)].append(i)

    acc: defaultdict[str, list[np.ndarray]] = defaultdict(list)
    for n_chars, idxs in groups.items():
        if len(idxs) < min_per_glyph:
            continue
        cells = _cells(band, n_chars)
        for i in idxs:
            txt = legend_number(meta[i].get("fb_number"))
            for ch, (c0, r0, c1, r1) in zip(txt, cells):
                patch = arr[i, r0:r1, c0:c1]
                if patch.size:
                    acc[ch].append(patch)

    for ch, patches in sorted(acc.items()):
        if len(patches) < min_per_glyph:
            continue
        h = min(p.shape[0] for p in patches)
        w = min(p.shape[1] for p in patches)
        stack = np.stack([p[:h, :w] for p in patches])
        m = stack.mean(0)
        name = "O_letter" if ch == "O" else ch
        cv2.imwrite(str(out_dir / f"num_{name}.png"),
                    ((m - m.min()) / max(float(np.ptp(m)), 1e-6) * 255).astype(np.uint8))
        results[f"num_{ch}"] = {"n": len(patches), "shape": [h, w]}

    (base / "glyphs.json").write_text(json.dumps(
        {"band_px": list(band),
         "band_mm": [round(x / PX_PER_MM, 2) for x in band],
         "glyphs": results}, indent=1))
    return {"style": style, "band": band, "glyphs": results}
