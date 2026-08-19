# Trig-pillar CAD — parametric model collection

A collection of parametric [build123d](https://build123d.readthedocs.io/) models
for 3D-printable hardware for Ordnance Survey "Hotine" triangulation pillars. Two
components so far, with more expected:

- **plug** — the brass **plug** and **inner plug** from the top of a pillar; a
  printable replacement assembly for pillars whose original brass plug has been
  stolen. Unlike the Blender render model (`../Blender/Hotine/trig_pillar.py`),
  where the threads are bump-maps with no helix angle, this has **true helical
  threads** with correct flank form and lead — suitable for a functional print or
  a milling/casting master.
- **driver** — a hand tool to screw the plug in/out of the pillar (see
  [Plug driver tool](#plug-driver-tool)).

Each component is a self-contained package under `models/`; shared machinery
(threads, engraving, export, filesystem paths) lives in `common/`; a thin
top-level `build.py` orchestrates. Output is written to shared `step/` and `stl/`
directories with component-prefixed filenames.

## Layout

```
cad/
├─ common/                 # shared library (imported as common.*)
│   ├─ paths.py            # CAD_DIR / REPO_ROOT / STEP_DIR / STL_DIR anchors
│   ├─ specs.py            # ThreadSpec (generic, model-agnostic)
│   ├─ threads.py          # helical thread helpers (external shafts; tapped holes)
│   ├─ engraving.py        # generic mechanisms: arc-text, SVG relief, QR
│   └─ export.py           # validate() + watertight-STL export
├─ models/
│   ├─ plug/               # plug + inner-plug component
│   │   ├─ params.py       # every plug dimension, provenance-tagged. EDIT THIS.
│   │   ├─ plug.py         # outer plug (rings, bore, holes, cotter hole, lettering)
│   │   ├─ inner_plug.py   # inner plug (thread, blind holes, locking screw, top)
│   │   ├─ lettering.py    # "TRIANGULATION STATION" / "ORDNANCE SURVEY" arcs
│   │   ├─ top_surfaces.py # inner-plug top treatments (flat / logo / QR) + presets
│   │   └─ build.py        # plug recipe: run(*, threads, skip_stl)
│   └─ driver/             # plug driver tool
│       ├─ params.py       # every driver dimension, provenance-tagged. EDIT THIS.
│       ├─ driver.py       # ellipsoidal sawtooth-knurled disc + peg bores
│       └─ build.py        # driver recipe: run(*, threads, skip_stl)
├─ build.py                # orchestrator (build all, or named components)
├─ step/  stl/             # generated output (reproducible)
└─ requirements.txt  venv/
```

## Quick start

```bash
cd cad
virtualenv -p python3.12 venv          # python3.12: OCP has wheels for it
venv/bin/python -m pip install -r requirements.txt

# Run everything from the cad/ root (it must be on sys.path for the packages).
venv/bin/python build.py               # every component: STEP masters + STLs
venv/bin/python build.py plug          # just the named component(s)
venv/bin/python build.py driver
venv/bin/python build.py --step-only   # nominal STEP masters only
venv/bin/python build.py --fast        # no threads (quick dimensional check)

# Build/inspect one module directly (prints its volume + bounding box):
venv/bin/python -m models.plug.plug
venv/bin/python -m models.driver.driver
```

> Python 3.12 is used deliberately: `cadquery-ocp` (the OpenCASCADE binding)
> ships binary wheels for 3.12 but not yet for the system's 3.14, and this repo
> has no `python3.12-venv`, hence `virtualenv` rather than `python -m venv`.

## Output

- **`step/plug_assembly.step`** — the *master*: nominal geometry, zero print
  clearance, with both parts (`Plug` and `InnerPlug`) as separate named solids
  in their assembled position (inner plug seated in the bore, tops flush). This
  is the accurate archival model; treat it as the source of truth and never bake
  a print allowance into it.
- **`stl/<part>_resin.stl`, `stl/<part>_fdm.stl`** — one printable mesh per part
  per process, with a radial thread clearance applied for a running fit (resin
  0.10 mm, FDM 0.25 mm — starting points, tune after trial fits at the print
  shop).
- Extra STLs are produced for each customised inner-plug top (see below), named
  `inner_plug_<preset>_<variant>.stl`.
- **`step/driver.step`, `stl/driver.stl`** — the driver tool (single solid, no
  thread-clearance variants; its only fit dimension is the peg bore).

## Customising the inner-plug top

The inner plug's top is the one exposed face, so it can be personalised.
`top_surfaces.py` is a small **library** of engraved treatments plus named
**presets**:

- A treatment *type* is a function `(part, *, z_top, radius, clearance, **opts)
  -> part` registered in `TREATMENTS`. Built in: `flat` (no-op), `logo`
  (multi-level colour-mapped relief of an SVG, engraved *or* embossed via a
  `raised` option), `qr` (a `segno`-generated QR code engraved as recessed
  modules).
- A `TopSurface` *preset* binds a type to concrete options + a filename label,
  in `PRESETS`. Shipped presets: `flat`, `tuk-logo` (engraved `res/TUK-Logo.svg`,
  0.9 mm), `tuk-logo-emboss` (the same logo raised 0.9 mm proud), `trig-5169-qr`
  (QR to `https://trigpointing.uk/trigs/5169`).

**Select at build time** by editing `INNER_TOPS` in `build.py` (the list of
presets to render), or in code via `build_inner_plug(..., top="tuk-logo")`.

**Add an option**: write a treatment function, add it to `TREATMENTS`, and add a
`TopSurface` to `PRESETS`.

Notes:
- The **logo** reuses the Blender flush-bracket colour→relief table (bright green
  deepest/tallest … highlights shallowest, black outline skipped). Engraved
  (`raised=False`) or embossed (`raised=True`). A couple of near-white highlight
  paths yield degenerate faces and are skipped automatically; each boolean is
  volume-checked so a failed cut/union can never drop the body.
- The **QR** engraving depends on `segno` (added to `requirements.txt`). An
  engraved (recessed) QR reads by shadow/contrast, so it is **not guaranteed to
  scan** on bare metal — depends on the print finish and lighting. There is no
  embossed QR: fine raised modules are too fragile for rough handling.

## Plug driver tool

`models/driver/` is a **face/pin spanner** for screwing the plug in and out of
the pillar spider. Two steel pegs drop into the plug's two upper-ring clearance
holes (Ø9 mm, 77 mm apart — the spider-screw pattern) so the whole plug can be
rotated; that is the stiff 64.7 mm 8 TPI joint, the one that seizes.

- **Steel pegs, not printed.** At a firm ~40 N·m removal torque each peg carries
  ~520 N in transverse shear; a printed 8 mm peg shears across its layer lines
  and the printed pocket blows out. The pegs are **2× Ø8 mm silver-steel / dowel
  pins glued into deep (25 mm) blind bores** in the base; steel there sees an
  order of magnitude of margin. Only the bores are modelled — the dowels are a
  BOM item (the same convention the plug uses for its cotter pin / locking screw).
- **Glued, not pressed.** The bores are a **clearance fit** (Ø8.3 for an Ø8.0
  dowel) bonded with structural epoxy — an interference press would wedge the
  printed layers apart, and a press fit in plastic relaxes over time. The load is
  transverse *shear*, not pull-out, so the bore just has to stop the dowel
  wobbling. Each bore carries keying features for the epoxy: **annular grooves**
  down the wall (the cured epoxy keys to the plastic so the plug can't slide
  out), a **mouth chamfer** (dowel lead-in + a glue fillet that spreads the
  high-stress bearing load at the hole mouth), and a **thin vent** from the blind
  end to the top face so pushing the dowel in can't hydraulic-lock on trapped
  epoxy — surplus weeps out the top. All tuneable in `params.py`
  (`peg_bore_dia`, `peg_groove_*`, `peg_mouth_chamfer`, `peg_vent_dia`).
- **Directional sawtooth grip = easier loosening.** The body is a thick
  ellipsoidal ("discus") knob — a **2:1 ellipse in plan** (≈ Ø120 × Ø60 × 40 mm),
  its major axis running through the two pegs and extending ~20 mm beyond them
  for grip leverage and bulk around the bores — with a large **sawtooth** knurl
  round the rim: each tooth is a long shallow ramp and a short near-radial steep
  face. The teeth are spaced at **equal arc length** round the ellipse (not equal
  angle), so every tooth is the same physical size rather than bunched at the
  ends and stretched down the sides. Twisting
  anticlockwise (loosening, right-hand thread) the fingers catch the steep faces
  → high grip/torque; twisting clockwise to tighten they run down the ramps and
  slip → capped torque. So the tool gives more mechanical advantage for loosening
  than tightening, with **no separate wrench or breaker bar**. The peg spacing
  and mating-hole size are read from the plug params, so they cannot drift; the
  handedness (`catch_ccw`) assumes a right-hand spider thread — flip it if a
  measurement shows left-hand.
- **Sculpted top.** A flat central plateau carries an **embossed TrigpointingUK
  logo**, blending out and down a smooth sculpted shoulder to just above the
  knurl — a rounded, *sculpted* form, not a bevelled edge. A shallow **sighting
  groove** runs along the major axis from each vent hole out to the rim; line the
  two grooves up by eye with the plug's two holes when offering the tool up, to
  drop the pegs in first time.

**BOM:** 2× Ø8 mm silver-steel / dowel pin ≈ 35 mm long (25 mm embedded +
10 mm protruding) + structural epoxy. **Print** in a tough material
(PETG / ASA / PA) at high infill, **axis vertical**, so the peg-bore walls take
the tangential load within the layer plane rather than across it.

**Assembly:** scuff and degrease the dowel ends (IPA); butter them with epoxy
(don't fill the bore — let the vent do its job); insert. For alignment, use the
plug itself as a jig — pass the epoxied dowels through the plug's Ø9 mm holes so
they cure parallel and at the right protrusion, resting on a ~10 mm spacer;
**wax / release-agent the plug first** so you don't bond the tool to it. Wipe the
epoxy that weeps from the top vents. (Nylon prints resist epoxy — use a
methacrylate / structural-acrylic adhesive, or knurl the dowel ends, if printing
in PA.)

Body size/height, tooth count/depth, ramp/steep split and the flat radii are
ergonomic estimates flagged `[E]` in `models/driver/params.py` — iterate there;
no geometry code changes.

## Coordinate frame

Each part is modelled standalone: **z = 0 at the part's lowest face, +z up**,
revolved about the Z axis. (This differs from the pillar-assembly frame in the
render model, where the plug sits ~1.17 m up.) The driver uses the same
convention: z = 0 at its flat base, pegs protruding downward (−z).

## Thread specifications (measured)

All three joints were measured on a real plug as **Whitworth (55°)** form; the
pitch is the thread-gauge TPI reading (`pitch_mm = 25.4 / TPI`):

| Joint (`ThreadSpec`) | Major Ø | Form | Pitch |
|----------------------|---------|------|-------|
| `spider_joint` (plug ↔ spider) | 64.7 mm | Whitworth 55° | 8 TPI (3.175 mm) |
| `bore_joint` (inner plug ↔ bore) | 38 mm | Whitworth 55° | 14 TPI (1.814 mm) |
| `locking_screw_joint` | ~4 mm | Whitworth 55° | 32 TPI (0.794 mm) — 5/32″ BSW |

Major diameters are the dimensioned values (the gauge gives form + TPI, not
diameter). The Whitworth form is a **truncated-flat approximation**: correct
55° flanks and 0.6403·p depth, with the rounded crest/root approximated by
p/6 flats. The mating members of each joint are generated from the same nominal
so they fit by construction; per-process running clearance is applied at build
time (`STL_VARIANTS`). Refine `params.py` if a trial fit needs it.

### Provenance tags (in `params.py`)

- `[D]` Dimensioned — from a drawing or measured original (trusted).
- `[E]` Estimated — a plausible guess, **not** confirmed against a real part.
- `[S]` Spec — a nominal engineering-standard value.

## Known simplifications (this iteration)

- **Scope is the two brass bodies only** — the loose cotter pin and the locking
  screw (separate fasteners) are not yet modelled; their *holes* are.
- The fine locking-screw thread (32 TPI) is modelled in the **STEP master** but the
  printable **STLs get a plain tap-drill hole** instead — that thread is too
  fine to print cleanly, so it is meant to be hand-tapped after printing
  (`build_inner_plug(locking_screw_thread=False)`).
- The inner plug's 1 mm top chamfer sits on the thread's minor diameter (a
  short lead-in), rather than on the full crest diameter.
- Thread ends are faded (no partial teeth) for print/manufacturing robustness.
- The engraved lettering uses **DejaVu Sans** as a stand-in; the exact OS cast
  face has not been identified. Font, size, depth, radius and arc spans are all
  tuneable in `lettering.py`.

## Design notes

- **Internal threads are tapped, not glued on.** Unioning thin helical teeth
  onto a bore wall is numerically unstable in OCCT (it can collapse to an empty
  solid). Instead we drill to the minor diameter and *subtract* an
  external-thread "tap" tool — the way a machinist cuts a thread. See
  `threads.py`.
- **The radial locking-screw hole** has a smooth Ø6.3 mm counterbore for its
  first 8.3 mm, then a 45° taper into the threaded section. The thread is
  confined to the plain-drilled wall between the taper and a short run-out at
  the central hole, so it only meets plain cylinder walls -- the same clean case
  as the bore. The initial drill is a touch **under** the minor radius (a face
  exactly coincident with the tap core makes OCCT's boolean silently no-op for
  the rotated tool, leaving an unthreaded hole), and the radial tool is oriented `Rot(0,0,bearing) *
  Rot(0,90,0)` (a single `Rot(0,90,bearing)` spins it while still on the Z axis
  and ignores the bearing).
- Every exported part is checked with OCCT's `BRepCheck_Analyzer` and asserted
  to be a single solid; micro-slivers from thread booleans are dropped
  (`keep_largest_solid`).
- **STLs are guaranteed gap-free.** OCCT's mesher, on the fine rotated locking-screw
  thread, emits a few zero-area triangles and non-manifold "pinch" edges
  (surfaces meeting along an edge -- not leaks); `build.py` strips the slivers,
  fills any face OCCT skipped with `trimesh`, and asserts the mesh has **no open
  edges** before writing, so a genuine hole fails the build. A few pinch edges
  are tolerated (slicers handle them). The STEP master is the exact B-rep.
- **Mesh fineness is set by an absolute chord deflection**, `STL_LINEAR_TOL` in
  [`common/export.py`](common/export.py) — the furthest the flat mesh may stray
  from the true surface, currently 0.005 mm. Because it is absolute it is
  radius-adaptive: the Ø92 mm upper ring gets ~300 facets while a Ø6 mm hole
  needs only ~77. Note this means **not** using build123d's `export_stl`, which
  hardcodes OCCT's `isRelative=True` and so scales the deflection by each edge's
  own size — that makes the facet count independent of radius, and was why the
  first printed prototype came out with a visibly faceted 42-sided upper ring
  (a 6.9 mm chord, 129 µm off true). Raising the *angular* tolerance is not the
  fix: it is equally radius-blind, and tightening it inflates the lettering and
  logo tops by an order of magnitude for no visible gain, so it is left at 0.3
  rad purely as a backstop for curves too small to divide by chord length.
