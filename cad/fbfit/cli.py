"""Pipeline driver: ``python -m fbfit.cli <stage> [style ...]``.

Stages run in order and each writes into ``$FBFIT_WORK/<style>/``, so any one
can be re-run without repeating the others:

    harvest   query the API, download and cache candidate photographs
    rectify   detect and flatten each bracket; keep only convincing ones
    stack     illumination-flatten, align and average
    review    contact sheets to look at before trusting any of it
"""

from __future__ import annotations

import argparse
import json
import sys

from fbfit.corpus import WORK

STYLES = ["2gl", "s-early", "bsm", "s-late", "five-digit"]


def harvest(style: str, want: int, min_width: int) -> None:
    from fbfit import corpus

    cands = corpus.find(style, want=want, min_width=min_width)
    print(f"{style}: {len(cands)} candidates")
    corpus.download(cands, style)
    n = len(list((WORK / style / "raw").glob("*.jpg")))
    print(f"{style}: {n} cached in {WORK / style / 'raw'}")


def rectify(style: str, min_score: float) -> None:
    import cv2
    from fbfit import rectify as R

    raw = WORK / style / "raw"
    man = {m["photo_id"]: m
           for m in json.loads((WORK / style / "manifest.json").read_text())}
    out = WORK / style / "rect"
    out.mkdir(parents=True, exist_ok=True)
    kept = []
    files = sorted(raw.glob("*.jpg"))
    for i, f in enumerate(files, 1):
        img = cv2.imread(str(f))
        if img is None:
            continue
        r = R.rectify(img, min_score=min_score)
        if r is None:
            continue
        pid = int(f.stem)
        cv2.imwrite(str(out / f"{pid}.png"),
                    cv2.cvtColor(r.image, cv2.COLOR_BGR2GRAY))
        m = dict(man.get(pid, {"photo_id": pid}))
        m.update(score=round(float(r.score), 4), obliquity=round(float(r.obliquity), 4))
        kept.append(m)
        if i % 25 == 0:
            print(f"  {i}/{len(files)} scanned, {len(kept)} kept", flush=True)
    (WORK / style / "rect.json").write_text(json.dumps(kept, indent=1))
    pct = 100 * len(kept) / max(len(files), 1)
    print(f"{style}: rectified {len(kept)}/{len(files)} ({pct:.0f}%)")


def stack(style: str) -> None:
    from fbfit.stack import build_stack

    r = build_stack(style)
    print(f"{style}: stacked {r['n']} -> {WORK / style / 'mean.png'}")


def review(style: str, n: int) -> None:
    import cv2
    import numpy as np

    d = WORK / style / "rect"
    meta = json.loads((WORK / style / "rect.json").read_text())
    meta.sort(key=lambda m: -m.get("score", 0))
    tiles = []
    for m in meta[:n]:
        p = d / f"{m['photo_id']}.png"
        if p.exists():
            g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            tiles.append(cv2.resize(g, (120, 228)))
    if not tiles:
        print(f"{style}: nothing to review")
        return
    cols = 10
    rows = (len(tiles) + cols - 1) // cols
    sheet = np.full((rows * 232, cols * 124), 255, np.uint8)
    for i, t in enumerate(tiles):
        r0, c0 = (i // cols) * 232, (i % cols) * 124
        sheet[r0:r0 + 228, c0:c0 + 120] = t
    out = WORK / style / "review.png"
    cv2.imwrite(str(out), sheet)
    print(f"{style}: {out} ({len(tiles)} tiles)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["harvest", "rectify", "stack", "review"])
    ap.add_argument("styles", nargs="*", default=None)
    ap.add_argument("--want", type=int, default=200)
    ap.add_argument("--min-width", type=int, default=900)
    ap.add_argument("--min-score", type=float, default=0.03)
    ap.add_argument("--n", type=int, default=40)
    a = ap.parse_args(argv)
    for style in (a.styles or STYLES):
        if a.stage == "harvest":
            harvest(style, a.want, a.min_width)
        elif a.stage == "rectify":
            rectify(style, a.min_score)
        elif a.stage == "stack":
            stack(style)
        elif a.stage == "review":
            review(style, a.n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
