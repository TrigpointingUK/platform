# Trig-pillar plug assembly — parametric CAD

A parametric [build123d](https://build123d.readthedocs.io/) model of the brass
**plug** and **inner plug** from the top of an Ordnance Survey "Hotine"
triangulation pillar. The goal is a 3D-printable replacement plug assembly for
pillars whose original brass plug has been stolen.

Unlike the Blender render model (`../Blender/Hotine/trig_pillar.py`), where the
threads are bump-maps with no helix angle, this model has **true helical
threads** with correct flank form and lead — suitable for a functional print or
a milling/casting master.

## Layout

| File | What it is |
|------|-----------|
| `params.py` | Every dimension as a documented variable, with a provenance tag. **Edit this** as real measurements arrive. |
| `threads.py` | Helical thread helpers (external shafts; internal threads cut by a "tap" tool). |
| `plug.py` | The outer plug (three rings, bore, holes, cotter hole, lettering). |
| `inner_plug.py` | The inner plug (threaded cylinder, blind holes, locking-screw hole, top-surface treatment). |
| `lettering.py` | Engraved "TRIANGULATION STATION" / "ORDNANCE SURVEY" arcs. |
| `top_surfaces.py` | Library of engraved inner-plug top treatments (flat / logo / QR) + named presets. |
| `build.py` | Builds, validates and exports the STEP assembly + per-process STLs. |
| `step/`, `stl/` | Generated output (git-ignored; reproducible). |

## Quick start

```bash
cd cad
virtualenv -p python3.12 venv          # python3.12: OCP has wheels for it
venv/bin/python -m pip install -r requirements.txt

venv/bin/python build.py               # STEP masters + FDM/resin STLs
venv/bin/python build.py --step-only   # nominal STEP masters only
venv/bin/python build.py --fast        # no threads (quick dimensional check)
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

## Coordinate frame

Each part is modelled standalone: **z = 0 at the part's lowest face, +z up**,
revolved about the Z axis. (This differs from the pillar-assembly frame in the
render model, where the plug sits ~1.17 m up.)

## Thread specifications (measured)

All three joints were measured on a real plug as **Whitworth (55°)** form; the
pitch is the thread-gauge TPI reading (`pitch_mm = 25.4 / TPI`):

| Joint (`ThreadSpec`) | Major Ø | Form | Pitch |
|----------------------|---------|------|-------|
| `spider_joint` (plug ↔ spider) | 63.8 mm | Whitworth 55° | 8 TPI (3.175 mm) |
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
