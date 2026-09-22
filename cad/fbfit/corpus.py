"""Stage 1 -- choose and cache candidate photographs, one style at a time.

Two public sources, both read-only:

* ``/v1/trigs/export`` gives every trig with its ``fb_number`` in one request,
  which is what assigns a bracket to a lettering style (``models.flush_bracket
  .styles.resolve_style``).
* ``/v1/photos?trig_id=`` gives that trig's photos. ``type == 'F'`` marks a
  flush-bracket photo. That label is user-supplied and unindexed, so it is a
  hint rather than a guarantee -- rectification re-checks it downstream.

**Licensing.** Only ``license == 'Y'`` (Public Domain) photos are taken.
Anything else is a display-only licence to TUK, which does not cover deriving
a printable model -- still less a product. The photo id, photographer and trig
are recorded for every image so any glyph can be traced back to what it came
from, and its contributors credited.
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

from common.paths import CAD_DIR
from models.flush_bracket.styles import parse_number, resolve_style

API = os.environ.get("FBFIT_API", "https://api.trigpointing.uk")
# Cloudflare rejects the default urllib agent.
UA = {"User-Agent": "trigpointinguk-fbfit/1.0 (+https://trigpointing.uk)"}

WORK = Path(os.environ.get("FBFIT_WORK", CAD_DIR / "fbfit" / "work"))

#: Downloaded photos are reduced to this long edge. A bracket filling ~60% of
#: a 1400 px frame lands at roughly 0.2 mm/px on the plate, so a 24 mm letter
#: is ~120 px tall -- ample for tracing, and a manageable cache.
MAX_EDGE = 1400


@dataclass(frozen=True)
class Candidate:
    trig_id: int
    waypoint: str
    fb_number: str
    style: str
    photo_id: int
    url: str
    width: int
    height: int
    user_name: str
    caption: str


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _get_json(url: str, timeout: int = 60):
    return json.loads(_get(url, timeout))


def trigs() -> list[dict]:
    """Every trig with its fb_number, cached locally after the first call."""
    WORK.mkdir(parents=True, exist_ok=True)
    cache = WORK / "trigs.json"
    if not cache.exists():
        cache.write_bytes(_get(f"{API}/v1/trigs/export?limit=30000", timeout=180))
    return json.loads(cache.read_text())["items"]


def by_style() -> dict[str, list[dict]]:
    """Group trigs by lettering style, keeping only real bracket numbers."""
    out: dict[str, list[dict]] = {}
    for t in trigs():
        num = (t.get("fb_number") or "").strip()
        if parse_number(num)[1] is None:
            continue
        out.setdefault(resolve_style(num).name, []).append(t)
    return out


def _photos_for(t: dict, min_width: int) -> list[Candidate]:
    # Finding candidates means one request per trig, and a style can have
    # thousands. Cache each reply so re-running a harvest -- to widen the
    # search, or after changing the width floor -- costs nothing.
    cache = WORK / "photos" / f"{t['id']}.json"
    if cache.exists():
        data = json.loads(cache.read_text())
    else:
        try:
            data = _get_json(f"{API}/v1/photos?trig_id={t['id']}&limit=100",
                             timeout=40)
        except Exception:
            return []
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data))
    num = t["fb_number"].strip()
    style = resolve_style(num).name
    out = []
    for p in data.get("items", []):
        if p.get("type") != "F" or p.get("license") != "Y":
            continue
        if min(p.get("width", 0), p.get("height", 0)) < min_width:
            continue
        out.append(
            Candidate(
                trig_id=t["id"], waypoint=t["waypoint"], fb_number=num, style=style,
                photo_id=p["id"], url=p["photo_url"], width=p["width"],
                height=p["height"], user_name=p.get("user_name") or "",
                caption=(p.get("caption") or "")[:80],
            )
        )
    return out


def find(style: str, want: int = 200, min_width: int = 900,
         workers: int = 6, per_trig: int = 1) -> list[Candidate]:
    """Search that style's trigs for usable flush-bracket photographs.

    Stops as soon as ``want`` are found. ``per_trig`` caps how many photos are
    taken from any one bracket, so the sample spreads across brackets rather
    than over-weighting a few that were photographed a dozen times.
    """
    import random

    pool = by_style().get(style, [])
    random.Random(1).shuffle(pool)
    found: list[Candidate] = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for batch_start in range(0, len(pool), workers * 8):
            batch = pool[batch_start:batch_start + workers * 8]
            for res in ex.map(lambda t: _photos_for(t, min_width), batch):
                res.sort(key=lambda c: -c.width)
                found.extend(res[:per_trig])
            if len(found) >= want:
                break
            time.sleep(0.05)
    return found[:want]


def download(cands: list[Candidate], style: str) -> Path:
    """Fetch and reduce each photo into ``work/<style>/raw``; write a manifest."""
    import cv2
    import numpy as np

    out = WORK / style / "raw"
    out.mkdir(parents=True, exist_ok=True)
    kept = []

    def one(c: Candidate):
        dst = out / f"{c.photo_id}.jpg"
        if dst.exists():
            return c
        try:
            buf = np.frombuffer(_get(c.url, timeout=120), np.uint8)
            im = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if im is None:
                return None
            h, w = im.shape[:2]
            s = MAX_EDGE / max(h, w)
            if s < 1:
                im = cv2.resize(im, (round(w * s), round(h * s)),
                                interpolation=cv2.INTER_AREA)
            cv2.imwrite(str(dst), im, [cv2.IMWRITE_JPEG_QUALITY, 92])
            return c
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as ex:
        for c in ex.map(one, cands):
            if c is not None:
                kept.append(c)

    (WORK / style / "manifest.json").write_text(
        json.dumps([asdict(c) for c in kept], indent=1)
    )
    return out
