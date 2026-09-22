# `fbfit` — deriving flush-bracket glyphs from the photo corpus

Builds a vector glyph set for each flush-bracket **lettering style** (see
`models/flush_bracket/styles.py`) out of TrigpointingUK's own photographs, so
that printed replicas carry the letterforms the Ordnance Survey actually cast
rather than whichever system font came closest.

Runs offline, on a workstation. Nothing here is deployed.

## Why this is tractable

A single photograph cannot give relief. The albedo is unknown and covered in
lichen, paint, rust and shadow, the lighting is whatever the weather was, and
shape-from-shading under those conditions is hopeless. Depth-mapping one image
would invent detail that was never in it.

Three facts change the problem:

1. **The casting is identical within a style.** Flatten every photograph of a
   style onto the same plate coordinates and a given point on the casting lands
   on the same pixel every time.
2. **The lighting is effectively random across photographers.** So averaging
   many flattened images suppresses everything that is not geometry. This is
   the whole trick, and it gets better with corpus size — the corpus holds
   ~400k photos over ~26k trigs, 8,302 of which carry a bracket number.
3. **We already know what each bracket says.** `trig.fb_number` gives the
   number, so digits can be grouped and averaged *without OCR*. There is no
   recognition step to get wrong.

And the relief itself is **binary** — a flat plate and a plateau a constant
height above it — so a thresholded average plus the known relief height is the
geometry, exactly. No height field is required or wanted.

## The stages

```
python -m fbfit.cli harvest  [style ...]   # query the API, cache photographs
python -m fbfit.cli rectify  [style ...]   # detect the bracket, flatten it
python -m fbfit.cli stack    [style ...]   # illumination-flatten, align, average
python -m fbfit.cli review   [style ...]   # contact sheets to check by eye
```

Each writes into `$FBFIT_WORK/<style>/` (default `cad/fbfit/work/`), so any
stage can be re-run alone. Photo queries and downloads are cached.

**harvest** takes only `license == 'Y'` (Public Domain) photographs, and records
the photo id, photographer and trig for every image. Anything else is a
display-only licence to TUK, which does not cover deriving a printable model,
let alone a product. Provenance is kept so contributors can be credited.

**rectify** is deliberately high-precision and low-recall: there are thousands
of candidates and only a few hundred are needed, so anything doubtful is
discarded rather than repaired. A detection is accepted only if the flattened
image looks like a flush bracket, scored against the model's own geometry —
the keyhole pockets and staff slot are deep and shadowed, the plate face is
flat and lit. That test also settles the 180° ambiguity, since the opening
pattern is asymmetric top to bottom.

**stack** flattens each image's illumination (dividing out the slow lighting
gradient), then re-aligns every image to the running mean before averaging,
because residual detection error would otherwise soften the very edges the
tracing depends on. It emits two images:

- `mean.png` — the legend (`O S B M`, the broad arrow) resolved cleanly, because
  it is identical on every bracket of the style;
- `std.png` — where the stack *disagrees*, which is precisely where the number
  is. That localises the digit cells without anyone specifying them.

## Glyphs needed

Fourteen per style: `0`–`9` plus `O`, `S`, `B`, `M`. No `G` or `L` — those
series are wall brackets and do not occur on pillars.

## Status

Proven end to end on a real sample, and not yet good enough to trace from.

First run, `s-late`, 159 Public Domain photographs:

| Stage | Result |
|---|---|
| harvest | 160 candidates found, 159 cached (~5 min, mostly API round trips) |
| rectify | 13 accepted (8%) — all upright, correctly oriented, none false |
| stack | 11 survived alignment |

The average of those 11 resolves the keyhole pockets and the staff slot
crisply, and `O`, `S`, `B` and `M` are legible but soft. So the principle
holds: averaging really does recover the casting from photographs that
individually show mostly weather. Two things stand between that and a usable
glyph set.

**More images.** 8% of a 159-photo sample is 13. Several hundred per style are
wanted, which means harvesting a few thousand candidates — entirely feasible
(`s-late` alone has 4,289 brackets, and photo queries are now cached) but it is
an hour of API calls per style, not a minute.

**Registration, which is the real limit.** ECC finds corrections of 20–50 px —
4–10 mm on the plate — between one rectified bracket and another. That is the
detector not consistently locking on to the *same* rectangle: sometimes the
bead's outer edge, sometimes its crest, sometimes the recess in the pillar.
Averaging at that precision blurs exactly the edges tracing needs.

The fix is to stop registering photographs to each other and register each one
to **the model** instead: after the coarse rectification, search a small range
of affine corrections for the one that best aligns the image's dark regions
with the openings the CAD model says are there. That puts every image in true
plate coordinates rather than merely in agreement with its neighbours, and it
has a fixed, noise-free reference — unlike the current bootstrap, which has to
start from one arbitrary bracket.

Note also that ECC correlation between two *different* brackets tops out around
0.5 even when the alignment is perfect, since they are differently weathered and
carry different numbers. It is a convergence check here, not a quality measure;
an earlier version used it as a quality gate and threw away almost everything.
