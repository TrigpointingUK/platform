# Flush bracket — caliper sheet

Every dimension in `params.py` carries a provenance tag. **None of them has yet
been measured on a real casting.** The `[D]` values were dimensioned from
*photographs* by the Blender render model, scaled against an assumed plate
width; the `[E]` values are estimates, several read off a single perspective
photograph. This sheet lists what to measure, in priority order, with the
parameter each number lands in.

Take everything on **one bracket** if possible, and note its number — the
lettering (and possibly more) varies by era, see `styles.py`.

Notation: `W` across the plate, `H` up the plate, `D` into the plate.

---

## A. Scale — do these first, everything else is relative to them

| # | Measurement | Parameter | Current | Tag |
|---|---|---|---|---|
| A1 | Plate width, **inside** the beading | `w` | 85.5 | [D]* |
| A2 | Plate height, **inside** the beading | `h` | 172.0 | [D]* |
| A3 | Overall width, **over** the beading | — (check: `w + 2*bead_r`) | 95.5 | derived |
| A4 | Overall height, over the beading | — (check: `h + 2*bead_r`) | 182.0 | derived |
| A5 | Beading radius (half its width where it meets the plate) | `bead_r` | 5.0 | [D]* |
| A6 | How far the beading stands proud of the plate face | — (should equal `bead_r`) | 5.0 | derived |

A3/A4 are the cross-check: published figures of 90 x 175 mm disagree with the
render model's 85.5 x 172, and it is not clear whether the published number is
the plate or the overall size. Measuring both settles it.

---

## B. The broad arrow — the current work

The arrow is one solid mass with two V-grooves cut into it. Measure the mass
first, then the grooves.

`ba_w_top`, `ba_w_bot` and `ba_h` all describe the **front face** — the flat
top of the relief — not the footprint on the plate. The footprint is wider,
and the model derives it from these by the draft. Measure across the crisp top
edges of the raised face, not where it meets the plate.

| # | Measurement | Parameter | Current | Tag |
|---|---|---|---|---|
| B1 | Front face width across its **top** edge | `ba_w_top` | 14.6 | **[E]** |
| B2 | Front face width across its **bottom** edge | `ba_w_bot` | 31.3 | [D]* |
| B3 | Front face height, top edge to bottom edge | `ba_h` | 36.1 | [D]* |
| B4 | How far the arrow stands proud of the plate face | `ba_relief` | 4.5 | [D]* |
| B5 | Arrow top edge down from the **inner** edge of the top bead | `ba_below_bead` | 52.8 | [D]* |
| B5a | How far down the arrow the plate surface closes in beside it — i.e. where the flank plane first meets plate | `hole_front_bot_frac` | 0.55 | **[E]** |

B5a is the one that varies between brackets: 1.0 puts it right at the bottom of
the arrow (North Ockendon), ~0.55 just over halfway down (the reference photo).
Express it as a fraction of B3, or just give the height above the arrow's
bottom edge and note B3 alongside.

### The grooves

| # | Measurement | Parameter | Current | Tag |
|---|---|---|---|---|
Each groove is deepest at the bottom edge and shallows to nothing at its upper
end, so **every width and depth below must say where it was taken.**

| # | Measurement | Parameter | Current | Tag |
|---|---|---|---|---|
| B6 | Groove width where it breaks the front face, **at the bottom edge** | `ba_ch_width` | 4.0 | **[E]** |
| B7 | Groove depth **at the bottom edge** — does it reach the plate? | (assumed = `ba_relief`) | 4.5 | **[E]** |
| B8 | How far below the arrow's top edge each groove first appears | `ba_ch_top_drop_frac` x `ba_h` | 7.2 | **[E]** |
| B9 | Groove width and depth **at mid-length** — to check the taper | (assumed linear) | 2.0, 2.25 | **[E]** |
| B10 | Gap between the two grooves where they start (the ridge between them) | `ba_ch_top_sep` | 3.0 | **[E]** |
| B11 | Distance from the arrow's centreline to each groove **at the bottom edge** | `ba_ch_bot_frac` x `ba_w_bot`/2 | 5.5 | **[E]** |

B7 is the one that most changes the look. The model assumes the two faces of
each groove meet exactly at the plate at the bottom edge — a sharp V with
nothing flat between them. If there is a flat floor, or a radius, its width is
the number to take.

B9 tests the assumption that depth and width both grow **linearly** from
nothing at the top to full at the bottom (which follows from the V keeping a
constant half-angle). If the mid-length readings are not close to half the
bottom ones, the profile is curved and that is a change of geometry, not of a
number.

### The ledge (the sloping shelf above the arrow)

| # | Measurement | Parameter | Current | Tag |
|---|---|---|---|---|
The shelf is the **top surface of the same wedge the arrow is the front of** —
not a separate slab. Its widths and depth are all derived from features it runs
between, so there is little left to measure directly; what is worth measuring
is whether those derivations hold.

| # | Measurement | Parameter | Current | Tag |
|---|---|---|---|---|
| B12 | Width of the rectangular opening the shelf runs into | `hole_w` | 31.4 | [D]* |
| B13 | **Is the shelf level, or does it slope?** If it slopes, the rise front to back | not modelled | level | **missing** |
| B14 | Angle of the arrow's flank from the plate normal — a *check*, see below | derived | 18.3 deg | derived |

The model takes the shelf's front edge as the arrow's top edge (B1), its back
edge as the full opening width (B12), and its depth as `ba_relief +
total_plate_d`. All three are constraints rather than free numbers, so B1 and
B12 are worth confirming carefully — they now determine the flank as well.

B14 is the cross-check that ties it together. Because the flank is one plane
running from the arrow's bottom back to the ledge, its draft is **not free**:
it is fixed by B1, B12 and the depth. If a measured flank angle disagrees with
`atan((hole_w/2 − ba_w_top/2) / (ba_relief + total_plate_d))`, then one of
those three is wrong, and the flank angle says by how much.

B13 remains a **gap in the model**: the shelf is level. If the real one slopes,
that is new geometry, not a changed number.

---

## C. Casting draft

| # | Measurement | Parameter | Current | Tag |
|---|---|---|---|---|
| C1 | Width of a letter's stroke at its **base**, and at its **top** | `relief_draft_deg` | 13 deg | **[E]** |
| C2 | Same for the arrow's **bottom** edge | (shares `relief_draft_deg`) | 13 deg | **[E]** |

Easiest on a straight stroke — the upright of `B`, or the arrow's outer edge.
Two caliper readings, base and top, plus the relief height (B4), give the
angle directly. The current value is calibrated to the top of a letter being
about half the area of its base; C1 replaces that inference with a measurement,
and will also show whether the letters and the arrow's bottom edge are drafted
alike. The arrow's *flanks* are not in this section — their draft is derived
from the ledge (see B14), not set here.

---

## D. Lettering — lower priority, and era-dependent

Each letter is individually placed and sized. Measure on a bracket whose
number you record.

| # | Measurement | Parameter | Current |
|---|---|---|---|
| D1 | `O` and `S`: bounding width, height | `os_w`, `os_h` | 16.0, 24.0 |
| D2 | `O` to `S` centre-to-centre | `os_sep` | 56.0 |
| D3 | Top of `O` down from the inner edge of the top bead | `os_below_bead` | 48.4 |
| D4 | `B`: width, height; gap from its outer edge to the bead's inner edge; top below the bottom of `O` | `b_w`, `b_h`, `b_gap_from_bead`, `b_below_os` | 16.7, 24.9, 4.9, 13.6 |
| D5 | `M`: the same four | `m_w`, `m_h`, `m_gap_from_bead`, `m_below_os` | 17.6, 24.5, 2.9, 14.7 |
| D6 | Letter relief height | `let_relief` | 4.5 |
| D7 | Number: digit height, stroke width, baseline above the bottom bead, digit pitch | `num_cap_h`, `num_margin_bottom` | 22.0, 12.0 |
| D8 | On a **BsM** bracket (3200–3699): the middle `S` — width, height, and its baseline against `B` and `M` | `bsm_s_w_frac`, `bsm_s_h_frac` | derived |

---

## E. Keyholes and the back — lowest priority

| # | Measurement | Parameter | Current |
|---|---|---|---|
| E1 | Keyhole slot width, cuboid height, depth into the plate | `kh_w`, `kh_h`, `kh_d` | 16.9, 28.0, 12.1 |
| E1a | Depth of the rounded trough **at the back wall** vs at the mouth | `kh_scoop_angle_deg` | 0 (equal) |
| E2 | Gap between the two slots | `kh_gap` | 21.1 |
| E3 | Slot top below the top bead's inner edge | `kh_below_bead` | 5.0 |
| E4 | Bridging rib: height, thickness, edge radius, top below the slot top | `rib_h`, `rib_d`, `rib_bevel`, `rib_below_slot_top` | 11.5, 5.0, 2.0, 11.6 |
| E5 | Total plate depth, front face to back | `total_plate_d` | 20.9 |
| E6 | Front plate depth (front face to the step at the back, if visible) | `near_d_frac` | 6.97 |

E1a is the easy way to pin the trough's form without measuring an angle: at 0°
the trough is a cylinder and is exactly as deep at the back as at the mouth; at
~35° it has run out completely by the back wall. Anything between is
`atan(rise / kh_d)` where `rise` is the difference of the two depths.

The keying bar and anchor (`bar_*`, `anchor_*`) are buried in the concrete on a
fitted bracket and can only be measured on a salvaged one.

---

\* `[D]` here means "dimensioned from photographs by the render model", not
from calipers. Re-tag as genuinely `[D]` once measured.
