"""Stage 3 -- average many flattened brackets into clean glyphs.

This is where the corpus earns its keep. One photograph shows illumination,
not relief, and estimating depth from it is hopeless: the albedo is unknown
and covered in lichen, paint, rust and shadow. But across many photographs the
lighting direction is effectively random while the **casting is identical**, so
averaging suppresses everything that is not geometry.

Two kinds of average come out of the same stack:

* **The legend** (O, S, B, M, the arrow) is in the same place on every bracket
  of a style, so the plain mean already resolves it.
* **The digits** differ from bracket to bracket, so they blur in the mean --
  which is exactly what localises them. The per-pixel *standard deviation*
  across the stack lights up precisely where the number is and is flat
  everywhere else. Cells found that way are then regrouped by which digit each
  bracket actually carries (known from ``trig.fb_number``, so no OCR is
  needed) and averaged again, giving one clean image per digit.

Before averaging, each image is illumination-flattened and then re-aligned to
the running mean, because residual detection error would otherwise soften every
edge the tracing stage depends on.
"""

from __future__ import annotations

import json

import cv2
import numpy as np

from fbfit.corpus import WORK


def flatten_illumination(gray: np.ndarray, sigma: float = 40.0) -> np.ndarray:
    """Divide out the slow lighting gradient, then robustly rescale to 0..1.

    A flush bracket is photographed in whatever light there was. The relief is
    a high-frequency signal riding on a low-frequency one that carries no
    information about the casting, so the low frequencies go.
    """
    g = gray.astype(np.float32)
    base = cv2.GaussianBlur(g, (0, 0), sigma)
    out = g / np.maximum(base, 1e-3)
    lo, hi = np.percentile(out, (2, 98))
    if hi - lo < 1e-6:
        return np.zeros_like(out)
    return np.clip((out - lo) / (hi - lo), 0, 1)


def align_to(ref: np.ndarray, img: np.ndarray,
             max_shift_px: float = 70.0, max_scale: float = 0.14,
             min_cc: float = 0.05) -> np.ndarray | None:
    """Refine ``img`` onto ``ref`` with a small affine warp, or give up.

    Guarded three ways, because a bad alignment is worse than a missing one:
    it does not just fail to help, it smears the average that every glyph is
    cut from.

    * ECC's correlation coefficient must clear ``min_cc``. The bar is low on
      purpose: this is correlating photographs of *different* brackets, weathered
      differently and carrying different numbers, so even a perfect alignment
      only reaches ~0.5. It rejects failures to converge, not poor matches.
    * the translation and scale must stay within what a detection error could
      plausibly be. These are generous because the corrections are genuinely
      large -- the detector does not always lock on to the same rectangle
      (bead outer edge, bead crest, recess), which is the main accuracy limit
      in the pipeline today.
    """
    warp = np.eye(2, 3, dtype=np.float32)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 60, 1e-5)
    try:
        cc, warp = cv2.findTransformECC(ref, img, warp, cv2.MOTION_AFFINE,
                                        crit, None, 5)
    except cv2.error:
        return None
    if not np.isfinite(cc) or cc < min_cc:
        return None
    if np.hypot(warp[0, 2], warp[1, 2]) > max_shift_px:
        return None
    if abs(warp[0, 0] - 1) > max_scale or abs(warp[1, 1] - 1) > max_scale:
        return None
    h, w = ref.shape
    return cv2.warpAffine(img, warp, (w, h),
                          flags=cv2.INTER_LINEAR + cv2.WARP_INVERSE_MAP,
                          borderMode=cv2.BORDER_REPLICATE)


def build_stack(style: str, passes: int = 2) -> dict:
    """Flatten, align and average every rectified image for one style."""
    d = WORK / style / "rect"
    meta = json.loads((WORK / style / "rect.json").read_text())
    imgs, keep = [], []
    for m in meta:
        p = d / f"{m['photo_id']}.png"
        if not p.exists():
            continue
        g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
        if g is None:
            continue
        imgs.append(flatten_illumination(g))
        keep.append(m)
    if not imgs:
        raise SystemExit(f"{style}: nothing rectified yet")

    arr = np.stack(imgs)
    # Seed the reference from the single best detection, not from the mean of
    # everything. An unaligned mean is blurred, and aligning sharp images to a
    # blurred reference correlates poorly across the board -- so the guard
    # throws away good images along with bad. One real bracket is a far better
    # starting reference; the mean takes over from the first pass onward.
    order = np.argsort([-m.get("score", 0) for m in keep])
    mean = arr[order[0]].astype(np.float32)
    for _ in range(passes):
        aligned, kept2 = [], []
        for a, m in zip(arr, keep):
            r = align_to(mean.astype(np.float32), a.astype(np.float32))
            if r is not None:
                aligned.append(r)
                kept2.append(m)
        if not aligned:
            break
        arr = np.stack(aligned)
        keep = kept2
        mean = arr.mean(0)

    out = WORK / style
    std = arr.std(0)
    cv2.imwrite(str(out / "mean.png"), (mean * 255).astype(np.uint8))
    cv2.imwrite(str(out / "std.png"),
                (std / max(std.max(), 1e-6) * 255).astype(np.uint8))
    np.save(out / "stack.npy", arr.astype(np.float16))
    (out / "stack.json").write_text(json.dumps(keep, indent=1))
    return {"style": style, "n": len(arr), "mean": mean, "std": std, "meta": keep}
