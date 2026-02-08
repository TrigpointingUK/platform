# Trig Pillar Animation — Workflow Plan

## End Goal

A video of a camera flying down towards the trigpoint, orbiting it, flying
through a sighting hole and out the other side, then pulling back.  The first
part is photorealistic; the view then transitions to transparent tinted solids
to reveal the internal structure.

---

## 1. Materials & Textures (do first)

Everything else depends on being able to see what the final result looks like.
You can't meaningfully judge lighting or camera angles until the surfaces look
right.

### Concrete
- Originally whitewashed, now heavily degraded — patchy white over beige
  concrete.
- Weather-stained, dirty, with possible lichen/algae patches.
- Needs: base colour variation (procedural noise mixing white and beige),
  roughness map, bump/normal map for fine surface texture.

### Brass (spider, plug, inner plug, centre marks, flush bracket, loops)
- Aged and dirty — dull brown, not shiny yellow.
- Patina variation: darker in crevices, slight green verdigris in sheltered
  areas.
- Needs: base colour shift toward brown/olive, roughness variation, subtle
  normal map for surface wear.

### Steel
- **Sighting tubes & centre pipe**: severely rusted — heavy orange/brown rust,
  flaking, pitting.
- **Screws & peg**: aged and dirty but not badly corroded — dark grey with
  surface grime, slight surface oxide.
- Needs: two separate steel materials (rusted vs aged), or one material with
  per-object variation.

### Wood (upper & lower boxes)
- Stained dark, showing early signs of rotting.
- Grain texture visible but degraded.
- Needs: wood grain (procedural or image), dark staining, soft/spongy patches.

### Approach
- **Procedural textures** (noise, Musgrave, Voronoi in Blender's shader nodes)
  for resolution-independent, tuneable results.
- **Reference photographs** of actual trigpoints used as visual targets to
  match against — not as direct texture maps.
- Hybrid: if a particular effect is hard to achieve procedurally (e.g. lichen
  patches, rust flaking), layer in image textures from CC0 libraries
  (ambientCG, Poly Haven).

---

## 2. Render Engine & Lighting (second)

### Render Engine
- Switch to **Cycles** for photorealistic sections (path-traced global
  illumination, accurate reflections).
- EEVEE can be used for fast preview iterations.

### Lighting
- **HDRI environment map** — provides realistic sky, ambient light, and
  reflections in brass surfaces.  Use an overcast British-looking outdoor HDRI
  (e.g. from Poly Haven).
- **Sun light** — keep existing, align direction with HDRI.
- **Remove fill light** — HDRI provides natural fill.
- **Sighting-hole point light** — keep for interior illumination through tubes.

### Ground Plane
- Add a ground plane (grass/earth/gravel) so the pillar isn't floating.
- Even a simple textured plane with a subtle displacement sells the scene.

---

## 3. Camera Path & Animation (third)

### Shot Segments

| Segment | Frames (approx) | Duration @ 24fps | Description |
|---------|-----------------|-------------------|-------------|
| **A — Approach** | 1–120 | 5 s | Camera descends from above, looking down at pillar |
| **B — Orbit** | 121–360 | 10 s | Circular orbit at mid-height, steady distance |
| **C — Through-shot** | 361–480 | 5 s | Camera flies in through East sighting hole, through box interior, out West hole |
| **D — Pull-back** | 481–600 | 5 s | Camera pulls away and rotates to 3/4 view |
| **E — X-ray transition** | 601–840 | 10 s | Materials crossfade to transparent tinted solids; slow orbit to show internals |

**Total: ~35 seconds @ 24fps = 840 frames**

### Implementation
- Use an **Empty** at the pillar centre as a tracking target.
- Animate camera along a **Bezier curve path** (or keyframed positions with
  smooth interpolation).
- For the orbit: parent camera to an Empty, animate the Empty's Z rotation
  through 360°.
- For the through-shot: animate camera location along a straight line through
  the sighting tube axis (Y axis, at z = 0.117 m).  May need a narrow FOV or
  artistic licence to "fit" through the 44 mm bore.
- Use **Track To** constraint on camera pointing at the central Empty for
  smooth look-at behaviour.

---

## 4. X-ray / Transparent Materials (fourth)

### Transparent Material Set
Create a second set of materials — one per component — that are transparent
with an appropriate tint:

| Material | Tint Colour |
|----------|-------------|
| Concrete | Semi-transparent grey |
| Wood | Semi-transparent amber |
| Brass | Semi-transparent gold |
| Steel | Semi-transparent blue-grey |

### Transition Method
- **Keyframed Mix Shader**: blend between photorealistic shader and
  transparent/glass shader, with the mix factor animated from 0 → 1 over a
  few seconds.
- **Alternative**: render the X-ray section as a separate render pass and
  composite them together — easier and gives more control in post.

---

## 5. Compositing & Final Render (last)

- Set up render output: PNG image sequence (not video file — crash recovery).
- Frame rate: 24 fps.
- Resolution: 1920 × 1080 (or 3840 × 2160 for 4K).
- Test-render individual frames from each segment to check exposure, focus,
  timing.
- Composite the photorealistic and X-ray segments with a transition.
- Encode final PNG sequence to video (FFmpeg / H.264 or H.265).

---

## Material Tuning Guide

All materials are built procedurally using Blender's shader nodes.  Parameters
are defined as local variables at the top of each `make_*_material()` function
in `trig_pillar.py`.

### Quick Start — Interactive Tuning

1. Run the script in Blender to generate the model.
2. Select an object (e.g. the Pillar).
3. Open the **Shader Editor** panel.
4. You'll see a labelled node graph.  Each node's label describes its role.
5. To preview what any node is producing:
   - Enable the **Node Wrangler** add-on (Edit → Preferences → Add-ons).
   - **Ctrl+Shift+Click** any node to preview its output on the object.
6. Adjust values directly in the node properties — changes show immediately
   in Material Preview or Rendered viewport mode (press **Z** to switch).

> **Note:** Changes made in the Shader Editor are lost when you re-run the
> script.  Once you're happy with values, copy them back into the script's
> tuneable parameters section.

### Concrete (`make_concrete_material`)

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| `WHITEWASH_COVERAGE` | 0.35 | Fraction of surface with remaining whitewash (0 = bare, 1 = fully painted) |
| `WHITEWASH_EDGE` | 0.15 | Softness of whitewash edges (0 = crisp chips, 0.5 = very soft) |
| `WHITEWASH_SCALE` | 3.0 | Pattern size (smaller = larger patches) |
| `WHITEWASH_COLOUR` | (0.85, 0.83, 0.78) | Off-white paint colour |
| `CONCRETE_COLOUR` | (0.52, 0.48, 0.43) | Exposed concrete colour |
| `STAIN_STRENGTH` | 0.25 | Max darkening from rain streaks (0 = none, 0.5 = very dark) |
| `STAIN_SCALE` | 4.0 | Streak width (higher = narrower, more frequent) |
| `STAIN_STRETCH` | 8.0 | Vertical elongation (higher = longer continuous streaks) |
| `ROUGHNESS_BASE` | 0.85 | Average surface roughness |
| `ROUGHNESS_VAR` | 0.10 | Roughness variation (±) |
| `BUMP_STRENGTH` | 0.15 | Fine surface bump intensity |
| `BUMP_SCALE` | 25.0 | Bump detail scale |

### Brass (`make_brass_material`)

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| `BASE_COLOUR` | (0.25, 0.18, 0.06) | Main tarnished brass colour |
| `PATINA_COLOUR` | (0.10, 0.09, 0.03) | Darker patina in sheltered areas |
| `PATINA_AMOUNT` | 0.40 | How much patina variation (0 = uniform, 1 = heavily varied) |
| `PATINA_SCALE` | 8.0 | Patina pattern size |
| `METALLIC` | 0.55 | Metallicness (tarnish reduces this) |
| `ROUGHNESS_BASE` | 0.65 | Average roughness (dull surface) |
| `ROUGHNESS_VAR` | 0.15 | Roughness variation |
| `BUMP_STRENGTH` | 0.10 | Surface wear bump intensity |
| `BUMP_SCALE` | 30.0 | Bump detail scale |

### Rusted Steel (`make_rusted_steel_material`)

Used for: sighting tubes, centre pipe, angle irons.

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| `RUST_COLOUR_A` | (0.45, 0.18, 0.04) | Primary rust (orange) |
| `RUST_COLOUR_B` | (0.20, 0.08, 0.02) | Secondary rust (dark brown) |
| `RUST_SCALE` | 6.0 | Rust pattern scale |
| `ROUGHNESS` | 0.95 | Surface roughness (very rough for corroded metal) |
| `BUMP_STRENGTH` | 0.50 | Pitting/flaking bump intensity |
| `BUMP_SCALE` | 20.0 | Pitting detail scale |

### Aged Steel (`make_aged_steel_material`)

Used for: screws, anti-rotation peg.

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| `BASE_COLOUR` | (0.12, 0.12, 0.13) | Dark grey steel base |
| `GRIME_COLOUR` | (0.06, 0.04, 0.03) | Dark brown grime/dirt |
| `GRIME_AMOUNT` | 0.30 | Grime coverage (0 = clean, 1 = fully grimy) |
| `GRIME_SCALE` | 10.0 | Grime pattern scale |
| `METALLIC` | 0.70 | Metallicness |
| `ROUGHNESS` | 0.55 | Surface roughness |
| `BUMP_STRENGTH` | 0.08 | Surface texture bump |

### Wood (`make_wood_material`)

| Parameter | Default | What It Does |
|-----------|---------|-------------|
| `BASE_COLOUR` | (0.15, 0.08, 0.03) | Dark stained wood base |
| `GRAIN_COLOUR` | (0.22, 0.13, 0.05) | Lighter grain bands |
| `ROT_COLOUR` | (0.04, 0.03, 0.02) | Dark rot/decay patches |
| `GRAIN_SCALE` | 15.0 | Wood grain scale |
| `GRAIN_DISTORTION` | 4.0 | How wavy/organic the grain is |
| `ROT_AMOUNT` | 0.20 | Rot coverage (0 = no rot, 1 = fully decayed) |
| `ROT_SCALE` | 5.0 | Rot patch pattern scale |
| `ROUGHNESS` | 0.90 | Surface roughness |
| `BUMP_STRENGTH` | 0.20 | Grain/rot bump intensity |

### Noise Texture Controls (general)

These appear in many of the node graphs:

| Control | What It Does |
|---------|-------------|
| Scale | Pattern size — **smaller value = larger features** |
| Detail | Fractal octaves — more = finer grain added |
| Roughness | Small-octave contribution — 0 = smooth, 1 = grainy |
| Distortion | Warps the pattern — 0 = regular, higher = more organic |

### ColorRamp Tips

The ColorRamp node maps a 0–1 noise value to a colour gradient:
- Moving stops **closer together** = sharper transition (paint-chip edges).
- Moving stops **further apart** = softer blend (gradual weathering).
- The **left stop position** sets where the effect begins.
- The **right stop position** sets where the effect is at full strength.

---

## File & Asset Organisation

```
Blender/Hotine/
├── trig_pillar.py          # model generator script
├── animation-workflow.md   # this file
├── textures/               # image textures (HDRI, rust maps, etc.)
├── reference/              # photographs of actual trigpoints
└── renders/                # output frames and final video
```

