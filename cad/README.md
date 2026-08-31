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
- **driver** — a hand tool to screw the plug in/out of the pillar, in three
  successive versions (`driver_v1` … `driver_v3`, each building on the last; see
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
│   ├─ driver_v1/          # plug driver tool, v1: the bare tool
│   │   ├─ params.py       # every driver dimension, provenance-tagged. EDIT THIS.
│   │   ├─ driver_v1.py    # ellipsoidal sawtooth-knurled disc + peg bores
│   │   └─ build.py        # driver_v1 recipe: run(*, threads, skip_stl)
│   ├─ driver_v2/          # v2 = v1 + a 4 mm hex key stored inside the body
│   │   ├─ params.py       # key channel / slot / magnet / O-ring dimensions
│   │   ├─ driver_v2.py    # build_driver_v1() + the key-storage cavities
│   │   └─ build.py        # driver_v2 recipe
│   └─ driver_v3/          # v3 = v2 + a pair of spare screws stashed in the top
│       ├─ params.py       # screw, stash bore sections, tap drill, placement
│       ├─ driver_v3.py    # build_driver_v2() + the two stash bores
│       └─ build.py        # driver_v3 recipe
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
venv/bin/python build.py driver_v3     # driver_v1 / driver_v2 / driver_v3
venv/bin/python build.py --step-only   # nominal STEP masters only
venv/bin/python build.py --fast        # no threads (quick dimensional check)

# Build/inspect one module directly (prints its volume + bounding box):
venv/bin/python -m models.plug.plug
venv/bin/python -m models.driver_v3.driver_v3
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
  0.10 mm, FDM 0.25 mm on the spider thread; the inner-plug/bore joint is
  allowed separately per member, see below). Tune after trial fits.
- Extra STLs are produced for each customised inner-plug top (see below), named
  `inner_plug_<preset>_<variant>.stl`.
- **`step/driver_v<n>.step`, `stl/driver_v<n>.stl`** — the driver tool, one pair
  per version (single solid each, no thread-clearance variants; the fit
  dimensions are the peg bore and, on v3, the stash tap drill).

### The FDM bore thread is not the brass thread

The STEP master and the **resin** STLs carry the real 14 TPI Whitworth bore
thread, so resin parts interchange with brass originals. The **FDM** STLs do
not: they use `FDM_BORE_JOINT`, a 4 mm-pitch 90° trapezoid, and mate only with
each other.

This is not a preference, it is printability. A V-form thread's flanks overhang
at **62.5° from vertical at every pitch** — depth and axial run both scale with
pitch, so coarsening it never helps — and 14 TPI Whitworth also asks for a
0.30 mm crest flat, narrower than one 0.42 mm extrusion, so the crest never
forms at all. The first FDM pair would not screw together for exactly this
reason, even though the CAD pair mates freely with 0.48 mm of clearance.

Assuming a **0.4 mm nozzle and 0.2 mm layers**, the replacement is sized so that
every feature is printable: 45° flanks (the steepest FDM holds unsupported,
putting the radial step per layer equal to one layer height), 0.8 mm — two
extrusions — at both the crest flat and the root gap, 1.2 mm deep, 20 layers per
turn. Change the nozzle or layer height and `FDM_BORE_JOINT.crest_flat` and
pitch should be revisited; a 0.6 mm nozzle would need roughly a 5 mm pitch.

The allowance is applied **once**, entirely to the external member
(`bore_clearance_external` 0.30, `bore_clearance_internal` 0). Both members of
this joint are printed, so allowing on each — which is right for the spider
joint, where only one member is printed — gave the assembled pair double the
intended slop. That is what let the inner plug tilt and cross-thread.

### The bore joint is allowed per member

Both members of the inner-plug/bore joint are printed, so its allowance is given
per member (`bore_clearance_external` on the shaft, `bore_clearance_internal` on
the bore) rather than once for the joint. Allowing the full figure on each — the
right thing for the spider joint, where only one member is printed — gives the
assembled pair double the intended slop.

Where the allowance sits is a design decision, not bookkeeping, because the
**resin** parts have to interchange with brass in both directions. Calipers on
the round-2 print showed the resin inner plug exactly 0.2 mm under the brass one
on diameter — precisely the 0.10 mm radial allowance the STL asked for — so
resin tracks the model faithfully and every fit here is a modelling choice.

The brass original puts its whole allowance on the female: the brass bore is cut
**0.26 mm** generous (37.5 mm minor against a 39.3 mm crest) and the shaft is
nominal. The resin variant now does the same, at 0.30 mm — the brass figure plus
a little for resin's surface texture, since 0.26 mm is an allowance for smooth
machined metal:

| Fit | Radial clearance | Engagement |
|-----|------------------|------------|
| printed shaft ↔ printed bore | 0.30 mm | 0.86 mm (74%) |
| brass shaft ↔ printed bore | 0.30 mm | 0.86 mm (74%) |
| printed shaft ↔ brass bore | 0.26 mm | 0.90 mm (78%) |

The round-2 print brackets that choice from both sides: at 0.20 mm the printed
pair needed PTFE and ten minutes of working in before it ran by hand, while
0.36 mm (printed shaft in a brass bore) ran freely. It is also well short of the
0.5 mm that let the FDM pair tilt and cross-thread.

The **spider joint keeps its 8 TPI Whitworth form** in every output: it has to
mate with a real pillar spider, so it is not ours to redraw. It carries the same
62.5° overhang, though with a 0.529 mm crest flat and 16 layers per turn it is
better placed than the bore thread was. It is untested against a real spider.

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

The driver exists in three versions. Each is a **superset of the one before** —
`driver_v2` calls `build_driver_v1()` and subtracts its extra cavities,
`driver_v3` calls `build_driver_v2()` and subtracts its own — so the body,
pegs, knurl and logo are described once, in v1, and every version inherits any
fix to them. Print whichever you want; they are separate build targets.

| Version | Adds | Package |
|---------|------|---------|
| **v1** | the bare tool: knurled elliptical knob + two glued steel pegs | `models/driver_v1/` |
| **v2** | a 4 mm hex key stored inside the body | `models/driver_v2/` |
| **v3** | spare screws in the top, a magnetic tray in the base, and a second pin spanner in the end for the *inner* plug | `models/driver_v3/` |

### v1 — the tool itself

`models/driver_v1/` is a **face/pin spanner** for screwing the plug in and out of
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
ergonomic estimates flagged `[E]` in `models/driver_v1/params.py` — iterate
there; no geometry code changes.

### v2 — the hex key lives in the tool

`models/driver_v2/` stores a **4 mm hex (allen) L-key** inside the body, so the
one tool carries what the job needs. The key is modelled as its own *cutter*: the
long arm slides down a horizontal Ø5 mm channel parallel to the major axis,
offset in Y so it passes clear of the left dowel bore; a swept round bend takes
it into a flat slot cut into the −X end, where the short arm comes to rest just
inside the elliptical rim. A **spherical finger scoop** at that end gives
purchase to pull it out.

Two retention options are modelled, both BOM items in their own pockets: a **Ø8
neodymium disc** let into the slot floor (its pocket pulled outboard so the disc
drops straight in past the slot wall), and an **O-ring gland** in the bore wall
near the mouth — a 4 × 1.5 mm NBR ring stands ~0.5 mm proud and grips the key's
across-corners as it passes. Set `oring_groove_dia <= bore_dia` to drop the
gland, or `magnet_dia` to zero out the magnet.

### v3 — screw stashes, a magnetic tray, and a second pin spanner

`models/driver_v3/` adds three things to v2: **spare-screw stashes** in the top
plateau, a **magnetic parts tray** in the base, and a **second pin spanner in the
+X end** that drives the *inner* plug. The first two are cut from opposite faces
and never meet — the stashes bottom out at z = 22 on the major axis, the tray's
magnet pocket tops out at z = 8.3 on the centreline.

Carrying the side pins reshaped the shared body: **45 mm thick instead of 40**,
with **squarer shoulders** and the **knurl faded out at both ends**. The plan
ellipse is untouched — Ø120 × Ø60, as before. v3 does not edit v1 to get this; it
hands `build_driver_v1` its own `DRIVER_V3` params, so v1 and v2 still build
byte-identical STLs.

#### Spare-screw stashes

It sinks two stashes into the flat top plateau,
on the major axis, one each side of the logo. Lose a spider shelf screw on a
windy summit and there is a spare in the tool that drove the plug out.

Each stash is one blind bore in **three coaxial sections**:

1. **Head recess** — Ø taken from `PLUG.clr_hole_r` (Ø9 mm), i.e. *the same hole
   the screw passes through on the real part*, read from the plug params at build
   time exactly as v1 reads the peg spacing, so the two cannot drift apart. It is
   **5 mm deep against a 4.8 mm head**, so a seated screw sits 0.2 mm *below*
   flush — nothing protrudes into the palm that grips the knob.
2. **Shaft hole** — Ø3.8 × 10 mm, printed plain and **tapped by hand after
   printing**. The screw then threads into its own stash and cannot rattle out
   with the tool upside-down in a bag. Ø3.8 is the tap drill (major − pitch) for
   *either* candidate thread: 4.6 − 0.80 = 3.80 for a 0.8 mm metric pitch,
   4.6 − 0.847 = 3.75 for 30 TPI. The two differ by 0.05 mm, below what an FDM
   hole resolves, so one printed hole suits both. (Ø4.6 at ~0.8 mm is also within
   a whisker of **2BA** — Ø4.70, 0.81 mm — which would be unsurprising on OS-era
   brass hardware.)
3. **Tap relief** — Ø5 × 8 mm, *wider than the screw's Ø4.6 crest*. A taper tap's
   first several threads are only partly formed; this gives that lead somewhere
   to run out, so full-form thread reaches the bottom of section 2 instead of
   petering out short. It doubles as tip clearance: the screw can never bottom
   before its head seats.

**Placement** is `stash_x = ±23 mm`, the midpoint of the clear corridor on the
top face — the embossed logo ends at x = 9.1 and the sighting groove starts at
x = 36.5 — which also puts the whole Ø9 recess (x = 18.5…27.5) on the **flat**
plateau, so its floor is a true flat counterbore and the tap starts square.
Underneath, the Ø5 relief passes 8 mm clear of the peg bore's epoxy keying
grooves and 5 mm clear of v2's hex-key channel, leaving 22 mm of floor.

Those clearances are all *derived* relationships between params owned by three
different modules, so `build_driver_v3` **re-checks every one at build time** and
raises rather than shipping a tool with a stash broken into the peg bore. Move
`stash_x`, deepen the relief or change the screw and it will tell you what it
fouls.

**BOM (in addition to v1/v2):** 2× spare spider shelf screw. **After printing:**
tap both shaft holes (0.8 mm / 30 TPI / 2BA — whichever the real screw gauges
as); the head recesses and relief need no work.

#### Magnetic base tray

A **53.7 × 45 × 5 mm elliptical** tray recessed into the flat base, echoing the
tool's own plan, with a **Ø8 × 3 mm disc magnet** epoxied into a pocket in the
middle of its roof, to hold the small ferrous oddments a plug swap generates.

**Only the minor axis is given; the major is derived** from the rule that
balances the tray in the base face — it should stand off the dowel pegs by the
same distance it stands off the tool's own edge on the minor axis. Both are
clearances measured edge to edge (tray wall to peg *bore*, tray wall to the
tool's Ø60 minor rim), so at minor = 45 the gap is 30 − 22.5 = **7.5 mm each
way** and the major falls out at 2 × (38.5 − 4.15 − 7.5) = **53.7 mm**. Deriving
it keeps that balance true through any later change to the body radius, the peg
spacing or the bore size — `_tray_axes` is the whole of it. The tray clears the
peg keying grooves by 6.2 mm and sits 11.7 mm below v2's key channel.

**Its shape is dictated by printing, not by taste.** The tool prints **base-down**
— smooth base, symmetric elliptical layer marks on top — so the tray is a cavity
whose roof the printer has to close *over air*, and it must do so without
support (support inside a 54 × 45 × 5 mm pocket is miserable to remove, and
would mar the face the magnet bonds to). Three rules follow:

- **The chamfers are lofted between ellipses, not scaled from a round cone.**
  This is the trap the elliptical tray sets. Scaling a circular cutter by the
  plan ratio scales its chamfer too, and a 45° cone stretched 1.19× in X comes
  out at **50° from vertical** — past the self-supporting limit, in the one
  direction nobody would think to check. Each chamfer instead shrinks *both*
  semi-axes by the same amount over the same height, so every point of the
  section moves inward by exactly that amount and the slope stays at or under 45°
  in every direction. Verified on the built solid: **1.00 in both the X and Y
  columns**, through both chamfers.
- **Chamfers, never fillets, on anything facing the plate.** A concave fillet
  between the tray wall and its roof sweeps through *every* overhang angle from
  0° to 90°, and the fully horizontal part lands exactly where it meets the roof.
  Worse, the slicer reads a fillet as a *sloped surface* rather than a bridge, so
  it gets none of the bridge flow / fan / anchoring treatment and simply droops.
  A 45° chamfer holds one constant, self-supporting angle. Ranked: **45° chamfer
  > sharp 90° corner > fillet** — the fillet is the worst of the three, which is
  the opposite of the usual instinct.
- **Every chamfer is 45° by construction** — its height equals its inward run, so
  no parameter edit can quietly produce an unprintable overhang.
- **The flat roof must bridge, and no chamfer removes that.** This is what the
  bigger tray costs: the roof is now **49.7 × 41.0 mm** where the old Ø35 tray
  gave Ø31. A slicer bridges the short way, so ~41 mm is the number that matters
  — long, but this is the inside of a tray and the roughness is invisible.
  `roof_chamfer` (2 mm) is the dial; raise it and the tray drafts toward a cone,
  shortening the bridge at the cost of tray volume.

The **magnet pocket's mouth chamfer** is the one that earns its keep twice. The
pocket opens as a hole in the middle of the roof's bridge layer, so its perimeter
is laid down in mid-air and sags inward — straight into the space the magnet
needs. The 0.5 mm × 45° chamfer puts that sagging loop at Ø9.3, half a millimetre
radially clear of the Ø8.3 bore, so droop cannot foul the magnet. It is also the
usual lead-in and glue fillet.

`build_driver_v3` checks the printability constraints as well as the geometric
ones, because an edit that turns a 45° chamfer into a 60° one still looks fine in
CAD and droops on the plate.

The magnet pocket stays **round** — the magnet is. **BOM:** 1× Ø8 × 3 mm disc
magnet + structural epoxy (the pocket is Ø8.3 × 3.3, a clearance fit for an epoxy
annulus, same convention as the dowel bores).
**Slicing:** supports **off**; nothing in the part needs them.

#### Inner-plug pin spanner (+X end)

The inner plug has its own pin-spanner pattern — two Ø6.7 × 8 mm blind holes in
its top face, 27 mm apart (`PLUG.ip_side_spacing`). Two **Ø6 steel pins** glued
into the tool's +X end drop into them, so the same tool that breaks the big
64.7 mm spider joint also turns the inner plug out of the bore. Held for that job
the tool is a 120 mm lever turned about its own major axis; the grip is the
knurled waist, which the end fade leaves at full depth.

Three things had to change to carry them, and each is worth stating because none
was optional:

- **The pins are stacked vertically, and that costs the tool's profile.** A pair
  spaced 27 mm *across* the tool cannot work: at the +X end the plan ellipse has
  narrowed so fast that each bore's outer flank leaves the solid 3.7 mm before
  reaching the surface — the bores break out sideways. Stacked vertically instead,
  they need **33.3 mm of straight knurl band** (27 spacing + Ø6.3 bore) to sit in,
  plus a wall top and bottom. v1's 40 mm body has 25 mm of band, so the bores
  break clean out of it.

  **45 mm** buys 5 mm of that; the other 9 has to come out of the shoulders,
  which shrink from 8 mm of rounded base edge and 7 mm of sculpted top to **3 mm
  of each**. Band z = 3…42, bores at z = 9 and 36, 2.85 mm of wall at the band
  ends, thickening to ~4 mm as each bore runs inboard. That is the real price of
  the side pins: the plan ellipse is untouched, but the profile is noticeably
  squarer — a thick knurled disc with softened edges rather than a discus.

  Two knock-on adjustments. With only 3 mm of rise the sculpt spline bulges
  **0.88 mm proud of the plateau** — a raised ridge round the logo — because it
  still has 16 mm of radius to cover; widening `plateau_r` to 22 shortens that run
  and kills it (0.05 mm, on a par with v1's own 0.015). But `plateau_r` also sets
  the logo's size, so `logo_fill` drops to 0.541 to hold the badge at exactly the
  size it is on v1 and v2 (22.0 × 0.541 = 14.0 × 0.85).
- **Each mouth opens through a spherical dish, not a chamfer.** This one is
  subtle and it decides the shape of the whole end. The +X tip has a plan radius
  of curvature of just 15 mm and is *narrower than the bore*: the body is 6.3 mm
  wide only **0.33 mm** back from the tip. Over that last stretch the bore is
  wider than the nose it is entering, so slivers of nose survive between the
  cavity and the flank — feather edges, and unprintable besides.

  A sphere of radius 9 mm centred out on the bore axis, biting 2 mm deep at the
  tip, fixes it at the root. It **swallows the entire region where the bore is
  wider than the nose**, and its own rim meets the flank at a shallow angle all
  round. Measured on the built solid: **0 of 1331 sample points** in that region
  survive, and the cut deepens at a slope of ~0.97 across the rim — a **136°
  included edge**. What is left is a shallow oval dimple at each pin, blending
  into the flank. It is the same trick that blunts the finger scoop's rim at the
  other end of the tool.

  On a 45 mm body the dish is boxed in vertically as well: it reaches
  `sqrt(2rd - d²)` up and down the nose, and there is only 6.0 mm of straight band
  above each bore before the sculpted top takes over. r = 9 reaches 5.66 and keeps
  0.34 mm of daylight; r = 10 reaches exactly 6.00, tangent to that junction —
  the sort of exact touch v2's `mesh_gap` exists to avoid. `build_driver_v3`
  checks it.

  **A plain chamfer also works, if it is big enough**, and "big enough" is not
  what intuition suggests: the cone has to reach the *corner* of the breakout
  region, where a point sits at the full bore radius in y and z at once —
  r·√2 = 4.45 mm from the axis. Measured, **1.0 mm leaves 8 slivers** in a
  1331-point sample where **2.0 mm leaves none**. So `mouth_dish_r = 0` with
  `mouth_chamfer = 2.0` is a supported alternative, and it is checked the same
  way; it just gives a **121°** rim against the dish's 136°.

  Truncating the nose to a flat is a third route, and throws in a bearing pad
  square to the pins, but it costs the elliptical silhouette and 3 mm of bore
  depth. `nose_flat_back` still does it, and defaults to 0.
- **Bore depth is 14 mm, and that is not a free choice.** The +X dowel peg bore's
  keying grooves reach x = 43.45 — the lower pin bore passes straight over them —
  so the blind end has to stop at x = 46.0, 2.55 mm clear. The dish opens the
  outer ~1.2 mm, leaving ~12.8 mm of full-diameter grip on the pin (2.1× the pin
  diameter, against 2.5× for v1's pegs). The load here is transverse shear **in
  the layer plane** — turning about the major axis pushes each pin along ±Y —
  which is the direction printed plastic bears best. Two keying grooves rather
  than v1's three: over a 14 mm bore, three 1.5 mm rings run together into one
  counterbore with no shoulders to key on.

Vents run to whichever face is nearer — the lower pin's drops to the flat base,
the upper pin's rises to the sculpted top and surfaces inside the sighting groove
alongside the existing peg vents.

`build_driver_v3` checks three properties of the dish, because swallowing the
breakout region is necessary but not sufficient — the dish's own rim then has to
be blunt, which is the entire point of using one, and it has to fit inside the
straight band. A dish that clears the breakout region by under 0.5 mm is refused,
so is one whose rim falls below 130°, and so is one that reaches into the
sculpted top or the base edge.

**BOM:** 2× Ø6 mm silver-steel / dowel pin ≈ 21 mm long (14 mm embedded +
6.5 mm protruding) + structural epoxy. The protrusion bottoms 1.5 mm short in the
plug's 8 mm holes, so the pins work in shear, not as struts.

#### No knurl at the ends, and what that fixed

The sawtooth teeth now **fade out toward both ends** — full depth to |x| = 30,
gone by |x| = 45, smoothstepped between over about 2.5 teeth so the knurl dies
away rather than stopping. This is not cosmetic. Every feature that breaks the
rim at an end — the two pin mouths, and at the −X end the key flare, the
short-arm slot and the finger scoop — was truncating whatever teeth it landed on
into thin sharp spikes. The furthest-inboard of them is the finger scoop at
|x| = 46.2, which is what sets the 45 mm threshold.

(The pin mouths sit at |x| = 60, so they need the fade as much as anything at the
other end.) The fade is driven by `knurl_fade_start` / `knurl_fade_end` /
`knurl_crest_out` on
`DriverParams`, all **defaulting to no-ops** so v1 and v2 are unaffected.
`knurl_crest_out` lifts the cutting wheel's crests just outside the body: since
the knurl is made by *intersecting* that wheel with the body, a crest that pokes
out gets clipped back to the body's own surface. That does two jobs at once — the
faded end caps stay exactly, smoothly elliptical instead of picking up the
wheel's polygon facets, and every tooth crest loses its knife edge for a narrow
flat of the true surface.

Alongside it the **finger scoop became a shallow cap** — a Ø40 sphere backed off
to bite 6 mm deep, giving a Ø28.6 dish whose rim meets the surface at 46°
(a 134° edge) instead of the hemisphere's square 90° — and the **slot mouth lost
its four corner points**, by filleting the slot *cutter* before subtracting it.
That last trick matters: OCCT fillets a `Box` happily and refuses the same edges
once they are spline-bounded cavity edges in the finished solid.

**One edge is not fixed.** The short-arm slot's two long mouth edges, where its
flat floor and ceiling break the curved end, stay square. OCCT refuses to fillet
them — of the 32 edges in that region it declines 19, including every one that
matters, one at a time, at 0.8, 0.6 and 0.4 mm — and no cutter shape chamfers them
either, because a chamfer needs a plane to follow and the slot cuts across the
ellipse's nose, so its mouth wanders over ~6 mm in x between the middle of the
opening and its ends. That is a deburring job on the print, or a differently
built slot in a later version.

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
| `bore_joint` (inner plug ↔ bore) | 39.3 mm | Whitworth 55° | 14 TPI (1.814 mm) |
| `FDM_BORE_JOINT` (**FDM prints only**) | 39.3 mm | trapezoid 90° | 4.0 mm (6.35 TPI) |
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
