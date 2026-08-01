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
| `inner_plug.py` | The inner plug (threaded cylinder, blind holes, grub-screw hole, top-surface treatment). |
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

## ⚠️ Accuracy status — read before relying on fit

The overall shape and the `[D]`-tagged sizes are believed accurate (they match
the render model's dimensioned values). **The threads are not yet verified.**
Specifically:

- **Thread pitch** for both joints is an estimate (`[E]`) derived from the
  render model, not a gauge reading.
- **Thread form** is assumed ISO metric (60°). A real OS plug of this era may
  well be **Whitworth (55°, rounded crests/roots)** or another form — this is
  unconfirmed.
- The inner-plug / bore joint nominal is driven to Ø38 so the two mate *by
  construction*; the render model's Ø37.8 inner-plug figure is treated as the
  same joint.

So today's model is **correct-by-construction and dimensionally consistent**,
but a printed pair is not guaranteed to screw into a *real* pillar until the
threads are measured. When you have calipers + a thread gauge on a real plug (or
an OS drawing), update the `ThreadSpec`s and any `[E]` values in `params.py` and
re-run `build.py`. No geometry code needs to change.

### Provenance tags (in `params.py`)

- `[D]` Dimensioned — from a drawing or measured original (trusted).
- `[E]` Estimated — a plausible guess, **not** confirmed against a real part.
- `[S]` Spec — a nominal engineering-standard value.

## Known simplifications (this iteration)

- **Scope is the two brass bodies only** — the loose cotter pin and the grub
  screw (separate fasteners) are not yet modelled; their *holes* are.
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
- **The radial grub-screw hole** is a plain passage drilled the whole way (so
  its cuts through the surface and the central blind hole are clean), with the
  thread confined to the plain-drilled wall between a short run-out at the
  central hole and a shallow lead-in at the mouth. Keeping the thread clear of
  both the central hole and the *external* thread means it only meets plain
  cylinder walls -- the same clean case as the bore. Two subtleties: the drill
  is a touch **under** the minor radius (a face exactly coincident with the tap
  core makes OCCT's boolean silently no-op for the rotated tool, leaving an
  unthreaded hole), and the radial tool is oriented `Rot(0,0,bearing) *
  Rot(0,90,0)` (a single `Rot(0,90,bearing)` spins it while still on the Z axis
  and ignores the bearing).
- Every exported part is checked with OCCT's `BRepCheck_Analyzer` and asserted
  to be a single solid; micro-slivers from thread booleans are dropped
  (`keep_largest_solid`).
- **STLs are guaranteed gap-free.** OCCT's mesher, on the fine rotated grub
  thread, emits a few zero-area triangles and non-manifold "pinch" edges
  (surfaces meeting along an edge -- not leaks); `build.py` strips the slivers,
  fills any face OCCT skipped with `trimesh`, and asserts the mesh has **no open
  edges** before writing, so a genuine hole fails the build. A few pinch edges
  are tolerated (slicers handle them). The STEP master is the exact B-rep.
