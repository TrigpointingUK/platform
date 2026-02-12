"""
Ordnance Survey Trig Point (Hotine Pillar) — Blender 4.3 Model Generator
=========================================================================

Generates a complete parametric 3D model of a standard OS triangulation
pillar with all internal and external components.

Usage:
    Open in Blender's Text Editor (Scripting tab) and click "Run Script"
    or from the command line:
        blender --python trig_pillar.py

Dimensions marked [D] are from the OS specification diagram (Fig 2.2).
Dimensions marked [E] are estimated from proportions / photographs.
All measurements are in metres.
"""

import bpy
import bmesh
import math
import os
import random
from mathutils import Vector, Matrix


# =====================================================================
# MEASUREMENTS
# =====================================================================

# --- Main Pillar ---
PILLAR_HEIGHT       = 1.190     # [D] 119 cm above ground
PILLAR_TOP_HW       = 0.180     # [D] 36 cm / 2 — half-width at top
PILLAR_BTM_HW       = 0.305     # [D] 61 cm / 2 — half-width at base
BEVEL_RADIUS        = 0.025     # [E] ~1" chamfer on vertical edges
BEVEL_SEGMENTS      = 1         # 1 = flat 45° mitre, >1 = rounded arc

# --- Centre Pipe ---
CP_OUTER_R          = 0.038     # [E] 3" OD / 2
CP_INNER_R          = 0.032     # [E] ~2.5" ID / 2
# (Centre pipe now ends at spider underside — no protrusion above pillar top)

# --- Sighting Tubes ---
ST_OUTER_R          = 0.025     # [E] 2" OD / 2
ST_INNER_R          = 0.022     # [E] ~1.75" ID / 2
ST_TILT             = math.radians(2)   # [E] 2° drainage tilt
ST_Z                = 0.117     # [E] aimed at top of dome / base of spike

# --- Upper Wooden Box (internal) ---
UB_HW               = 0.127     # [E] ~10" outer / 2
UB_HEIGHT           = 0.203     # [E] ~8"
UB_WALL             = 0.015     # 15 mm timber
UB_BASE_Z           = 0.000     # box base sits on top of the base slab

# --- Concrete Fill in Upper Box ---
FILL_HEIGHT         = 0.096     # [E] top 5 mm below bottom of sighting-tube holes

# --- Upper Centre Mark ---
UCM_R               = 0.03175   # [D] 2.5" widest flange dia / 2
UCM_DISC_H          = 0.005     # [E] disc thickness (5 mm, both discs)
UCM_SPIKE_D         = 0.005     # [E] spike diameter (5 mm)
UCM_STEM_H          = 0.072     # [E] stem zone height incl. fillets (72 mm)
UCM_FILLET_R        = 0.005     # [E] fillet radius at stem-disc junctions (5 mm)
UCM_BASE_H          = 0.008     # [E] base disc height (8 mm)

# --- Base Slab (Foundation) ---
BASE_TOP_HW         = 0.380     # [E] ~2'6" / 2 — wider overhang around pillar
BASE_BTM_HW         = 0.457     # [D] 3'0" / 2
BASE_HEIGHT         = 0.305     # [E] ~12" thick

# --- Angle Irons ---
AI_LEG              = 0.038     # [E] 1½" × 1½"
AI_THICK            = 0.005     # [E] 3/16"
AI_TOTAL_H          = 0.600     # [E] total length spanning junction

# --- Spider ---
SPIDER_ANNULUS_INNER_R = 0.0465  # [D] 93 mm inner dia / 2
SPIDER_ANNULUS_OUTER_R = 0.065   # [D] 130 mm outer dia / 2
SPIDER_INNER_BEVEL     = 0.003   # [D] 3 mm 45° bevel to top (inner edge)
SPIDER_OUTER_BEVEL     = 0.001   # [D] 1 mm bevel to top (outer edge)
SPIDER_THICK           = 0.020   # [D] 20 mm
SPIDER_LOWER_BORE_R    = 0.032   # [D] 64 mm lower bore dia / 2 (forms shelf)
SPIDER_SCREW_R         = 0.002   # [D] 4 mm threaded screwholes / 2
SPIDER_SCREW_SPACING   = 0.077   # [D] 77 mm apart (diametrically opposite)
SPIDER_ARM_LEN         = 0.115   # [D] 115 mm from inner dia of annulus
SPIDER_ARM_W           = 0.030   # [D] 30 mm
SPIDER_GROOVE_W        = 0.010   # [D] 10 mm wide, 90° V-groove
SPIDER_FILLET_R        = 0.020   # [D] 20 mm fillet at arm-annulus junction

# --- Brass Loops ---
LOOP_R              = 0.015     # [D] 30 mm loop dia / 2
LOOP_WIRE_R         = 0.002     # [D] 4 mm wire dia / 2
LOOP_DEPTH          = 0.003     # [D] top of loop 3 mm below pillar surface
LOOP_RECESS_L       = 0.070     # [E] 70 mm total recess length (tangential)
LOOP_RECESS_W       = 0.020     # [E] 20 mm U-trough width (radial)
LOOP_RECESS_D       = 0.015     # [D] 15 mm recess depth
LOOP_POS_R          = 0.120     # [D] 120 mm from pillar centre

# --- Plug ---
PLUG_UPPER_R        = 0.046     # [D] 92 mm upper ring dia / 2
PLUG_UPPER_H        = 0.006     # [D] 6 mm thick
PLUG_UPPER_BEVEL    = 0.003     # [D] 3 mm 45° chamfer on top edge
PLUG_MIDDLE_R       = 0.0319    # [D] ~63.8 mm dia / 2 (fraction under 64 mm)
PLUG_MIDDLE_H       = 0.009     # [D] 9 mm thick
PLUG_LOWER_R        = 0.023     # [D] 46 mm dia / 2
PLUG_LOWER_H        = 0.009     # [D] 9 mm thick
PLUG_BORE_R         = 0.019     # [D] 38 mm inner dia / 2
PLUG_BORE_BEVEL     = 0.001     # [D] 1 mm chamfer on top of bore (matches inner plug)
PLUG_HOLE_R         = 0.0045    # [D] 9 mm clearance holes in upper ring / 2
PLUG_HOLE_SPACING   = 0.077     # [D] 77 mm apart (matches spider screwholes)

# --- Inner Plug ---
IPLUG_R             = 0.0189    # [D] ~37.8 mm dia / 2 (fraction under 38 mm)
IPLUG_H             = 0.023     # [D] 23 mm thick
IPLUG_BEVEL         = 0.001     # [D] 1 mm chamfer on top edge
IPLUG_HOLE_R        = 0.003     # [D] 6 mm blind holes / 2
IPLUG_CENTRE_DEPTH  = 0.016     # [D] centre hole 16 mm deep
IPLUG_SIDE_DEPTH    = 0.008     # [D] side holes 8 mm deep
IPLUG_SIDE_SPACING  = 0.027     # [D] side holes 27 mm apart

# --- Steel Fixings ---
SCREW_SHAFT_R       = 0.00195   # [D] <4 mm shaft dia / 2
SCREW_SHAFT_H       = 0.010     # [D] 10 mm long shaft
SCREW_HEAD_R        = 0.0035    # [D] 7 mm head dia / 2
SCREW_HEAD_H        = 0.005     # [D] 5 mm head height
SCREW_SOCKET_R      = 0.0025    # [D] 3 mm allen socket dia / 2
SCREW_SOCKET_DEPTH  = 0.003     # [D] 3 mm deep
SCREW_SPACING       = 0.077     # [D] 77 mm apart (matches spider/plug)

PEG_R               = 0.0015    # [D] 3 mm peg dia / 2
PEG_LENGTH          = 0.030     # [D] 30 mm long
PEG_OVERHANG        = 0.010     # [D] 10 mm outside plug annulus

# --- Flush Bracket ---
FB_W                = 0.100     # [D] 100 mm wide
FB_H                = 0.180     # [D] 180 mm high
FB_D                = 0.008     # [D] plate thickness behind beading
FB_BEAD_R           = 0.005     # [D] 5 mm semicircular beading radius
FB_SETBACK          = 0.023     # [D] bead peak ~10 mm behind pillar face at top
FB_BTM_Z            = 0.172     # [D] 30 mm above sighting tube top edge
FB_RECESS_MARGIN    = 0.020     # [E] recess outer edge this far beyond plate edge

# --- Flush Bracket Keying Structure ---
FB_REAR_H_FRAC     = 0.90      # [E] rear plate height as fraction of front
FB_BAR_H            = 0.010     # [D] keying bar height (10 mm)
FB_BAR_DEPTH        = 0.025     # [D] keying bar protrusion behind rear plate (25 mm)
FB_ANCHOR_H         = 0.035     # [D] anchor block height (35 mm)
FB_ANCHOR_DEPTH     = 0.010     # [D] anchor block depth (10 mm)

# --- Flush Bracket Logo Relief ---
LOGO_SVG            = 'TUK-Logo.svg'   # SVG file in ../../res/ relative to script
LOGO_RELIEF         = 0.0048    # [E] maximum relief height (4.8 mm, bright green UK)
LOGO_MARGIN         = 0.014     # [E] 8 mm margin inside plate edges
LOGO_V_STRETCH      = 1.30      # [E] vertical stretch factor (20 % taller)
LOGO_BTM_OFFSET     = 0.020     # [E] bottom of logo 10 mm above plate bottom
LOGO_BEVEL_FRAC     = 0.10      # [E] bevel width as fraction of layer relief
LOGO_BEVEL_SEGS     = 1         # [E] bevel segments (1 = flat chamfer, 2+ = rounded)

# --- Lower Wooden Box ---
LB_HW               = 0.127     # [E] ~10" / 2
LB_HEIGHT           = 0.102     # [E] ~4"
LB_WALL             = 0.025     # [E] 1"

# --- Lower Block ---
LBLOCK_HW           = 0.152     # [D] 1'0" / 2
LBLOCK_H            = 0.305     # [E] ~12"

# --- Lower Centre Mark ---
# Below-ground components reuse UCM stem/fillet/base dimensions.
# Above-ground dimensions derived from the shared base disc.
LCM_CYL_H          = 0.003     # [E] cylinder thickness (3 mm)
LCM_PUNCH_R        = 0.0014    # [E] punch mark radius (1.4 mm); depth = radius (45°)

# --- Hilltop Terrain ---
TERRAIN_RADIUS      = 6.0       # [E] radius of the grassy dome (metres)
DOME_HEIGHT         = 1.10      # [E] height drop from dome centre to edge (metres)


# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def clear_scene():
    """Delete everything in the scene."""
    if bpy.data.objects:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
    # Purge orphan data
    for attr in ('meshes', 'materials', 'cameras', 'lights', 'curves'):
        data_block = getattr(bpy.data, attr)
        for item in list(data_block):
            if item.users == 0:
                data_block.remove(item)


def make_material(name, rgb, metallic=0.0, roughness=0.5):
    """Create a Principled BSDF material."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return m


def assign(obj, material):
    """Assign material to object, replacing any existing."""
    obj.data.materials.clear()
    obj.data.materials.append(material)


def activate(obj):
    """Deselect all, then select and activate obj."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def smooth(obj):
    """Apply angle-based smooth shading."""
    activate(obj)
    try:
        bpy.ops.object.shade_smooth_by_angle()
    except (AttributeError, RuntimeError):
        bpy.ops.object.shade_smooth()


def boolean_cut(target, cutter, operation='DIFFERENCE', solver='EXACT'):
    """Apply a boolean modifier to target using cutter, then remove cutter.

    The EXACT solver is used by default — it uses exact arithmetic and
    produces clean, predictable geometry.  FAST is available as a fallback
    but produces messier triangulation and potential artefacts.

    After applying, normals are recalculated so that subsequent booleans
    on the same target mesh have clean, consistent geometry to work with.
    """
    activate(target)
    mod = target.modifiers.new("_bool", 'BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    mod.solver = solver
    bpy.ops.object.modifier_apply(modifier="_bool")
    bpy.data.objects.remove(cutter, do_unlink=True)

    # Recalculate normals for reliability of any subsequent booleans
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')


def make_frustum(name, btm_hw, top_hw, height, base_z=0.0,
                 bevel_r=0.0, bevel_n=4):
    """
    Create a tapered square prism (frustum).

    If bevel_r > 0 the four vertical edges get rounded corners
    with bevel_n arc segments each.  Origin is at the centre of
    the bottom face.

    Parameters
    ----------
    btm_hw : float   — half-width at the bottom (z = base_z)
    top_hw : float   — half-width at the top   (z = base_z + height)
    height : float   — height of the frustum
    base_z : float   — Z coordinate of the bottom face
    bevel_r : float  — radius of the rounded vertical edges
    bevel_n : int    — number of arc segments per corner
    """
    bm = bmesh.new()

    def ring(hw, z):
        """Create a ring of verts for one horizontal cross-section."""
        if bevel_r > 0 and bevel_r < hw:
            r = bevel_r
            verts = []
            if bevel_n <= 1:
                # Flat 45° chamfer — octagonal cross-section.
                # Two vertices per corner: where the chamfer meets each
                # adjacent face.  Going counter-clockwise.
                pts = [
                    ( hw,      hw - r),  ( hw - r,  hw),      # +X +Y
                    (-hw + r,  hw),      (-hw,      hw - r),  # -X +Y
                    (-hw,     -hw + r),  (-hw + r, -hw),      # -X -Y
                    ( hw - r, -hw),      ( hw,     -hw + r),  # +X -Y
                ]
                for x, y in pts:
                    verts.append(bm.verts.new((x, y, z)))
            else:
                # Multi-segment rounded bevel (arc approximation)
                centres = [
                    (hw - r,  hw - r),      # corner 0: +X +Y
                    (-(hw - r),  hw - r),    # corner 1: -X +Y
                    (-(hw - r), -(hw - r)),  # corner 2: -X -Y
                    (hw - r, -(hw - r)),     # corner 3: +X -Y
                ]
                for ci, (cx, cy) in enumerate(centres):
                    a0 = ci * math.pi / 2
                    for j in range(bevel_n):
                        a = a0 + (math.pi / 2) * j / bevel_n
                        x = cx + r * math.cos(a)
                        y = cy + r * math.sin(a)
                        verts.append(bm.verts.new((x, y, z)))
            return verts
        else:
            return [
                bm.verts.new((hw,  hw, z)),
                bm.verts.new((-hw,  hw, z)),
                bm.verts.new((-hw, -hw, z)),
                bm.verts.new((hw, -hw, z)),
            ]

    bv = ring(btm_hw, base_z)
    tv = ring(top_hw, base_z + height)
    n = len(bv)

    # Bottom face — reversed so normal points -Z (downward)
    bm.faces.new(bv[::-1])
    # Top face — normal points +Z (upward)
    bm.faces.new(tv)
    # Side quads
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bv[i], bv[j], tv[j], tv[i]])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    return obj


def make_tube(name, outer_r, inner_r, depth, loc=(0, 0, 0), segs=32):
    """Create a tube (hollow cylinder) using bmesh — no booleans needed.

    Constructs four sets of quad faces directly:
      outer wall, inner wall (bore), top annulus, bottom annulus.
    The bore is guaranteed to be open.
    """
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    half = depth / 2

    # Four vertex rings: top-outer, top-inner, bottom-outer, bottom-inner
    rings = {}
    for label, r, z in [
        ('to', outer_r,  half),
        ('ti', inner_r,  half),
        ('bo', outer_r, -half),
        ('bi', inner_r, -half),
    ]:
        verts = []
        for i in range(segs):
            angle = 2 * math.pi * i / segs
            v = bm.verts.new((r * math.cos(angle), r * math.sin(angle), z))
            verts.append(v)
        rings[label] = verts

    bm.verts.ensure_lookup_table()

    for i in range(segs):
        j = (i + 1) % segs
        # Outer wall — normals point outward
        bm.faces.new([rings['to'][i], rings['to'][j],
                       rings['bo'][j], rings['bo'][i]])
        # Inner wall (bore) — normals point inward (toward centre)
        bm.faces.new([rings['ti'][j], rings['ti'][i],
                       rings['bi'][i], rings['bi'][j]])
        # Top annulus — normals point up
        bm.faces.new([rings['to'][j], rings['to'][i],
                       rings['ti'][i], rings['ti'][j]])
        # Bottom annulus — normals point down
        bm.faces.new([rings['bo'][i], rings['bo'][j],
                       rings['bi'][j], rings['bi'][i]])

    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = loc
    activate(obj)
    return obj


def subdivide_mesh(obj, cuts=3):
    """Subdivide all edges of a mesh to add geometry for roughness."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def roughen_mesh(obj, amount, seed=42, protect_top=True, protect_bottom=False):
    """
    Add random displacement to mesh vertices to simulate rough concrete.

    Vertices on the top face (and optionally bottom) are kept in place
    so the surface remains flat where concrete was poured / levelled.
    """
    rng = random.Random(seed)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()

    max_z = max(v.co.z for v in bm.verts)
    min_z = min(v.co.z for v in bm.verts)
    eps = 0.0005

    for v in bm.verts:
        if protect_top and abs(v.co.z - max_z) < eps:
            continue
        if protect_bottom and abs(v.co.z - min_z) < eps:
            continue
        v.co.x += rng.uniform(-amount, amount)
        v.co.y += rng.uniform(-amount, amount)
        v.co.z += rng.uniform(-amount, amount)

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def pillar_hw_at(z):
    """Interpolate pillar half-width at height z above base."""
    t = max(0.0, min(1.0, z / PILLAR_HEIGHT))
    return PILLAR_BTM_HW + (PILLAR_TOP_HW - PILLAR_BTM_HW) * t


# =====================================================================
# PROCEDURAL MATERIAL BUILDERS
# =====================================================================
#
# Each function below creates a full PBR material using Blender's shader
# nodes.  All texturing is procedural — resolution-independent and seamless
# on any geometry, no UV unwrapping needed.
#
# HOW TO TUNE MATERIALS
# ---------------------
# 1. Run the script to generate the model with default settings.
# 2. Select an object (e.g. the Pillar) and open the Shader Editor.
# 3. You'll see the node graph.  Ctrl+Shift+Click any node to preview
#    its output in the viewport (requires the Node Wrangler add-on).
# 4. To adjust:
#    - Edit the TUNEABLE PARAMETER values in the function below and
#      re-run the script, OR
#    - Adjust values directly in the Shader Editor (faster for
#      interactive tuning, but changes won't persist across re-runs).
# 5. Use Material Preview or Rendered viewport shading (Z key) to see
#    results in real time.
#
# NOISE TEXTURE CONTROLS
# ----------------------
# Scale       — pattern size (smaller value = LARGER features)
# Detail      — number of fractal octaves (more = finer grain)
# Roughness   — contribution of smaller octaves (0 = smooth, 1 = grainy)
# Distortion  — warps the pattern (0 = regular, higher = organic)
#
# COLORRAMP TIPS
# --------------
# The ColorRamp node maps a 0–1 value to a colour gradient.
# - Moving stops CLOSER together = sharper transition
# - Moving stops FURTHER apart   = softer blend
# - The LEFT stop's POSITION sets "where does the effect begin"
# - The RIGHT stop's POSITION sets "where is the effect at full strength"

def _new_node(tree, node_type, location=(0, 0), label=""):
    """Helper: create a shader node at the given position with optional label."""
    n = tree.nodes.new(node_type)
    n.location = location
    if label:
        n.label = label
    return n


def make_concrete_material():
    """Weathered concrete with patchy whitewash and rain staining.

    TUNEABLE PARAMETERS
    -------------------
    Whitewash layer:
      WHITEWASH_COVERAGE  (0.0–1.0)  How much whitewash remains.
                                      0.0 = bare concrete, 1.0 = fully painted.
                                      Default: 0.35
      WHITEWASH_EDGE      (0.0–0.5)  Transition softness at paint edges.
                                      0.0 = crisp paint chips, 0.5 = very soft.
                                      Default: 0.15
      WHITEWASH_SCALE     (float)    Pattern size for paint patches.
                                      Smaller = larger patches.
                                      Default: 3.0
      WHITEWASH_COLOUR    (R,G,B)    The whitewash paint colour.
                                      Default: (0.85, 0.83, 0.78)

    Concrete base:
      CONCRETE_COLOUR     (R,G,B)    Exposed concrete colour.
                                      Default: (0.52, 0.48, 0.43)

    Rain staining:
      STAIN_STRENGTH      (0.0–1.0)  Max darkening from rain streaks.
                                      0.0 = no staining, 0.5 = very dark.
                                      Default: 0.25
      STAIN_SCALE         (float)    Width/frequency of streaks.
                                      Higher = narrower, more frequent.
                                      Default: 4.0
      STAIN_STRETCH       (float)    Vertical elongation of streaks.
                                      Higher = longer continuous vertical streaks.
                                      Default: 8.0

    Surface texture:
      ROUGHNESS_BASE      (0.0–1.0)  Average surface roughness.
                                      Default: 0.85
      ROUGHNESS_VAR       (0.0–0.3)  Roughness variation (±).
                                      Default: 0.10
      BUMP_STRENGTH       (0.0–2.0)  Fine surface bump intensity.
                                      Default: 0.15
      BUMP_SCALE          (float)    Bump detail scale.
                                      Default: 25.0
    """
    # ── Tuneable values (edit these) ──────────────────────────────
    WHITEWASH_COVERAGE = 0.40
    WHITEWASH_EDGE     = 0.15
    WHITEWASH_SCALE    = 5.0
    WHITEWASH_COLOUR   = (0.45, 0.42, 0.37)
    CONCRETE_COLOUR    = (0.30, 0.28, 0.23)
    STAIN_STRENGTH     = 0.55
    STAIN_SCALE        = 4.0
    STAIN_STRETCH      = 8.0
    ROUGHNESS_BASE     = 0.85
    ROUGHNESS_VAR      = 0.10
    BUMP_STRENGTH      = 0.03
    BUMP_SCALE         = 80.0

    mat = bpy.data.materials.new("Concrete")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    # Node column X positions (left → right)
    C = [-1200, -900, -600, -300, 0, 300]

    # ── Texture coordinates ───────────────────────────────────────
    tex_coord = _new_node(tree, 'ShaderNodeTexCoord', (C[0], 300))
    mapping = _new_node(tree, 'ShaderNodeMapping', (C[1], 300),
                        "Base Mapping")

    # ── Whitewash patchiness ──────────────────────────────────────
    # A large-scale 3D noise determines where whitewash remains.
    noise_ww = _new_node(tree, 'ShaderNodeTexNoise', (C[1], 0),
                         "Whitewash Pattern")
    noise_ww.inputs['Scale'].default_value = WHITEWASH_SCALE
    noise_ww.inputs['Detail'].default_value = 6.0
    noise_ww.inputs['Roughness'].default_value = 0.6

    # Threshold: the coverage parameter sets where the paint/concrete
    # boundary falls.  Inverted so higher coverage = more whitewash.
    ramp_ww = _new_node(tree, 'ShaderNodeValToRGB', (C[2], 0),
                        "Whitewash Threshold")
    threshold = 1.0 - WHITEWASH_COVERAGE
    lo = max(0.001, threshold - WHITEWASH_EDGE)
    hi = min(0.999, threshold + WHITEWASH_EDGE)
    ramp_ww.color_ramp.elements[0].position = lo
    ramp_ww.color_ramp.elements[1].position = hi

    # Mix: factor=0 → concrete (A), factor=1 → whitewash (B)
    mix_ww = _new_node(tree, 'ShaderNodeMix', (C[3], 0),
                       "Concrete ↔ Whitewash")
    mix_ww.data_type = 'RGBA'
    mix_ww.inputs[6].default_value = (*CONCRETE_COLOUR, 1.0)    # A
    mix_ww.inputs[7].default_value = (*WHITEWASH_COLOUR, 1.0)   # B

    # ── Rain staining ─────────────────────────────────────────────
    # Noise stretched vertically to create long vertical streaks from
    # water runoff.  Applied as a darkening multiply over the base.
    mapping_st = _new_node(tree, 'ShaderNodeMapping', (C[1], -300),
                           "Stain Stretch")
    mapping_st.inputs['Scale'].default_value = (
        STAIN_SCALE, STAIN_SCALE, STAIN_SCALE / STAIN_STRETCH)

    noise_st = _new_node(tree, 'ShaderNodeTexNoise', (C[2], -300),
                         "Rain Stain")
    noise_st.inputs['Scale'].default_value = 1.0   # controlled by mapping
    noise_st.inputs['Detail'].default_value = 4.0
    noise_st.inputs['Roughness'].default_value = 0.5

    # Ramp outputs white (clean) to grey (stained).  The grey value
    # is used as a multiply factor: 1.0 = no change, <1.0 = darker.
    ramp_st = _new_node(tree, 'ShaderNodeValToRGB', (C[3], -300),
                        "Stain Darkness")
    ramp_st.color_ramp.elements[0].position = 0.4
    ramp_st.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp_st.color_ramp.elements[1].position = 0.7
    sv = 1.0 - STAIN_STRENGTH
    ramp_st.color_ramp.elements[1].color = (sv, sv, sv, 1)

    # Multiply blend: result = base × stain_grey
    mix_st = _new_node(tree, 'ShaderNodeMix', (C[4], -100),
                       "Apply Stain")
    mix_st.data_type = 'RGBA'
    mix_st.blend_type = 'MULTIPLY'
    mix_st.inputs[0].default_value = 1.0                         # factor

    # ── Roughness variation ───────────────────────────────────────
    noise_rgh = _new_node(tree, 'ShaderNodeTexNoise', (C[2], -550),
                          "Roughness Noise")
    noise_rgh.inputs['Scale'].default_value = 12.0
    noise_rgh.inputs['Detail'].default_value = 3.0

    map_rng = _new_node(tree, 'ShaderNodeMapRange', (C[3], -550),
                        "Roughness Range")
    map_rng.inputs['From Min'].default_value = 0.0
    map_rng.inputs['From Max'].default_value = 1.0
    map_rng.inputs['To Min'].default_value = ROUGHNESS_BASE - ROUGHNESS_VAR
    map_rng.inputs['To Max'].default_value = ROUGHNESS_BASE + ROUGHNESS_VAR

    # ── Bump map (fine surface texture) ───────────────────────────
    voronoi = _new_node(tree, 'ShaderNodeTexVoronoi', (C[2], -750),
                        "Surface Texture")
    voronoi.inputs['Scale'].default_value = BUMP_SCALE
    voronoi.voronoi_dimensions = '3D'

    bump = _new_node(tree, 'ShaderNodeBump', (C[4], -650), "Bump")
    bump.inputs['Strength'].default_value = BUMP_STRENGTH

    # ── Principled BSDF & output ──────────────────────────────────
    bsdf = _new_node(tree, 'ShaderNodeBsdfPrincipled', (C[5], 0))
    bsdf.inputs['Metallic'].default_value = 0.0

    output = _new_node(tree, 'ShaderNodeOutputMaterial', (C[5] + 300, 0))

    # ── Link everything together ──────────────────────────────────
    L = tree.links
    # Coordinate chains
    L.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise_ww.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise_rgh.inputs['Vector'])
    L.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])
    L.new(tex_coord.outputs['Object'], mapping_st.inputs['Vector'])
    L.new(mapping_st.outputs['Vector'], noise_st.inputs['Vector'])

    # Whitewash: noise → ramp → mix factor
    L.new(noise_ww.outputs['Fac'], ramp_ww.inputs['Fac'])
    L.new(ramp_ww.outputs['Color'], mix_ww.inputs[0])           # factor
    L.new(mix_ww.outputs[2], mix_st.inputs[6])                  # → stain A

    # Rain stain: noise → ramp → multiply B
    L.new(noise_st.outputs['Fac'], ramp_st.inputs['Fac'])
    L.new(ramp_st.outputs['Color'], mix_st.inputs[7])           # → stain B

    # Final colour → BSDF
    L.new(mix_st.outputs[2], bsdf.inputs['Base Color'])

    # Roughness
    L.new(noise_rgh.outputs['Fac'], map_rng.inputs['Value'])
    L.new(map_rng.outputs['Result'], bsdf.inputs['Roughness'])

    # Bump
    L.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    # Output
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


def make_brass_material():
    """Aged, tarnished brass — dull brown with patina variation.

    TUNEABLE PARAMETERS
    -------------------
    Colour:
      BASE_COLOUR      (R,G,B)    Main tarnished brass colour.
                                    Default: (0.25, 0.18, 0.06)
      PATINA_COLOUR    (R,G,B)    Darker patina in sheltered areas.
                                    Default: (0.10, 0.09, 0.03)
      PATINA_AMOUNT    (0.0–1.0)  How much patina variation.
                                    0.0 = uniform, 1.0 = heavily varied.
                                    Default: 0.40
      PATINA_SCALE     (float)    Patina pattern size.
                                    Default: 8.0

    Surface:
      METALLIC         (0.0–1.0)  Metallicness (tarnish reduces this).
                                    Default: 0.55
      ROUGHNESS_BASE   (0.0–1.0)  Average roughness (dull surface).
                                    Default: 0.65
      ROUGHNESS_VAR    (0.0–0.3)  Roughness variation.
                                    Default: 0.15
      BUMP_STRENGTH    (0.0–2.0)  Surface wear bump intensity.
                                    Default: 0.10
      BUMP_SCALE       (float)    Bump detail scale.
                                    Default: 30.0
    """
    # ── Tuneable values ───────────────────────────────────────────
    BASE_COLOUR    = (0.25, 0.18, 0.06)
    PATINA_COLOUR  = (0.10, 0.09, 0.03)
    PATINA_AMOUNT  = 0.40
    PATINA_SCALE   = 8.0
    METALLIC       = 0.55
    ROUGHNESS_BASE = 0.50
    ROUGHNESS_VAR  = 0.05
    BUMP_STRENGTH  = 0.02
    BUMP_SCALE     = 50.0

    mat = bpy.data.materials.new("Brass")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    C = [-1000, -700, -400, -100, 200]

    tex_coord = _new_node(tree, 'ShaderNodeTexCoord', (C[0], 200))
    mapping = _new_node(tree, 'ShaderNodeMapping', (C[1], 200))

    # ── Patina distribution ───────────────────────────────────────
    noise_pat = _new_node(tree, 'ShaderNodeTexNoise', (C[1], 0),
                          "Patina Pattern")
    noise_pat.inputs['Scale'].default_value = PATINA_SCALE
    noise_pat.inputs['Detail'].default_value = 5.0
    noise_pat.inputs['Roughness'].default_value = 0.7

    ramp_pat = _new_node(tree, 'ShaderNodeValToRGB', (C[2], 0),
                         "Patina Threshold")
    lo = max(0.001, PATINA_AMOUNT - 0.10)
    hi = min(0.999, PATINA_AMOUNT + 0.10)
    ramp_pat.color_ramp.elements[0].position = lo
    ramp_pat.color_ramp.elements[1].position = hi

    mix_col = _new_node(tree, 'ShaderNodeMix', (C[3], 0),
                        "Base ↔ Patina")
    mix_col.data_type = 'RGBA'
    mix_col.inputs[6].default_value = (*BASE_COLOUR, 1.0)       # A
    mix_col.inputs[7].default_value = (*PATINA_COLOUR, 1.0)     # B

    # ── Roughness variation ───────────────────────────────────────
    noise_rgh = _new_node(tree, 'ShaderNodeTexNoise', (C[1], -300),
                          "Roughness Noise")
    noise_rgh.inputs['Scale'].default_value = 15.0
    noise_rgh.inputs['Detail'].default_value = 3.0

    map_rng = _new_node(tree, 'ShaderNodeMapRange', (C[2], -300),
                        "Roughness Range")
    map_rng.inputs['From Min'].default_value = 0.0
    map_rng.inputs['From Max'].default_value = 1.0
    map_rng.inputs['To Min'].default_value = ROUGHNESS_BASE - ROUGHNESS_VAR
    map_rng.inputs['To Max'].default_value = ROUGHNESS_BASE + ROUGHNESS_VAR

    # ── Bump ──────────────────────────────────────────────────────
    voronoi = _new_node(tree, 'ShaderNodeTexVoronoi', (C[1], -500),
                        "Surface Wear")
    voronoi.inputs['Scale'].default_value = BUMP_SCALE
    voronoi.voronoi_dimensions = '3D'

    bump = _new_node(tree, 'ShaderNodeBump', (C[3], -400), "Bump")
    bump.inputs['Strength'].default_value = BUMP_STRENGTH

    # ── BSDF ──────────────────────────────────────────────────────
    bsdf = _new_node(tree, 'ShaderNodeBsdfPrincipled', (C[4], 0))
    bsdf.inputs['Metallic'].default_value = METALLIC

    output = _new_node(tree, 'ShaderNodeOutputMaterial', (C[4] + 300, 0))

    # ── Links ─────────────────────────────────────────────────────
    L = tree.links
    L.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise_pat.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise_rgh.inputs['Vector'])
    L.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])

    L.new(noise_pat.outputs['Fac'], ramp_pat.inputs['Fac'])
    L.new(ramp_pat.outputs['Color'], mix_col.inputs[0])
    L.new(mix_col.outputs[2], bsdf.inputs['Base Color'])

    L.new(noise_rgh.outputs['Fac'], map_rng.inputs['Value'])
    L.new(map_rng.outputs['Result'], bsdf.inputs['Roughness'])

    L.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


def make_rusted_steel_material():
    """Severely rusted steel — heavy orange/brown rust with pitting.

    Used for sighting tubes and centre pipe which are exposed to the
    elements and badly corroded.

    TUNEABLE PARAMETERS
    -------------------
    Colour:
      RUST_COLOUR_A    (R,G,B)    Primary rust (orange).
                                    Default: (0.45, 0.18, 0.04)
      RUST_COLOUR_B    (R,G,B)    Secondary rust (dark brown).
                                    Default: (0.20, 0.08, 0.02)
      RUST_SCALE       (float)    Rust pattern scale.
                                    Default: 6.0

    Surface:
      ROUGHNESS        (0.0–1.0)  Very rough for corroded metal.
                                    Default: 0.95
      BUMP_STRENGTH    (0.0–2.0)  Pitting/flaking bump intensity.
                                    Default: 0.50
      BUMP_SCALE       (float)    Pitting detail scale.
                                    Default: 20.0
    """
    # ── Tuneable values ───────────────────────────────────────────
    RUST_COLOUR_A  = (0.14, 0.06, 0.02)
    RUST_COLOUR_B  = (0.07, 0.03, 0.01)
    RUST_SCALE     = 6.0
    ROUGHNESS      = 0.95
    BUMP_STRENGTH  = 0.50
    BUMP_SCALE     = 20.0

    mat = bpy.data.materials.new("RustedSteel")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    C = [-1000, -700, -400, -100, 200]

    tex_coord = _new_node(tree, 'ShaderNodeTexCoord', (C[0], 200))
    mapping = _new_node(tree, 'ShaderNodeMapping', (C[1], 200))

    # ── Rust colour variation ─────────────────────────────────────
    # Noise mixes between orange and dark brown rust.
    noise_rust = _new_node(tree, 'ShaderNodeTexNoise', (C[1], 0),
                           "Rust Pattern")
    noise_rust.inputs['Scale'].default_value = RUST_SCALE
    noise_rust.inputs['Detail'].default_value = 8.0
    noise_rust.inputs['Roughness'].default_value = 0.7

    mix_col = _new_node(tree, 'ShaderNodeMix', (C[2], 0), "Rust Colour")
    mix_col.data_type = 'RGBA'
    mix_col.inputs[6].default_value = (*RUST_COLOUR_A, 1.0)     # A
    mix_col.inputs[7].default_value = (*RUST_COLOUR_B, 1.0)     # B

    # ── Bump — Voronoi for pitting ────────────────────────────────
    voronoi = _new_node(tree, 'ShaderNodeTexVoronoi', (C[1], -300),
                        "Pitting")
    voronoi.inputs['Scale'].default_value = BUMP_SCALE
    voronoi.voronoi_dimensions = '3D'

    bump = _new_node(tree, 'ShaderNodeBump', (C[2], -300), "Bump")
    bump.inputs['Strength'].default_value = BUMP_STRENGTH

    # ── BSDF — rust is not metallic ──────────────────────────────
    bsdf = _new_node(tree, 'ShaderNodeBsdfPrincipled', (C[3], 0))
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = ROUGHNESS

    output = _new_node(tree, 'ShaderNodeOutputMaterial', (C[3] + 300, 0))

    # ── Links ─────────────────────────────────────────────────────
    L = tree.links
    L.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise_rust.inputs['Vector'])
    L.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])

    L.new(noise_rust.outputs['Fac'], mix_col.inputs[0])
    L.new(mix_col.outputs[2], bsdf.inputs['Base Color'])

    L.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


def make_aged_steel_material():
    """Aged steel with surface grime — dark grey, still metallic.

    Used for screws and pegs which are somewhat protected from weather
    but still show age and dirt.

    TUNEABLE PARAMETERS
    -------------------
    Colour:
      BASE_COLOUR      (R,G,B)    Dark grey steel base.
                                    Default: (0.12, 0.12, 0.13)
      GRIME_COLOUR     (R,G,B)    Dark brown grime/dirt.
                                    Default: (0.06, 0.04, 0.03)
      GRIME_AMOUNT     (0.0–1.0)  How much grime coverage.
                                    Default: 0.30
      GRIME_SCALE      (float)    Grime pattern scale.
                                    Default: 10.0

    Surface:
      METALLIC         (0.0–1.0)  Metallicness.
                                    Default: 0.70
      ROUGHNESS        (0.0–1.0)  Surface roughness.
                                    Default: 0.55
      BUMP_STRENGTH    (0.0–2.0)  Surface texture bump.
                                    Default: 0.08
    """
    # ── Tuneable values ───────────────────────────────────────────
    BASE_COLOUR    = (0.12, 0.12, 0.13)
    GRIME_COLOUR   = (0.06, 0.04, 0.03)
    GRIME_AMOUNT   = 0.30
    GRIME_SCALE    = 10.0
    METALLIC       = 0.70
    ROUGHNESS      = 0.55
    BUMP_STRENGTH  = 0.08

    mat = bpy.data.materials.new("AgedSteel")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    C = [-1000, -700, -400, -100, 200]

    tex_coord = _new_node(tree, 'ShaderNodeTexCoord', (C[0], 200))
    mapping = _new_node(tree, 'ShaderNodeMapping', (C[1], 200))

    # ── Grime distribution ────────────────────────────────────────
    noise = _new_node(tree, 'ShaderNodeTexNoise', (C[1], 0),
                      "Grime Pattern")
    noise.inputs['Scale'].default_value = GRIME_SCALE
    noise.inputs['Detail'].default_value = 5.0

    ramp = _new_node(tree, 'ShaderNodeValToRGB', (C[2], 0),
                     "Grime Threshold")
    lo = max(0.001, GRIME_AMOUNT - 0.10)
    hi = min(0.999, GRIME_AMOUNT + 0.10)
    ramp.color_ramp.elements[0].position = lo
    ramp.color_ramp.elements[1].position = hi

    mix_col = _new_node(tree, 'ShaderNodeMix', (C[3], 0),
                        "Base ↔ Grime")
    mix_col.data_type = 'RGBA'
    mix_col.inputs[6].default_value = (*BASE_COLOUR, 1.0)       # A
    mix_col.inputs[7].default_value = (*GRIME_COLOUR, 1.0)      # B

    # ── Bump ──────────────────────────────────────────────────────
    voronoi = _new_node(tree, 'ShaderNodeTexVoronoi', (C[1], -300),
                        "Surface Texture")
    voronoi.inputs['Scale'].default_value = 40.0
    voronoi.voronoi_dimensions = '3D'

    bump = _new_node(tree, 'ShaderNodeBump', (C[2], -300), "Bump")
    bump.inputs['Strength'].default_value = BUMP_STRENGTH

    # ── BSDF ──────────────────────────────────────────────────────
    bsdf = _new_node(tree, 'ShaderNodeBsdfPrincipled', (C[4], 0))
    bsdf.inputs['Metallic'].default_value = METALLIC
    bsdf.inputs['Roughness'].default_value = ROUGHNESS

    output = _new_node(tree, 'ShaderNodeOutputMaterial', (C[4] + 300, 0))

    # ── Links ─────────────────────────────────────────────────────
    L = tree.links
    L.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise.inputs['Vector'])
    L.new(mapping.outputs['Vector'], voronoi.inputs['Vector'])

    L.new(noise.outputs['Fac'], ramp.inputs['Fac'])
    L.new(ramp.outputs['Color'], mix_col.inputs[0])
    L.new(mix_col.outputs[2], bsdf.inputs['Base Color'])

    L.new(voronoi.outputs['Distance'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


def make_wood_material():
    """Weathered, stained wood showing early rot.

    TUNEABLE PARAMETERS
    -------------------
    Colour:
      BASE_COLOUR        (R,G,B)    Dark stained wood base.
                                      Default: (0.15, 0.08, 0.03)
      GRAIN_COLOUR       (R,G,B)    Lighter grain bands.
                                      Default: (0.22, 0.13, 0.05)
      ROT_COLOUR         (R,G,B)    Dark rot/decay patches.
                                      Default: (0.04, 0.03, 0.02)

    Pattern:
      GRAIN_SCALE        (float)    Wood grain scale.
                                      Default: 15.0
      GRAIN_DISTORTION   (float)    How wavy/organic the grain is.
                                      Default: 4.0
      ROT_AMOUNT         (0.0–1.0)  How much rot coverage.
                                      0.0 = no rot, 1.0 = fully decayed.
                                      Default: 0.20
      ROT_SCALE          (float)    Rot patch pattern scale.
                                      Default: 5.0

    Surface:
      ROUGHNESS          (0.0–1.0)  Surface roughness.
                                      Default: 0.90
      BUMP_STRENGTH      (0.0–2.0)  Grain/rot bump intensity.
                                      Default: 0.20
    """
    # ── Tuneable values ───────────────────────────────────────────
    BASE_COLOUR      = (0.15, 0.08, 0.03)
    GRAIN_COLOUR     = (0.22, 0.13, 0.05)
    ROT_COLOUR       = (0.04, 0.03, 0.02)
    GRAIN_SCALE      = 15.0
    GRAIN_DISTORTION = 4.0
    ROT_AMOUNT       = 0.20
    ROT_SCALE        = 5.0
    ROUGHNESS        = 0.90
    BUMP_STRENGTH    = 0.20

    mat = bpy.data.materials.new("Wood")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    C = [-1000, -700, -400, -100, 200]

    tex_coord = _new_node(tree, 'ShaderNodeTexCoord', (C[0], 200))
    mapping = _new_node(tree, 'ShaderNodeMapping', (C[1], 200))

    # ── Wood grain ────────────────────────────────────────────────
    # Wave texture produces banded stripes; distortion makes them organic.
    wave = _new_node(tree, 'ShaderNodeTexWave', (C[1], 0), "Wood Grain")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'Z'
    wave.wave_profile = 'SAW'
    wave.inputs['Scale'].default_value = GRAIN_SCALE
    wave.inputs['Distortion'].default_value = GRAIN_DISTORTION
    wave.inputs['Detail'].default_value = 3.0
    wave.inputs['Detail Scale'].default_value = 1.0

    mix_grain = _new_node(tree, 'ShaderNodeMix', (C[2], 0),
                          "Grain Colour")
    mix_grain.data_type = 'RGBA'
    mix_grain.inputs[6].default_value = (*BASE_COLOUR, 1.0)     # A
    mix_grain.inputs[7].default_value = (*GRAIN_COLOUR, 1.0)    # B

    # ── Rot patches ───────────────────────────────────────────────
    noise_rot = _new_node(tree, 'ShaderNodeTexNoise', (C[1], -300),
                          "Rot Pattern")
    noise_rot.inputs['Scale'].default_value = ROT_SCALE
    noise_rot.inputs['Detail'].default_value = 4.0
    noise_rot.inputs['Roughness'].default_value = 0.8

    ramp_rot = _new_node(tree, 'ShaderNodeValToRGB', (C[2], -300),
                         "Rot Threshold")
    lo = max(0.001, ROT_AMOUNT - 0.08)
    hi = min(0.999, ROT_AMOUNT + 0.08)
    ramp_rot.color_ramp.elements[0].position = lo
    ramp_rot.color_ramp.elements[1].position = hi

    mix_rot = _new_node(tree, 'ShaderNodeMix', (C[3], 0), "Apply Rot")
    mix_rot.data_type = 'RGBA'
    mix_rot.inputs[7].default_value = (*ROT_COLOUR, 1.0)        # B

    # ── Bump from grain ───────────────────────────────────────────
    bump = _new_node(tree, 'ShaderNodeBump', (C[3], -300), "Bump")
    bump.inputs['Strength'].default_value = BUMP_STRENGTH

    # ── BSDF ──────────────────────────────────────────────────────
    bsdf = _new_node(tree, 'ShaderNodeBsdfPrincipled', (C[4], 0))
    bsdf.inputs['Metallic'].default_value = 0.0
    bsdf.inputs['Roughness'].default_value = ROUGHNESS

    output = _new_node(tree, 'ShaderNodeOutputMaterial', (C[4] + 300, 0))

    # ── Links ─────────────────────────────────────────────────────
    L = tree.links
    L.new(tex_coord.outputs['Object'], mapping.inputs['Vector'])
    L.new(mapping.outputs['Vector'], wave.inputs['Vector'])
    L.new(mapping.outputs['Vector'], noise_rot.inputs['Vector'])

    # Grain → rot overlay
    L.new(wave.outputs['Fac'], mix_grain.inputs[0])
    L.new(mix_grain.outputs[2], mix_rot.inputs[6])               # → rot A
    L.new(noise_rot.outputs['Fac'], ramp_rot.inputs['Fac'])
    L.new(ramp_rot.outputs['Color'], mix_rot.inputs[0])          # rot factor

    # Final colour
    L.new(mix_rot.outputs[2], bsdf.inputs['Base Color'])

    # Bump from grain pattern
    L.new(wave.outputs['Fac'], bump.inputs['Height'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


def make_terrain_material():
    """Layered terrain: bedrock → soil → grass, blended by world-space Z.

    TUNEABLE PARAMETERS
    -------------------
    BEDROCK_Z / SOIL_Z       — Z heights of layer boundaries
    TRANSITION               — blending width at each boundary (metres)
    *_COLOUR_A / _COLOUR_B   — base / variation colours for each layer
    *_ROUGHNESS              — surface roughness per layer
    *_SCALE                  — procedural texture scale per layer
    GRASS_BUMP               — strength of grassy lumpiness
    """
    # ── TUNEABLE VALUES ──────────────────────────────────────────
    # Ground surface sits 80% up the base slab
    GROUND_Z       = -BASE_HEIGHT + 0.80 * BASE_HEIGHT
    BEDROCK_Z      = -(BASE_HEIGHT + LB_HEIGHT + LBLOCK_H * 0.80)
    SOIL_Z         = GROUND_Z - 0.01   # grass begins just below ground surface
    TRANSITION     = 0.04        # 4 cm blend between layers

    BEDROCK_COL_A  = (0.35, 0.33, 0.30)    # pale grey stone
    BEDROCK_COL_B  = (0.22, 0.20, 0.18)    # darker crevice
    BEDROCK_ROUGH  = 0.95
    BEDROCK_SCALE  = 4.0

    SOIL_COL_A     = (0.18, 0.12, 0.06)    # rich brown earth
    SOIL_COL_B     = (0.12, 0.08, 0.04)    # darker variation
    SOIL_ROUGH     = 0.98
    SOIL_SCALE     = 6.0

    GRASS_COL_A    = (0.12, 0.22, 0.04)    # mid green
    GRASS_COL_B    = (0.08, 0.15, 0.03)    # darker tufts
    GRASS_COL_DRY  = (0.20, 0.18, 0.06)    # dry / bare patches
    GRASS_ROUGH    = 0.90
    GRASS_SCALE    = 8.0
    GRASS_BUMP     = 0.12
    GRASS_DRY_AMT  = 0.10                  # proportion of dry patches

    # Radial dryness (centre browner, edges greener)
    RADIAL_DRY_INNER = 0.80                # full dryness within this radius
    RADIAL_DRY_OUTER = 4.60                # fades to green by this radius
    RADIAL_DRY_POWER = 0.5                 # >1 = tighter centre falloff
    RADIAL_NOISE_SCALE = 0.6               # blotchy radial variation
    RADIAL_NOISE_STRENGTH = 0.8            # 0..1 → how patchy

    # Stones / rocks
    STONE_SCALE     = 6.0                  # higher = smaller stones
    STONE_THRESHOLD = 0.12                 # distance threshold for stones
    STONE_BUMP      = 0.18                 # bump height contribution
    STONE_COL_A     = (0.38, 0.36, 0.33)   # light stone
    STONE_COL_B     = (0.25, 0.23, 0.21)   # dark stone
    STONE_ROUGH     = 0.85
    USE_SHADER_STONES = False              # if True, tint terrain with stone mask
    # ─────────────────────────────────────────────────────────────

    mat = bpy.data.materials.new("Terrain")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    N = lambda t, loc, lbl="": _new_node(tree, t, loc, lbl)
    L = tree.links

    # ── Coordinates ──────────────────────────────────────────────
    tex_coord = N('ShaderNodeTexCoord', (-1400, 0), "Tex Coord")
    # Use Object coordinates so the Z height is in world space
    sep_xyz   = N('ShaderNodeSeparateXYZ', (-1200, 0), "Separate XYZ")
    L.new(tex_coord.outputs['Object'], sep_xyz.inputs['Vector'])

    # ── Layer masks from Z height ────────────────────────────────
    # Bedrock → Soil transition
    cr_bs = N('ShaderNodeValToRGB', (-900, 200), "Bedrock→Soil")
    cr_bs.color_ramp.elements[0].position = 0.0
    cr_bs.color_ramp.elements[1].position = 1.0
    # Map: Z = BEDROCK_Z → 0 (bedrock), Z = BEDROCK_Z + TRANSITION → 1 (soil)
    map_bs = N('ShaderNodeMapRange', (-1050, 200), "Map Bedrock→Soil")
    map_bs.inputs['From Min'].default_value = BEDROCK_Z
    map_bs.inputs['From Max'].default_value = BEDROCK_Z + TRANSITION
    map_bs.inputs['To Min'].default_value = 0.0
    map_bs.inputs['To Max'].default_value = 1.0
    map_bs.clamp = True
    L.new(sep_xyz.outputs['Z'], map_bs.inputs['Value'])

    # Soil → Grass transition
    map_sg = N('ShaderNodeMapRange', (-1050, -100), "Map Soil→Grass")
    map_sg.inputs['From Min'].default_value = SOIL_Z
    map_sg.inputs['From Max'].default_value = SOIL_Z + TRANSITION
    map_sg.inputs['To Min'].default_value = 0.0
    map_sg.inputs['To Max'].default_value = 1.0
    map_sg.clamp = True
    L.new(sep_xyz.outputs['Z'], map_sg.inputs['Value'])

    # ── Radial dryness (brown centre → green edges) ─────────────
    # Compute radius from X/Y, then map to a 0–1 dryness mask.
    comb_xy = N('ShaderNodeCombineXYZ', (-1050, -350), "XY Vector")
    L.new(sep_xyz.outputs['X'], comb_xy.inputs['X'])
    L.new(sep_xyz.outputs['Y'], comb_xy.inputs['Y'])

    radius = N('ShaderNodeVectorMath', (-900, -350), "Radius")
    radius.operation = 'LENGTH'
    L.new(comb_xy.outputs['Vector'], radius.inputs[0])

    radial_sub = N('ShaderNodeMath', (-750, -350), "Radial Shift")
    radial_sub.operation = 'SUBTRACT'
    radial_sub.inputs[1].default_value = RADIAL_DRY_INNER
    L.new(radius.outputs['Value'], radial_sub.inputs[0])

    radial_map = N('ShaderNodeMapRange', (-600, -350), "Radial Dry Map")
    radial_map.inputs['From Min'].default_value = 0.0
    radial_map.inputs['From Max'].default_value = max(
        0.01, RADIAL_DRY_OUTER - RADIAL_DRY_INNER)
    radial_map.inputs['To Min'].default_value = 1.0
    radial_map.inputs['To Max'].default_value = 0.0
    radial_map.clamp = True
    L.new(radial_sub.outputs['Value'], radial_map.inputs['Value'])

    radial_pow = N('ShaderNodeMath', (-450, -350), "Radial Dry Power")
    radial_pow.operation = 'POWER'
    radial_pow.inputs[1].default_value = RADIAL_DRY_POWER
    L.new(radial_map.outputs['Result'], radial_pow.inputs[0])

    # Blotchy modulation of radial dryness
    radial_noise = N('ShaderNodeTexNoise', (-450, -500), "Radial Noise")
    radial_noise.inputs['Scale'].default_value = RADIAL_NOISE_SCALE
    radial_noise.inputs['Detail'].default_value = 2.0
    radial_noise.inputs['Roughness'].default_value = 0.6
    L.new(tex_coord.outputs['Object'], radial_noise.inputs['Vector'])

    radial_noise_map = N('ShaderNodeMapRange', (-250, -500), "Radial Noise Map")
    radial_noise_map.inputs['From Min'].default_value = 0.0
    radial_noise_map.inputs['From Max'].default_value = 1.0
    radial_noise_map.inputs['To Min'].default_value = 1.0 - RADIAL_NOISE_STRENGTH
    radial_noise_map.inputs['To Max'].default_value = 1.0 + RADIAL_NOISE_STRENGTH
    radial_noise_map.clamp = True
    L.new(radial_noise.outputs['Fac'], radial_noise_map.inputs['Value'])

    radial_patch = N('ShaderNodeMath', (-50, -420), "Radial Dry Patch")
    radial_patch.operation = 'MULTIPLY'
    L.new(radial_pow.outputs['Value'], radial_patch.inputs[0])
    L.new(radial_noise_map.outputs['Result'], radial_patch.inputs[1])

    radial_clamp = N('ShaderNodeMapRange', (120, -420), "Radial Dry Clamp")
    radial_clamp.inputs['From Min'].default_value = 0.0
    radial_clamp.inputs['From Max'].default_value = 1.0
    radial_clamp.inputs['To Min'].default_value = 0.0
    radial_clamp.inputs['To Max'].default_value = 1.0
    radial_clamp.clamp = True
    L.new(radial_patch.outputs['Value'], radial_clamp.inputs['Value'])

    radial_grass = N('ShaderNodeMath', (300, -420), "Radial Grass")
    radial_grass.operation = 'SUBTRACT'
    radial_grass.inputs[0].default_value = 1.0
    L.new(radial_clamp.outputs['Result'], radial_grass.inputs[1])

    grass_mask = N('ShaderNodeMath', (500, -200), "Grass Mask")
    grass_mask.operation = 'MAXIMUM'
    L.new(map_sg.outputs['Result'], grass_mask.inputs[0])
    L.new(radial_grass.outputs['Value'], grass_mask.inputs[1])

    # ── Bedrock colour ───────────────────────────────────────────
    rock_noise = N('ShaderNodeTexNoise', (-700, 500), "Rock Noise")
    rock_noise.inputs['Scale'].default_value = BEDROCK_SCALE
    rock_noise.inputs['Detail'].default_value = 8.0
    rock_noise.inputs['Roughness'].default_value = 0.7
    L.new(tex_coord.outputs['Object'], rock_noise.inputs['Vector'])

    rock_cr = N('ShaderNodeValToRGB', (-500, 500), "Rock Colour")
    rock_cr.color_ramp.elements[0].position = 0.35
    rock_cr.color_ramp.elements[0].color = (*BEDROCK_COL_B, 1)
    rock_cr.color_ramp.elements[1].position = 0.65
    rock_cr.color_ramp.elements[1].color = (*BEDROCK_COL_A, 1)
    L.new(rock_noise.outputs['Fac'], rock_cr.inputs['Fac'])

    # ── Soil colour ──────────────────────────────────────────────
    soil_noise = N('ShaderNodeTexNoise', (-700, 200), "Soil Noise")
    soil_noise.inputs['Scale'].default_value = SOIL_SCALE
    soil_noise.inputs['Detail'].default_value = 6.0
    soil_noise.inputs['Roughness'].default_value = 0.6
    L.new(tex_coord.outputs['Object'], soil_noise.inputs['Vector'])

    soil_cr = N('ShaderNodeValToRGB', (-500, 200), "Soil Colour")
    soil_cr.color_ramp.elements[0].position = 0.40
    soil_cr.color_ramp.elements[0].color = (*SOIL_COL_B, 1)
    soil_cr.color_ramp.elements[1].position = 0.60
    soil_cr.color_ramp.elements[1].color = (*SOIL_COL_A, 1)
    L.new(soil_noise.outputs['Fac'], soil_cr.inputs['Fac'])

    # ── Grass colour (with dry patches) ──────────────────────────
    grass_noise = N('ShaderNodeTexNoise', (-700, -100), "Grass Noise")
    grass_noise.inputs['Scale'].default_value = GRASS_SCALE
    grass_noise.inputs['Detail'].default_value = 6.0
    grass_noise.inputs['Roughness'].default_value = 0.5
    L.new(tex_coord.outputs['Object'], grass_noise.inputs['Vector'])

    grass_cr = N('ShaderNodeValToRGB', (-500, -100), "Grass Colour")
    grass_cr.color_ramp.elements[0].position = 0.40
    grass_cr.color_ramp.elements[0].color = (*GRASS_COL_B, 1)
    grass_cr.color_ramp.elements[1].position = 0.60
    grass_cr.color_ramp.elements[1].color = (*GRASS_COL_A, 1)
    L.new(grass_noise.outputs['Fac'], grass_cr.inputs['Fac'])

    # Dry patch overlay
    dry_noise = N('ShaderNodeTexNoise', (-700, -350), "Dry Noise")
    dry_noise.inputs['Scale'].default_value = 3.0
    dry_noise.inputs['Detail'].default_value = 4.0
    L.new(tex_coord.outputs['Object'], dry_noise.inputs['Vector'])

    dry_cr = N('ShaderNodeValToRGB', (-500, -350), "Dry Mask")
    dry_cr.color_ramp.elements[0].position = 1.0 - GRASS_DRY_AMT
    dry_cr.color_ramp.elements[1].position = 1.0
    L.new(dry_noise.outputs['Fac'], dry_cr.inputs['Fac'])

    # Dry patches biased toward the centre (radial dryness)
    dry_strength = N('ShaderNodeMapRange', (-300, -350), "Dry Strength")
    dry_strength.inputs['From Min'].default_value = 0.0
    dry_strength.inputs['From Max'].default_value = 1.0
    dry_strength.inputs['To Min'].default_value = 0.20
    dry_strength.inputs['To Max'].default_value = 1.00
    dry_strength.clamp = True
    L.new(radial_clamp.outputs['Result'], dry_strength.inputs['Value'])

    dry_mask = N('ShaderNodeMath', (-120, -350), "Dry Mask × Radial")
    dry_mask.operation = 'MULTIPLY'
    L.new(dry_cr.outputs['Color'], dry_mask.inputs[0])
    L.new(dry_strength.outputs['Result'], dry_mask.inputs[1])

    grass_mix = N('ShaderNodeMixRGB', (-300, -200), "Grass + Dry")
    grass_mix.blend_type = 'MIX'
    grass_mix.inputs[0].default_value = 1.0   # use dry mask as factor
    L.new(dry_mask.outputs['Value'], grass_mix.inputs['Fac'])
    L.new(grass_cr.outputs['Color'], grass_mix.inputs['Color1'])
    grass_mix.inputs['Color2'].default_value = (*GRASS_COL_DRY, 1)

    # Radial dryness: mix grass with soil colour toward the centre
    grass_radial = N('ShaderNodeMixRGB', (-120, -50), "Grass ↔ Soil (Radial)")
    grass_radial.blend_type = 'MIX'
    L.new(radial_clamp.outputs['Result'], grass_radial.inputs['Fac'])
    L.new(grass_mix.outputs['Color'], grass_radial.inputs['Color1'])
    L.new(soil_cr.outputs['Color'], grass_radial.inputs['Color2'])

    # ── Combine layers: bedrock → soil → grass ───────────────────
    mix_bs = N('ShaderNodeMixRGB', (-100, 300), "Bedrock→Soil Mix")
    mix_bs.blend_type = 'MIX'
    L.new(map_bs.outputs['Result'], mix_bs.inputs['Fac'])
    L.new(rock_cr.outputs['Color'], mix_bs.inputs['Color1'])
    L.new(soil_cr.outputs['Color'], mix_bs.inputs['Color2'])

    mix_sg = N('ShaderNodeMixRGB', (100, 100), "→Grass Mix")
    mix_sg.blend_type = 'MIX'
    L.new(grass_mask.outputs['Value'], mix_sg.inputs['Fac'])
    L.new(mix_bs.outputs['Color'], mix_sg.inputs['Color1'])
    L.new(grass_radial.outputs['Color'], mix_sg.inputs['Color2'])


    # ── Roughness: blend per layer (bedrock → soil → grass) ─────
    rough_bs = N('ShaderNodeMixRGB', (-100, -200), "Rough B→S")
    rough_bs.blend_type = 'MIX'
    L.new(map_bs.outputs['Result'], rough_bs.inputs['Fac'])
    rough_bs.inputs['Color1'].default_value = (BEDROCK_ROUGH, BEDROCK_ROUGH, BEDROCK_ROUGH, 1)
    rough_bs.inputs['Color2'].default_value = (SOIL_ROUGH, SOIL_ROUGH, SOIL_ROUGH, 1)

    rough_final = N('ShaderNodeMixRGB', (100, -200), "Rough →G")
    rough_final.blend_type = 'MIX'
    L.new(grass_mask.outputs['Value'], rough_final.inputs['Fac'])
    L.new(rough_bs.outputs['Color'], rough_final.inputs['Color1'])
    rough_final.inputs['Color2'].default_value = (GRASS_ROUGH, GRASS_ROUGH, GRASS_ROUGH, 1)


    # ── Bump: grassy lumpiness on top layer ──────────────────────
    bump_noise = N('ShaderNodeTexNoise', (-300, -500), "Grass Bump Noise")
    bump_noise.inputs['Scale'].default_value = 30.0
    bump_noise.inputs['Detail'].default_value = 8.0
    bump_noise.inputs['Roughness'].default_value = 0.6
    L.new(tex_coord.outputs['Object'], bump_noise.inputs['Vector'])

    bump_mul = N('ShaderNodeMath', (-100, -500), "Bump × Grass Mask")
    bump_mul.operation = 'MULTIPLY'
    L.new(bump_noise.outputs['Fac'], bump_mul.inputs[0])
    L.new(grass_mask.outputs['Value'], bump_mul.inputs[1])

    # Stone/rock micro-relief — small pebbles concentrated near centre
    stone_voro = N('ShaderNodeTexVoronoi', (-300, -750), "Stone Voronoi")
    stone_voro.inputs['Scale'].default_value = STONE_SCALE
    stone_voro.voronoi_dimensions = '3D'
    L.new(tex_coord.outputs['Object'], stone_voro.inputs['Vector'])

    stone_mask = N('ShaderNodeMath', (-100, -750), "Stone Mask")
    stone_mask.operation = 'LESS_THAN'
    stone_mask.inputs[1].default_value = STONE_THRESHOLD
    L.new(stone_voro.outputs['Distance'], stone_mask.inputs[0])

    stone_occ = N('ShaderNodeMath', (-100, -850), "Stone Occurrence")
    stone_occ.operation = 'MULTIPLY'
    L.new(stone_mask.outputs['Value'], stone_occ.inputs[0])
    L.new(radial_clamp.outputs['Result'], stone_occ.inputs[1])

    stone_cr = N('ShaderNodeValToRGB', (100, -850), "Stone Colour")
    stone_cr.color_ramp.elements[0].position = 0.35
    stone_cr.color_ramp.elements[0].color = (*STONE_COL_B, 1)
    stone_cr.color_ramp.elements[1].position = 0.65
    stone_cr.color_ramp.elements[1].color = (*STONE_COL_A, 1)
    L.new(stone_voro.outputs['Distance'], stone_cr.inputs['Fac'])

    # Stones tint the base colour in the drier centre
    stone_mix = N('ShaderNodeMixRGB', (250, 100), "Base + Stones")
    stone_mix.blend_type = 'MIX'
    L.new(stone_occ.outputs['Value'], stone_mix.inputs['Fac'])
    L.new(mix_sg.outputs['Color'], stone_mix.inputs['Color1'])
    L.new(stone_cr.outputs['Color'], stone_mix.inputs['Color2'])

    rough_stone = N('ShaderNodeMixRGB', (250, -200), "Rough + Stones")
    rough_stone.blend_type = 'MIX'
    L.new(stone_occ.outputs['Value'], rough_stone.inputs['Fac'])
    L.new(rough_final.outputs['Color'], rough_stone.inputs['Color1'])
    rough_stone.inputs['Color2'].default_value = (STONE_ROUGH, STONE_ROUGH, STONE_ROUGH, 1)

    stone_height = N('ShaderNodeMath', (100, -750), "Stone Height")
    stone_height.operation = 'MULTIPLY'
    stone_height.inputs[1].default_value = STONE_BUMP
    L.new(stone_mask.outputs['Value'], stone_height.inputs[0])

    stone_centre = N('ShaderNodeMath', (250, -750), "Stone × Dry")
    stone_centre.operation = 'MULTIPLY'
    L.new(stone_height.outputs['Value'], stone_centre.inputs[0])
    L.new(radial_clamp.outputs['Result'], stone_centre.inputs[1])

    bump_add = N('ShaderNodeMath', (-20, -600), "Bump + Stones")
    bump_add.operation = 'ADD'
    L.new(bump_mul.outputs['Value'], bump_add.inputs[0])
    L.new(stone_centre.outputs['Value'], bump_add.inputs[1])

    bump = N('ShaderNodeBump', (100, -500), "Bump")
    bump.inputs['Strength'].default_value = GRASS_BUMP
    L.new(bump_add.outputs['Value'], bump.inputs['Height'])

    # ── BSDF ─────────────────────────────────────────────────────
    bsdf = N('ShaderNodeBsdfPrincipled', (400, 100), "Terrain BSDF")
    # Choose whether to apply the shader-based stone tint
    if USE_SHADER_STONES:
        color_out = stone_mix
        rough_out = rough_stone
    else:
        color_out = mix_sg
        rough_out = rough_final
    L.new(color_out.outputs['Color'], bsdf.inputs['Base Color'])
    # Feed the R channel of the blended roughness colour into Roughness
    sep_rough = N('ShaderNodeSeparateColor', (250, -200), "Sep Rough")
    L.new(rough_out.outputs['Color'], sep_rough.inputs['Color'])
    L.new(sep_rough.outputs['Red'], bsdf.inputs['Roughness'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    output = N('ShaderNodeOutputMaterial', (700, 100))
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


def make_landscape_material():
    """Distant countryside surrounding the hilltop — patchwork fields
    fading into overcast atmospheric haze at distance.

    The material is entirely procedural: Voronoi-based field boundaries
    tinted with varied greens and browns, plus distance-based haze that
    blends to the overcast sky colour so the far edge of the landscape
    ring dissolves invisibly into the world background.

    TUNEABLE PARAMETERS
    -------------------
    FIELD_SCALE         — Voronoi scale (lower = larger fields)
    FIELD_COL_DARK      — darkest field green
    FIELD_COL_MID       — mid field green
    FIELD_COL_LIGHT     — lightest / pasture green
    FIELD_COL_CROP      — brown / ploughed field
    HEDGE_WIDTH         — hedgerow darkness width in Voronoi space
    HEDGE_COL           — hedgerow colour (dark green/brown)
    HAZE_START          — distance (m) where haze begins
    HAZE_END            — distance (m) where fully hazed out
    HAZE_COL            — haze / overcast sky colour
    """
    # ── TUNEABLE VALUES ──────────────────────────────────────────
    FIELD_SCALE     = 0.08       # large fields (~12 m Voronoi cells)
    FIELD_COL_DARK  = (0.06, 0.14, 0.03)   # dark pasture
    FIELD_COL_MID   = (0.10, 0.20, 0.05)   # mid green
    FIELD_COL_LIGHT = (0.14, 0.26, 0.07)   # light meadow
    FIELD_COL_CROP  = (0.16, 0.14, 0.06)   # ploughed / arable
    HEDGE_WIDTH     = 0.06       # hedgerow band width (normalised)
    HEDGE_COL       = (0.03, 0.06, 0.02)   # dark hedge green
    WITHIN_NOISE_SC = 1.2        # within-field variation scale
    WITHIN_NOISE_AM = 0.15       # within-field variation amplitude

    HAZE_START      = 15.0       # haze begins (metres from origin)
    HAZE_END        = 150.0      # fully hazed by here
    HAZE_COL        = (0.52, 0.54, 0.50)   # overcast haze (matches sky)
    # ─────────────────────────────────────────────────────────────

    mat = bpy.data.materials.new("Landscape")
    mat.use_nodes = True
    tree = mat.node_tree
    tree.nodes.clear()

    N = lambda t, loc, lbl="": _new_node(tree, t, loc, lbl)
    L = tree.links

    # ── Coordinates ───────────────────────────────────────────────
    tex_coord = N('ShaderNodeTexCoord', (-1200, 0), "Tex Coord")
    sep_xyz   = N('ShaderNodeSeparateXYZ', (-1000, 0), "Sep XYZ")
    L.new(tex_coord.outputs['Object'], sep_xyz.inputs['Vector'])

    # XY-only vector for distance calculation
    comb_xy = N('ShaderNodeCombineXYZ', (-1000, -300), "XY Vector")
    L.new(sep_xyz.outputs['X'], comb_xy.inputs['X'])
    L.new(sep_xyz.outputs['Y'], comb_xy.inputs['Y'])

    dist = N('ShaderNodeVectorMath', (-800, -300), "Distance")
    dist.operation = 'LENGTH'
    L.new(comb_xy.outputs['Vector'], dist.inputs[0])

    # ── Patchwork fields via Voronoi ──────────────────────────────
    voronoi = N('ShaderNodeTexVoronoi', (-800, 300), "Field Voronoi")
    voronoi.inputs['Scale'].default_value = FIELD_SCALE
    voronoi.voronoi_dimensions = '2D'
    voronoi.feature = 'F1'
    L.new(tex_coord.outputs['Object'], voronoi.inputs['Vector'])

    # Use randomness output (cell ID hash) for per-field colour
    field_cr = N('ShaderNodeValToRGB', (-550, 300), "Field Colours")
    els = field_cr.color_ramp.elements
    els[0].position = 0.0
    els[0].color = (*FIELD_COL_DARK, 1)
    e1 = field_cr.color_ramp.elements.new(0.33)
    e1.color = (*FIELD_COL_MID, 1)
    e2 = field_cr.color_ramp.elements.new(0.66)
    e2.color = (*FIELD_COL_LIGHT, 1)
    els[1].position = 1.0
    els[1].color = (*FIELD_COL_CROP, 1)
    L.new(voronoi.outputs['Distance'], field_cr.inputs['Fac'])

    # ── Within-field variation (subtle noise) ─────────────────────
    field_noise = N('ShaderNodeTexNoise', (-800, 100), "Field Noise")
    field_noise.inputs['Scale'].default_value = WITHIN_NOISE_SC
    field_noise.inputs['Detail'].default_value = 4.0
    field_noise.inputs['Roughness'].default_value = 0.5
    L.new(tex_coord.outputs['Object'], field_noise.inputs['Vector'])

    field_var = N('ShaderNodeMapRange', (-600, 100), "Field Var")
    field_var.inputs['From Min'].default_value = 0.0
    field_var.inputs['From Max'].default_value = 1.0
    field_var.inputs['To Min'].default_value = 1.0 - WITHIN_NOISE_AM
    field_var.inputs['To Max'].default_value = 1.0 + WITHIN_NOISE_AM
    field_var.clamp = True
    L.new(field_noise.outputs['Fac'], field_var.inputs['Value'])

    # Multiply field colour by variation
    field_varied = N('ShaderNodeVectorMath', (-350, 200), "Field × Var")
    field_varied.operation = 'SCALE'
    L.new(field_cr.outputs['Color'], field_varied.inputs[0])
    L.new(field_var.outputs['Result'], field_varied.inputs['Scale'])

    # ── Hedgerow darkening at field boundaries ────────────────────
    hedge_mask = N('ShaderNodeMapRange', (-550, 0), "Hedge Mask")
    hedge_mask.inputs['From Min'].default_value = 0.0
    hedge_mask.inputs['From Max'].default_value = HEDGE_WIDTH
    hedge_mask.inputs['To Min'].default_value = 1.0
    hedge_mask.inputs['To Max'].default_value = 0.0
    hedge_mask.clamp = True
    L.new(voronoi.outputs['Distance'], hedge_mask.inputs['Value'])

    hedge_mix = N('ShaderNodeMixRGB', (-200, 200), "Hedge Mix")
    hedge_mix.blend_type = 'MIX'
    L.new(hedge_mask.outputs['Result'], hedge_mix.inputs['Fac'])
    L.new(field_varied.outputs['Vector'], hedge_mix.inputs['Color1'])
    hedge_mix.inputs['Color2'].default_value = (*HEDGE_COL, 1)

    # ── Distance haze fade ────────────────────────────────────────
    haze_map = N('ShaderNodeMapRange', (-600, -300), "Haze Fade")
    haze_map.inputs['From Min'].default_value = HAZE_START
    haze_map.inputs['From Max'].default_value = HAZE_END
    haze_map.inputs['To Min'].default_value = 0.0
    haze_map.inputs['To Max'].default_value = 1.0
    haze_map.clamp = True
    L.new(dist.outputs['Value'], haze_map.inputs['Value'])

    haze_mix = N('ShaderNodeMixRGB', (0, 100), "Landscape + Haze")
    haze_mix.blend_type = 'MIX'
    L.new(haze_map.outputs['Result'], haze_mix.inputs['Fac'])
    L.new(hedge_mix.outputs['Color'], haze_mix.inputs['Color1'])
    haze_mix.inputs['Color2'].default_value = (*HAZE_COL, 1)

    # ── BSDF ──────────────────────────────────────────────────────
    bsdf = N('ShaderNodeBsdfPrincipled', (200, 100), "Landscape BSDF")
    L.new(haze_mix.outputs['Color'], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = 1.0

    output = N('ShaderNodeOutputMaterial', (450, 100))
    L.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    return mat


# =====================================================================
# COMPONENT BUILDERS
# =====================================================================

def build_pillar(M):
    """Main concrete pillar body with channels for centre pipe and sighting tubes.

    The centre-pipe channel runs from the pillar top to the box top face.
    The four sighting-tube channels each run from one pillar face inward to
    the box outer face — they do NOT extend into the box interior.  The
    concrete is bounded by the tube surfaces and the box wall.
    """
    print("  Pillar body ...")
    pillar = make_frustum(
        "Pillar", PILLAR_BTM_HW, PILLAR_TOP_HW, PILLAR_HEIGHT,
        base_z=0, bevel_r=BEVEL_RADIUS, bevel_n=BEVEL_SEGMENTS)

    # --- Rectangular void for the upper wooden box ---
    # The box sits inside the pillar; the concrete must have a matching
    # cavity so the box, cavity air, and concrete are distinct volumes.
    box_top_z = UB_BASE_Z + UB_HEIGHT
    bpy.ops.mesh.primitive_cube_add(size=1, location=(
        0, 0, UB_BASE_Z + UB_HEIGHT / 2))
    v = bpy.context.active_object
    # Slightly larger than the box outer dimensions for a clean cut
    v.scale = (UB_HW * 2 + 0.001, UB_HW * 2 + 0.001, UB_HEIGHT + 0.001)
    activate(v)
    bpy.ops.object.transform_apply(scale=True)
    boolean_cut(pillar, v)

    # --- Centre-pipe channel (spider underside → box top face) ---
    # The top 20 mm of the pillar is carved by the spider boolean later;
    # the pipe channel only needs to reach the spider underside.
    spider_base = PILLAR_HEIGHT - SPIDER_THICK
    cp_void_len = spider_base - box_top_z + 0.002
    cp_void_z = (box_top_z - 0.001 + spider_base + 0.001) / 2
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CP_OUTER_R + 0.001,      # 1 mm clearance — tight fit
        depth=cp_void_len,
        vertices=32,
        location=(0, 0, cp_void_z))
    boolean_cut(pillar, bpy.context.active_object)

    # --- Four sighting-tube channels (pillar face → box outer face) ---
    # Each channel shares the exact axis of its sighting tube so the
    # concrete is in intimate contact with the tube outer surface.
    # The 0.1 mm boolean clearance avoids co-planar faces while keeping
    # the gap invisible.
    chan_r = ST_OUTER_R + 0.0001        # 0.1 mm clearance for clean boolean
    a = ST_TILT
    hw = pillar_hw_at(ST_Z)
    box_face = UB_HW                    # box outer face distance from centre
    box_inner = UB_HW - UB_WALL         # inner box wall distance from centre

    # Tube midpoint — same calculation as build_sighting_tubes() so the
    # channel cutter shares the identical axis line.
    tube_outer_end = hw - 0.005
    tube_inner_end = box_inner - 0.010
    tube_mid = (tube_inner_end + tube_outer_end) / 2

    # Channel spans from 2 mm inside the box wall to 5 mm past the pillar face
    chan_inner = box_face - 0.002
    chan_outer = hw + 0.005
    chan_radial_mid = (chan_outer + chan_inner) / 2
    chan_len = (chan_outer - chan_inner) / math.cos(a)

    # Z offset so channel centre lies on the tilted tube axis
    # (outer end of every tube is lower — drainage tilt)
    chan_z = ST_Z - (chan_radial_mid - tube_mid) * math.tan(a)

    # Rotations match the sighting-tube rotations exactly so channel
    # and tube share the same tilted axis (symmetric cutter — direction
    # along the axis is irrelevant).
    for dx, dy, ry, rx in (
        (0, -1, 0,  (math.pi / 2 + a)),      # South — same as tube
        (0, +1, 0, -(math.pi / 2 + a)),      # North — same as tube
        (+1, 0,  (math.pi / 2 + a), 0),      # East  — same as tube
        (-1, 0, -(math.pi / 2 + a), 0),      # West  — same as tube
    ):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=chan_r, depth=chan_len, vertices=32,
            location=(dx * chan_radial_mid, dy * chan_radial_mid, chan_z))
        c = bpy.context.active_object
        c.rotation_euler = (rx, ry, 0)
        activate(c)
        bpy.ops.object.transform_apply(rotation=True)
        boolean_cut(pillar, c)

    # Bevelled entrance at each sighting hole — conical chamfer, 8 mm deep
    bevel_face_r = ST_OUTER_R + 0.012   # wider at the pillar surface
    bevel_inner_r = chan_r               # matches channel
    bevel_depth = 0.008

    # Z at pillar face on the tilted tube axis
    bevel_face_z = ST_Z - (hw - tube_mid) * math.tan(a)

    # Cone is asymmetric (wide end at local -Z must face outward), so
    # the rotation preserves the original sign but reduces the magnitude
    # by the tilt angle — giving the same axis line as the tube while
    # keeping radius1 (wider) at the pillar face.
    for face_x, face_y, ry, rx in (
        (0, -hw, 0, -(math.pi / 2 - a)),      # South
        (0, +hw, 0, +(math.pi / 2 - a)),      # North
        (+hw, 0, -(math.pi / 2 - a), 0),      # East
        (-hw, 0, +(math.pi / 2 - a), 0),      # West
    ):
        bpy.ops.mesh.primitive_cone_add(
            radius1=bevel_face_r, radius2=bevel_inner_r,
            depth=bevel_depth, vertices=32,
            location=(face_x, face_y, bevel_face_z))
        c = bpy.context.active_object
        c.rotation_euler = (rx, ry, 0)
        activate(c)
        bpy.ops.object.transform_apply(rotation=True)
        # Shift inward along tube axis so wide end sits at pillar face
        shift_x = -face_x / hw * bevel_depth / 2 if face_x != 0 else 0
        shift_y = -face_y / hw * bevel_depth / 2 if face_y != 0 else 0
        shift_z = bevel_depth / 2 * math.sin(a)   # inward = slightly uphill
        c.location = (face_x + shift_x, face_y + shift_y, bevel_face_z + shift_z)
        boolean_cut(pillar, c)

    assign(pillar, M['concrete'])
    return pillar


def build_centre_pipe(M):
    """Vertical steel tube — from the spider underside down to just inside the box lid."""
    print("  Centre pipe ...")
    # Top of pipe: ends at the bottom surface of the spider
    z_top = PILLAR_HEIGHT - SPIDER_THICK
    # Bottom of pipe: protrudes a small, slightly random amount below the box lid
    lid_inner_z = UB_BASE_Z + UB_HEIGHT - UB_WALL
    protrude = 0.020 + random.Random(70).uniform(-0.008, 0.008)
    z_btm = lid_inner_z - protrude

    total_h = z_top - z_btm
    z_centre = (z_top + z_btm) / 2
    pipe = make_tube("CentrePipe", CP_OUTER_R, CP_INNER_R,
                     total_h, loc=(0, 0, z_centre))
    assign(pipe, M['rusted_steel'])
    smooth(pipe)
    return pipe


def build_sighting_tubes(M):
    """Four sighting tubes extending from 5 mm inside the pillar face,
    through the box wall, and 10 mm into the box cavity."""
    print("  Sighting tubes ...")
    hw = pillar_hw_at(ST_Z)
    box_inner = UB_HW - UB_WALL           # inner box wall distance from centre
    outer_end = hw - 0.005                 # 5 mm inside pillar face
    inner_end = box_inner - 0.010          # 10 mm into box cavity
    a = ST_TILT

    directions = [
        ("ST_East",  ( 1, 0), (0,  math.pi / 2 + a, 0)),
        ("ST_West",  (-1, 0), (0, -(math.pi / 2 + a), 0)),
        ("ST_North", (0,  1), (-(math.pi / 2 + a), 0, 0)),
        ("ST_South", (0, -1), ( (math.pi / 2 + a), 0, 0)),
    ]
    tubes = []
    for name, (dx, dy), rot in directions:
        tube_len = outer_end - inner_end
        mid = (inner_end + outer_end) / 2

        loc = (dx * mid, dy * mid, ST_Z)
        t = make_tube(name, ST_OUTER_R, ST_INNER_R, tube_len, loc=loc)
        t.rotation_euler = rot
        assign(t, M['rusted_steel'])
        smooth(t)
        tubes.append(t)
    return tubes


def build_upper_box(M):
    """Upper wooden box — 5-sided (4 walls + top, open bottom), 15 mm thick.

    Built directly with bmesh for clean, predictable geometry.  Circular
    holes for the centre pipe and four sighting tubes are then cut with
    boolean operations through the flat walls.
    """
    print("  Upper wooden box ...")
    ow = UB_HW                          # outer half-width
    iw = UB_HW - UB_WALL               # inner half-width
    bz = UB_BASE_Z                      # bottom of box
    tz = UB_BASE_Z + UB_HEIGHT          # top of box (outer)
    iz = tz - UB_WALL                   # ceiling (inner)

    bm = bmesh.new()

    # 16 vertices — outer shell and inner shell
    ot = [bm.verts.new(v) for v in [
        (-ow, -ow, tz), ( ow, -ow, tz), ( ow,  ow, tz), (-ow,  ow, tz)]]
    ob = [bm.verts.new(v) for v in [
        (-ow, -ow, bz), ( ow, -ow, bz), ( ow,  ow, bz), (-ow,  ow, bz)]]
    it_ = [bm.verts.new(v) for v in [
        (-iw, -iw, iz), ( iw, -iw, iz), ( iw,  iw, iz), (-iw,  iw, iz)]]
    ib = [bm.verts.new(v) for v in [
        (-iw, -iw, bz), ( iw, -iw, bz), ( iw,  iw, bz), (-iw,  iw, bz)]]

    # Top face (+Z)
    bm.faces.new([ot[0], ot[1], ot[2], ot[3]])
    # Ceiling (-Z, looking down into cavity)
    bm.faces.new([it_[3], it_[2], it_[1], it_[0]])
    # 4 outer sides
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([ob[i], ob[j], ot[j], ot[i]])
    # 4 inner sides (normals point into cavity)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([ib[j], ib[i], it_[i], it_[j]])
    # 4 bottom rim faces (normals -Z)
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([ob[j], ob[i], ib[i], ib[j]])

    mesh = bpy.data.meshes.new("UpperBox")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    box = bpy.data.objects.new("UpperBox", mesh)
    bpy.context.collection.objects.link(box)
    activate(box)

    # Ensure consistent outward-facing normals
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- Cut pipe holes through flat walls ---
    # Centre-pipe hole through top wall
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CP_OUTER_R + 0.001, depth=UB_WALL * 3,
        vertices=32, location=(0, 0, tz))
    boolean_cut(box, bpy.context.active_object)

    # Sighting-tube holes through four side walls — axis-matched to tubes
    a = ST_TILT
    _hw = pillar_hw_at(ST_Z)
    _box_inner = UB_HW - UB_WALL
    _tube_mid = ((_box_inner - 0.010) + (_hw - 0.005)) / 2
    # Z on the tilted tube axis at the box wall
    box_hole_z = ST_Z - (ow - _tube_mid) * math.tan(a)

    for dx, dy, rot in (
        ( 0, -1, ( (math.pi / 2 + a), 0, 0)),
        ( 0,  1, (-(math.pi / 2 + a), 0, 0)),
        ( 1,  0, (0,  (math.pi / 2 + a), 0)),
        (-1,  0, (0, -(math.pi / 2 + a), 0)),
    ):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ST_OUTER_R + 0.0001, depth=UB_WALL * 3,
            vertices=32, location=(dx * ow, dy * ow, box_hole_z))
        c = bpy.context.active_object
        c.rotation_euler = rot
        activate(c)
        bpy.ops.object.transform_apply(rotation=True)
        boolean_cut(box, c)

    assign(box, M['wood'])
    return box


def build_concrete_fill(M):
    """Concrete fill at the bottom of the upper wooden box.

    The upper centre mark was pushed into the wet concrete, so the fill
    comes right up to the mark with no gap.  The fill top is set 0.5 mm
    below the nominal surface so the base of the brass step sits slightly
    proud, avoiding Z-fighting without leaving a visible hole.
    """
    print("  Concrete fill ...")
    s = (UB_HW - UB_WALL) * 2 - 0.004  # slightly smaller than box interior
    fill_h = FILL_HEIGHT - 0.0005       # 0.5 mm below nominal for Z-fighting
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(0, 0, UB_BASE_Z + fill_h / 2))
    f = bpy.context.active_object
    f.name = "ConcreteFill"
    f.scale = (s, s, fill_h)
    activate(f)
    bpy.ops.object.transform_apply(scale=True)

    assign(f, M['concrete'])
    return f


def _union_into(target, piece):
    """Boolean-union piece into target, removing piece afterwards."""
    activate(target)
    mod = target.modifiers.new("_bool", 'BOOLEAN')
    mod.operation = 'UNION'
    mod.object = piece
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier="_bool")
    bpy.data.objects.remove(piece, do_unlink=True)


def _lathe_mesh(profile, name, n_sides=32):
    """Build a surface-of-revolution mesh from an (r, z) profile.

    Points with r < 1e-6 become singular centre vertices connected to
    their neighbour ring by a triangle fan.  All other adjacent pairs
    of rings are connected by a quad strip.
    """
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            ring = []
            for j in range(n_sides):
                a = 2 * math.pi * j / n_sides
                ring.append(bm.verts.new((
                    r * math.cos(a), r * math.sin(a), z)))
            rings.append(ring)

    for i in range(len(rings) - 1):
        r0, r1 = rings[i], rings[i + 1]
        if len(r0) == 1:
            for j in range(n_sides):
                k = (j + 1) % n_sides
                bm.faces.new([r0[0], r1[j], r1[k]])
        elif len(r1) == 1:
            for j in range(n_sides):
                k = (j + 1) % n_sides
                bm.faces.new([r0[k], r0[j], r1[0]])
        else:
            for j in range(n_sides):
                k = (j + 1) % n_sides
                bm.faces.new([r0[j], r0[k], r1[k], r1[j]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def _embedded_stem_profile(z_surface, stem_r, fillet_r, stem_h,
                           base_r, base_h, n_fillet=6):
    """Return (r, z) profile points for the embedded portion of a centre mark.

    The profile starts at the disc underside (z_surface) with a fillet
    transition into a straight cylindrical stem, a second fillet at the
    bottom, and a base disc.  The first point is (stem_r + fillet_r,
    z_surface); the last is (0, z_surface - stem_h - base_h).
    """
    z_base_top = z_surface - stem_h
    z_base_btm = z_base_top - base_h

    pts = []

    # Disc underside → fillet start
    pts.append((stem_r + fillet_r, z_surface))

    # Top fillet: quarter circle, disc underside → stem
    cx = stem_r + fillet_r
    cz = z_surface - fillet_r
    for i in range(1, n_fillet + 1):
        a = math.pi / 2 * i / n_fillet
        pts.append((cx - fillet_r * math.sin(a),
                     cz + fillet_r * math.cos(a)))

    # Straight stem
    pts.append((stem_r, z_base_top + fillet_r))

    # Bottom fillet: quarter circle, stem → base top
    cx = stem_r + fillet_r
    cz = z_base_top + fillet_r
    for i in range(1, n_fillet + 1):
        a = math.pi / 2 * i / n_fillet
        pts.append((cx - fillet_r * math.cos(a),
                     cz - fillet_r * math.sin(a)))

    # Base disc
    pts.append((base_r, z_base_top))
    pts.append((base_r, z_base_btm))
    pts.append((0, z_base_btm))

    return pts


def build_upper_centre_mark(M):
    """Upper centre mark — two stacked discs with dome and spike above,
    cylindrical stem with filleted transitions, and base disc below.

    Cross-section (top to bottom):
      - Dome (quarter ellipse, base = upper disc top, h = 75 % of disc)
      - Upper disc (tapered ~3 mm narrower at top)
      - Lower disc / flange (widest part, 2.5")
      - Cylindrical stem (25/62 of flange dia) with 5 mm fillet curves
      - Base disc (44/62 of flange dia)

    Built as a single lathe mesh; spike is a separate object.
    """
    print("  Upper centre mark ...")
    z0 = UB_BASE_Z + FILL_HEIGHT           # top of concrete fill

    # ── Dimensions ────────────────────────────────────────────
    flange_r      = UCM_R                   # 31.75 mm (widest)
    disc_h        = UCM_DISC_H             # 5 mm (both discs)
    dome_h        = 0.75 * disc_h          # 3.75 mm
    up_btm_r      = 0.0240                 # upper disc bottom radius (24.0 mm)
    up_top_r      = up_btm_r - 0.0015     # 3 mm narrower diameter → 1.5 mm radius
    dome_r        = up_top_r              # dome base = upper disc top
    spike_r       = UCM_SPIKE_D / 2        # 2.5 mm
    rod_h         = UCM_SPIKE_D * 2 / 3    # height = ⅔ diameter
    cone_h        = spike_r               # 45° tip (height = radius)
    stem_r        = 25 / 62 * flange_r
    fillet_r      = UCM_FILLET_R
    base_r        = 44 / 62 * flange_r
    base_h        = UCM_BASE_H

    # ── Z coordinates ─────────────────────────────────────────
    z_lo_btm      = z0                     # lower disc bottom (surface)
    z_lo_top      = z0 + disc_h
    z_up_top      = z_lo_top + disc_h
    z_dome_peak   = z_up_top + dome_h

    # ── Lathe profile ─────────────────────────────────────────
    N_DOME = 8
    profile = []

    # Dome: quarter ellipse from peak to upper disc top
    for i in range(N_DOME + 1):
        a = math.pi / 2 * i / N_DOME
        profile.append((dome_r * math.sin(a),
                         z_up_top + dome_h * math.cos(a)))

    # Upper disc tapered rim
    profile.append((up_btm_r, z_lo_top))

    # Lower disc (flange) — top annulus, outer rim, underside
    profile.append((flange_r, z_lo_top))
    profile.append((flange_r, z_lo_btm))

    # Embedded portion (shared with lower mark)
    profile += _embedded_stem_profile(
        z_lo_btm, stem_r, fillet_r, UCM_STEM_H, base_r, base_h)

    mesh = _lathe_mesh(profile, "UpperCentreMark")
    mark = bpy.data.objects.new("UpperCentreMark", mesh)
    bpy.context.collection.objects.link(mark)
    assign(mark, M['brass'])
    smooth(mark)

    # ── Spike (separate object) ───────────────────────────────
    z_rod  = z_dome_peak + rod_h / 2
    z_cone = z_dome_peak + rod_h + cone_h / 2

    bpy.ops.mesh.primitive_cylinder_add(
        radius=spike_r, depth=rod_h, vertices=16,
        location=(0, 0, z_rod))
    spike = bpy.context.active_object
    spike.name = "UpperCentreMark_Spike"

    bpy.ops.mesh.primitive_cone_add(
        radius1=spike_r, radius2=0,
        depth=cone_h, vertices=16,
        location=(0, 0, z_cone))
    _union_into(spike, bpy.context.active_object)

    assign(spike, M['brass'])
    smooth(spike)

    return mark


def _spider_outline():
    """Compute the 2D outer boundary of the spider (plan view).

    Returns a list of (x, y) tuples tracing the outline counter-clockwise,
    including annulus arcs, fillet curves, arm sides, and arm tips.

    Used by build_spider() for the mesh and by main() for the pillar cavity.
    """
    outer_r = SPIDER_ANNULUS_OUTER_R
    arm_hw  = SPIDER_ARM_W / 2
    tip_r   = SPIDER_ANNULUS_INNER_R + SPIDER_ARM_LEN
    fr      = SPIDER_FILLET_R

    arm_angles = [math.radians(90 + i * 120) for i in range(3)]

    # Fillet geometry (local frame: arm along +Y)
    fc_x    = arm_hw + fr
    fc_dist = outer_r + fr
    fc_y    = math.sqrt(fc_dist**2 - fc_x**2)

    t_ann_x = outer_r * fc_x / fc_dist
    t_ann_y = outer_r * fc_y / fc_dist

    fa_ann = math.atan2(t_ann_y - fc_y, t_ann_x - fc_x)
    fa_arm = math.pi
    if fa_ann < fa_arm:
        fa_ann += 2 * math.pi

    fl_arm = 0.0
    fl_ann = math.atan2(t_ann_y - fc_y, fc_x - t_ann_x)

    FILLET_N = 8
    ARC_N    = 12

    outline = []

    for ai in range(3):
        theta = arm_angles[ai]
        rot   = theta - math.pi / 2
        cr, sr = math.cos(rot), math.sin(rot)

        def xf(lx, ly, _c=cr, _s=sr):
            return (lx * _c - ly * _s, lx * _s + ly * _c)

        for j in range(FILLET_N + 1):
            t = j / FILLET_N
            a = fa_ann + t * (fa_arm - fa_ann)
            outline.append(xf(fc_x + fr * math.cos(a),
                              fc_y + fr * math.sin(a)))

        outline.append(xf(arm_hw, tip_r))
        outline.append(xf(-arm_hw, tip_r))

        for j in range(FILLET_N + 1):
            t = j / FILLET_N
            a = fl_arm + t * (fl_ann - fl_arm)
            outline.append(xf(-fc_x + fr * math.cos(a),
                              fc_y + fr * math.sin(a)))

        lt    = xf(-t_ann_x, t_ann_y)
        ang_s = math.atan2(lt[1], lt[0])

        ni    = (ai + 1) % 3
        nrot  = arm_angles[ni] - math.pi / 2
        nc, ns = math.cos(nrot), math.sin(nrot)
        rt    = (t_ann_x * nc - t_ann_y * ns,
                 t_ann_x * ns + t_ann_y * nc)
        ang_e = math.atan2(rt[1], rt[0])

        while ang_e <= ang_s:
            ang_e += 2 * math.pi

        for j in range(1, ARC_N):
            t = j / ARC_N
            a = ang_s + t * (ang_e - ang_s)
            outline.append((outer_r * math.cos(a), outer_r * math.sin(a)))

    # Deduplicate consecutive near-coincident vertices
    cleaned = [outline[0]]
    for pt in outline[1:]:
        if math.hypot(pt[0] - cleaned[-1][0], pt[1] - cleaned[-1][1]) > 1e-6:
            cleaned.append(pt)
    if math.hypot(cleaned[0][0] - cleaned[-1][0],
                  cleaned[0][1] - cleaned[-1][1]) < 1e-6:
        cleaned.pop()
    return cleaned


def build_spider(M):
    """Brass spider fitting at the top of the pillar.

    Three-armed spider with central annulus ring.  The annulus has bevelled
    top edges (inner 45° × 3 mm, outer 45° × 1 mm).  Each arm carries a
    90° V-groove down its centre.  Arm-to-annulus junctions have rounded
    fillets (20 mm radius).
    """
    print("  Spider ...")

    # ── Local shortcuts ───────────────────────────────────────────
    inner_r = SPIDER_ANNULUS_INNER_R
    outer_r = SPIDER_ANNULUS_OUTER_R
    thick   = SPIDER_THICK
    arm_hw  = SPIDER_ARM_W / 2
    tip_r   = inner_r + SPIDER_ARM_LEN      # arm tip radius from centre
    fr      = SPIDER_FILLET_R
    ib      = SPIDER_INNER_BEVEL
    obv     = SPIDER_OUTER_BEVEL
    lower_r = SPIDER_LOWER_BORE_R
    screw_r = SPIDER_SCREW_R
    screw_d = SPIDER_SCREW_SPACING / 2       # screw distance from centre
    gw      = SPIDER_GROOVE_W / 2            # groove half-width
    gd      = gw                             # groove depth (90° → depth = half-width)

    zt = PILLAR_HEIGHT
    zb = zt - thick
    zm = zt - thick / 2
    z_shelf = zb + thick / 2                 # shelf at spider mid-height

    arm_angles = [math.radians(90 + i * 120) for i in range(3)]

    outline = _spider_outline()

    # ── Compute outward normals for outer bevel offset ────────────
    # The 1 mm bevel runs around the entire outside edge (annulus arcs,
    # fillets, arm sides, and arm tips).  We build it directly into the
    # mesh by insetting the top ring from the outline.
    n = len(outline)
    normals = []
    for i in range(n):
        px, py = outline[(i - 1) % n]
        cx, cy = outline[i]
        qx, qy = outline[(i + 1) % n]
        # Edge vectors
        e1x, e1y = cx - px, cy - py
        e2x, e2y = qx - cx, qy - cy
        # Outward normals (90° CW rotation for CCW polygon)
        n1x, n1y = e1y, -e1x
        n2x, n2y = e2y, -e2x
        # Normalise each
        len1 = math.hypot(n1x, n1y)
        len2 = math.hypot(n2x, n2y)
        if len1 > 1e-9:
            n1x /= len1; n1y /= len1
        if len2 > 1e-9:
            n2x /= len2; n2y /= len2
        # Average and normalise
        ax, ay = n1x + n2x, n1y + n2y
        alen = math.hypot(ax, ay)
        if alen > 1e-9:
            ax /= alen; ay /= alen
        normals.append((ax, ay))

    # ── Create 3D spider body (solid, no inner hole yet) ──────────
    # Three vertex rings: bottom (at outer edge), bevel (outer edge,
    # 1 mm below top), and top (inset 1 mm from outer edge).
    # This builds the 45° outer bevel directly into the mesh so it
    # follows the full perimeter including arms and fillets.
    bm = bmesh.new()

    bot = [bm.verts.new((x, y, zb)) for x, y in outline]
    bev = [bm.verts.new((x, y, zt - obv)) for x, y in outline]
    top = [bm.verts.new((x - obv * nx, y - obv * ny, zt))
           for (x, y), (nx, ny) in zip(outline, normals)]

    bm.faces.new(bot[::-1])          # bottom face (normal ↓)
    bm.faces.new(top)                # top face    (normal ↑)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bot[i], bot[j], bev[j], bev[i]])    # side (vertical)
        bm.faces.new([bev[i], bev[j], top[j], top[i]])    # bevel (angled)

    # Triangulate for reliable booleans on this complex outline
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    mesh = bpy.data.meshes.new("Spider")
    bm.to_mesh(mesh)
    bm.free()

    spider = bpy.data.objects.new("Spider", mesh)
    bpy.context.collection.objects.link(spider)
    activate(spider)

    # ── Stepped centre bore ─────────────────────────────────────
    # Upper half: 93 mm dia bore from shelf to top.
    upper_h = thick / 2 + 0.002
    bpy.ops.mesh.primitive_cylinder_add(
        radius=inner_r, depth=upper_h,
        vertices=64,
        location=(0, 0, z_shelf + upper_h / 2))
    boolean_cut(spider, bpy.context.active_object)

    # Lower half: 64 mm dia bore from bottom to shelf (forms shelf).
    lower_h = thick / 2 + 0.002
    bpy.ops.mesh.primitive_cylinder_add(
        radius=lower_r, depth=lower_h,
        vertices=64,
        location=(0, 0, z_shelf - lower_h / 2))
    boolean_cut(spider, bpy.context.active_object)

    # ── Inner bevel (45° × 3 mm on top of inner edge) ────────────
    bevel_h = ib + 0.001
    bpy.ops.mesh.primitive_cone_add(
        radius1=inner_r,
        radius2=inner_r + ib + 0.001,
        depth=bevel_h,
        vertices=64,
        location=(0, 0, zt - ib + bevel_h / 2))
    boolean_cut(spider, bpy.context.active_object)

    # ── Screwholes in shelf ──────────────────────────────────────
    # Two 3 mm threaded holes drilled into the shelf, diametrically
    # opposite, 77 mm apart (centre-to-centre).
    screw_depth = thick / 2 + 0.002         # through lower half
    for angle_deg in (0, 180):
        a = math.radians(angle_deg)
        sx = screw_d * math.cos(a)
        sy = screw_d * math.sin(a)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=screw_r, depth=screw_depth,
            vertices=16,
            location=(sx, sy, z_shelf - screw_depth / 2 + 0.001))
        boolean_cut(spider, bpy.context.active_object)

    # ── V-grooves (90°, 10 mm wide) on each arm ──────────────────
    for ai in range(3):
        rot = arm_angles[ai] - math.pi / 2

        bm3 = bmesh.new()
        y0 = inner_r - 0.005
        y1 = tip_r + 0.005
        gv = [
            bm3.verts.new((-gw, y0, zt + 0.001)),   # 0 top-left  near
            bm3.verts.new(( gw, y0, zt + 0.001)),   # 1 top-right near
            bm3.verts.new(( 0,  y0, zt - gd)),      # 2 bottom    near
            bm3.verts.new((-gw, y1, zt + 0.001)),   # 3 top-left  far
            bm3.verts.new(( gw, y1, zt + 0.001)),   # 4 top-right far
            bm3.verts.new(( 0,  y1, zt - gd)),      # 5 bottom    far
        ]
        bm3.faces.new([gv[2], gv[1], gv[0]])          # near triangle
        bm3.faces.new([gv[3], gv[4], gv[5]])          # far triangle
        bm3.faces.new([gv[0], gv[1], gv[4], gv[3]])   # top quad
        bm3.faces.new([gv[1], gv[2], gv[5], gv[4]])   # right quad
        bm3.faces.new([gv[2], gv[0], gv[3], gv[5]])   # left quad

        mesh3 = bpy.data.meshes.new("_groove")
        bm3.to_mesh(mesh3)
        bm3.free()

        groove = bpy.data.objects.new("_groove", mesh3)
        bpy.context.collection.objects.link(groove)
        groove.rotation_euler.z = rot
        activate(groove)
        bpy.ops.object.transform_apply(rotation=True)
        boolean_cut(spider, groove)

    assign(spider, M['brass'])
    smooth(spider)
    return spider


def build_brass_loops(M):
    """Three brass loops embedded in the pillar top, with carved recesses.

    Each loop is a 30 mm torus (4 mm wire) standing vertically with its
    plane radially aligned (passing through the pillar centre axis).
    The top of the wire is 3 mm below the pillar surface.

    A round-bottomed recess (40 × 15 × 15 mm) with stadium plan shape
    and chamfered top edges is carved into the concrete.  The recess long
    axis runs tangentially (across the loop).  The upper portion of the
    loop and part of the inner hole are exposed; the bottom and sides
    remain embedded.
    """
    print("  Brass loops ...")

    R       = LOOP_R                              # major radius (15 mm)
    r       = LOOP_WIRE_R                         # wire radius (2 mm)
    rl      = LOOP_RECESS_L                       # recess length (40 mm)
    rw      = LOOP_RECESS_W                       # recess width  (15 mm)
    rd      = LOOP_RECESS_D                       # recess depth  (15 mm)
    hw      = rw / 2                              # half width (7.5 mm)
    z_surf  = PILLAR_HEIGHT                       # pillar surface

    # Loop centre Z: top of wire = surface - LOOP_DEPTH
    z_loop = z_surf - LOOP_DEPTH - R - r          # PILLAR_HEIGHT - 0.020

    r_pos   = LOOP_POS_R                          # 120 mm from centre
    pillar  = bpy.data.objects['Pillar']
    loops   = []

    # Recess geometry parameters
    # Local frame: length along X (tangential), width along Y (radial),
    #              depth along -Z, surface at Z = 0.
    #
    # Plan shape: a rounded rectangle (≈2:1 aspect ratio).  The narrow
    # sides have a small 5 mm bevel at the lip.  The long ends have a
    # massive spoon-shaped bevel — a flat section at full depth in the
    # middle, then gentle cos² ramps that smoothly meet the surface.
    #
    # The depth profile is generated once at full size, then each slice
    # along the length scales only the sub-surface Z coords by a taper
    # factor.  Width stays constant except for a gentle rounding of the
    # tips in the last 20 % of the ramp zone.
    half_L      = rl / 2                            # 35 mm half-length
    half_flat   = 0.010                             # 10 mm → 20 mm flat section
    ramp_L      = half_L - half_flat                # 25 mm ramp at each end
    bevel_r     = 0.005                             # 5 mm bevel (narrow dir)
    BEVEL_N     = 6                                 # bevel arc segments
    SEMI_N      = 8                                 # bottom semicircle segments
    N_SLICES    = 28                                # slices along length
    EPS         = 0.001                             # overshoot above surface

    # Build base cross-section profile once (full depth, full width).
    # List of (y, z) pairs; z < 0 = below surface, z > 0 = above.
    wall_h_full = max(0, rd - bevel_r - hw)
    base_pts = []
    # Above surface, right
    base_pts.append((hw + bevel_r, EPS))
    # Right bevel arc (quarter circle, surface → wall)
    for j in range(1, BEVEL_N + 1):
        theta = math.pi / 2 + j * (math.pi / 2) / BEVEL_N
        base_pts.append(((hw + bevel_r) + bevel_r * math.cos(theta),
                         -bevel_r + bevel_r * math.sin(theta)))
    # Wall bottom right
    base_pts.append((hw, -(bevel_r + wall_h_full)))
    # Semicircle bottom (right → left)
    for j in range(1, SEMI_N):
        a = j * (-math.pi / SEMI_N)
        base_pts.append((hw * math.cos(a),
                         -(bevel_r + wall_h_full) + hw * math.sin(a)))
    # Wall bottom left
    base_pts.append((-hw, -(bevel_r + wall_h_full)))
    # Left bevel arc (quarter circle, wall → surface)
    for j in range(1, BEVEL_N + 1):
        theta = j * (math.pi / 2) / BEVEL_N
        base_pts.append((-(hw + bevel_r) + bevel_r * math.cos(theta),
                         -bevel_r + bevel_r * math.sin(theta)))
    # Above surface, left
    base_pts.append((-(hw + bevel_r), EPS))

    for i in range(3):
        # Between spider arms (offset 60° from arm positions)
        angle = math.radians(90 + 60 + i * 120)
        cx = r_pos * math.cos(angle)
        cy = r_pos * math.sin(angle)

        # ── Brass loop (torus standing vertically) ────────────────
        bpy.ops.mesh.primitive_torus_add(
            major_radius=R, minor_radius=r,
            major_segments=32, minor_segments=12,
            location=(cx, cy, z_loop))
        lp = bpy.context.active_object
        lp.name = f"BrassLoop_{i}"

        # Stand upright with plane passing through Z axis:
        # Rx(90°) tilts ring into XZ plane, Rz(angle) aligns radially.
        lp.rotation_euler = (math.pi / 2, 0, angle)
        activate(lp)
        bpy.ops.object.transform_apply(rotation=True)

        assign(lp, M['brass'])
        smooth(lp)
        loops.append(lp)

        # ── Recess cutter (spoon-shaped indent) ────────────────
        # Scale only sub-surface Z by depth_t (cos² ramp at ends).
        # Scale Y by width_t (stays ~1 in the middle, rounds gently
        # to 0 at the tips so the outline is a rounded rectangle).
        bm_r = bmesh.new()
        rings = []

        for k in range(N_SLICES + 1):
            x = -half_L + k * rl / N_SLICES
            ax = abs(x)

            # Depth taper
            if ax <= half_flat:
                depth_t = 1.0
            else:
                depth_t = math.cos(
                    math.pi / 2 * (ax - half_flat) / ramp_L) ** 2

            # Width taper — constant in the flat zone and most of
            # the ramp zone; only rounds off in the last 20 %.
            tip_start = half_flat + 0.80 * ramp_L      # ~30 mm
            if ax <= tip_start:
                width_t = 1.0
            else:
                width_t = math.cos(
                    math.pi / 2 * (ax - tip_start)
                    / (half_L - tip_start)) ** 2

            if depth_t < 0.01 and width_t < 0.05:
                continue

            ring = []
            for y, z in base_pts:
                y_eff = y * width_t
                z_eff = z * depth_t if z < 0 else EPS
                ring.append(bm_r.verts.new((x, y_eff, z_eff)))
            rings.append(ring)

        nr  = len(rings)
        npv = len(rings[0])

        # Side quads between adjacent rings
        for s in range(nr - 1):
            for v in range(npv - 1):
                bm_r.faces.new([rings[s][v],   rings[s][v + 1],
                                rings[s+1][v + 1], rings[s+1][v]])

        # End-cap faces (close the left and right ends)
        bm_r.faces.new(rings[0])
        bm_r.faces.new(rings[-1][::-1])

        # Top face (rounded-rectangle outline at z = EPS)
        top = [ring[0] for ring in rings]
        top += [ring[-1] for ring in reversed(rings)]
        bm_r.faces.new(top)

        # Ensure outward normals, then triangulate for boolean
        bmesh.ops.recalc_face_normals(bm_r, faces=bm_r.faces[:])
        bmesh.ops.triangulate(bm_r, faces=bm_r.faces[:])

        mesh_r = bpy.data.meshes.new(f"_recess_{i}")
        bm_r.to_mesh(mesh_r)
        bm_r.free()

        recess = bpy.data.objects.new(f"_recess_{i}", mesh_r)
        bpy.context.collection.objects.link(recess)
        # Position at surface; rotate so length runs tangentially (+90°)
        recess.location = (cx, cy, z_surf)
        recess.rotation_euler.z = angle + math.pi / 2
        activate(recess)
        bpy.ops.object.transform_apply(location=True, rotation=True)
        boolean_cut(pillar, recess)

    return loops


def build_plug(M):
    """Brass plug that screws into the spider's stepped bore.

    Three stacked annular rings (upper, middle, lower) with a 38 mm
    through-bore.  The upper ring has a 3 mm 45° chamfer on its top edge
    and two 9 mm clearance holes for the spider shelf screws.

    The base of the upper ring sits on the spider shelf, so the plug
    top sits 4 mm below the pillar top.
    """
    print("  Plug & inner plug ...")

    # Positioning — upper ring base sits on the spider shelf
    z_shelf = PILLAR_HEIGHT - SPIDER_THICK / 2

    bore_r  = PLUG_BORE_R
    bore_bv = PLUG_BORE_BEVEL
    up_r    = PLUG_UPPER_R
    mid_r   = PLUG_MIDDLE_R
    low_r   = PLUG_LOWER_R
    chm     = PLUG_UPPER_BEVEL

    z_top     = z_shelf + PLUG_UPPER_H          # top of plug
    z_mid_bot = z_shelf - PLUG_MIDDLE_H          # bottom of middle ring
    z_bot     = z_mid_bot - PLUG_LOWER_H         # bottom of plug

    # ── Stepped profile (XZ half-plane, spun 360° around Z) ──────
    # Ten vertices trace the cross-section clockwise from top-inner.
    bm = bmesh.new()
    profile = [
        (bore_r,            z_top - bore_bv), # 0  bore wall, below inner chamfer
        (bore_r + bore_bv,  z_top),           # 1  inner chamfer end (top surface)
        (up_r - chm,        z_top),           # 2  top surface → outer chamfer
        (up_r,          z_top - chm),         # 2  chamfer end (outer wall)
        (up_r,          z_shelf),             # 3  upper ring outer, bottom
        (mid_r,         z_shelf),             # 4  step to middle ring
        (mid_r,         z_mid_bot),           # 5  middle ring outer, bottom
        (low_r,         z_mid_bot),           # 6  step to lower ring
        (low_r,         z_bot),               # 7  lower ring bottom outer
        (bore_r,        z_bot),               # 8  lower ring bottom inner
    ]

    verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    bm.faces.new(verts)

    geom = bm.faces[:] + bm.edges[:] + bm.verts[:]
    bmesh.ops.spin(bm, geom=geom,
                   cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=2 * math.pi, steps=64)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

    mesh = bpy.data.meshes.new("Plug")
    bm.to_mesh(mesh)
    bm.free()

    plug = bpy.data.objects.new("Plug", mesh)
    bpy.context.collection.objects.link(plug)
    activate(plug)

    # ── Clearance holes in the upper ring ────────────────────────
    # Two 9 mm holes, 77 mm apart, aligned with the spider screwholes.
    hole_r = PLUG_HOLE_R
    hole_d = PLUG_HOLE_SPACING / 2              # distance from centre
    hole_h = PLUG_UPPER_H + 0.004               # through the upper ring
    for angle_deg in (0, 180):
        a = math.radians(angle_deg)
        hx = hole_d * math.cos(a)
        hy = hole_d * math.sin(a)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=hole_r, depth=hole_h,
            vertices=24,
            location=(hx, hy, z_shelf + PLUG_UPPER_H / 2))
        boolean_cut(plug, bpy.context.active_object)

    assign(plug, M['brass'])
    smooth(plug)

    # ── Inner plug ─────────────────────────────────────────────────
    # Solid cylinder (~37.8 mm dia) with 1 mm chamfer on top edge and
    # three blind holes drilled into the bottom.  Sits inside the plug
    # bore with its top flush with the plug top.
    ip_r    = IPLUG_R
    ip_h    = IPLUG_H
    ip_bv   = IPLUG_BEVEL
    z_ip_top = z_top
    z_ip_bot = z_ip_top - ip_h
    z_ip_mid = z_ip_top - ip_h / 2

    bpy.ops.mesh.primitive_cylinder_add(
        radius=ip_r, depth=ip_h, vertices=64,
        location=(0, 0, z_ip_mid))
    ip = bpy.context.active_object
    ip.name = "InnerPlug"

    # Chamfer on top edge (1 mm, 45°) — revolved triangular cutter
    eps = 0.0005
    bm_c = bmesh.new()
    cv = [
        bm_c.verts.new((ip_r - ip_bv - eps, 0, z_ip_top + eps)),
        bm_c.verts.new((ip_r + eps,          0, z_ip_top + eps)),
        bm_c.verts.new((ip_r + eps,          0, z_ip_top - ip_bv - eps)),
    ]
    bm_c.faces.new(cv)
    geom_c = bm_c.faces[:] + bm_c.edges[:] + bm_c.verts[:]
    bmesh.ops.spin(bm_c, geom=geom_c,
                   cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=2 * math.pi, steps=64)
    bmesh.ops.remove_doubles(bm_c, verts=bm_c.verts, dist=0.0001)
    mesh_c = bpy.data.meshes.new("_iplug_chamfer")
    bm_c.to_mesh(mesh_c)
    bm_c.free()

    chamfer_cut = bpy.data.objects.new("_iplug_chamfer", mesh_c)
    bpy.context.collection.objects.link(chamfer_cut)
    boolean_cut(ip, chamfer_cut)

    # Three blind holes drilled into the bottom face
    bh_r = IPLUG_HOLE_R

    # Centre hole — 6 mm dia, 16 mm deep
    cd = IPLUG_CENTRE_DEPTH
    bpy.ops.mesh.primitive_cylinder_add(
        radius=bh_r, depth=cd + 0.002, vertices=16,
        location=(0, 0, z_ip_bot + cd / 2))
    boolean_cut(ip, bpy.context.active_object)

    # Two side holes — 6 mm dia, 8 mm deep, 27 mm apart
    sd = IPLUG_SIDE_DEPTH
    side_d = IPLUG_SIDE_SPACING / 2
    for angle_deg in (90, 270):
        a = math.radians(angle_deg)
        sx = side_d * math.cos(a)
        sy = side_d * math.sin(a)
        bpy.ops.mesh.primitive_cylinder_add(
            radius=bh_r, depth=sd + 0.002, vertices=16,
            location=(sx, sy, z_ip_bot + sd / 2))
        boolean_cut(ip, bpy.context.active_object)

    assign(ip, M['brass'])
    smooth(ip)

    return plug, ip


def build_plug_text(M):
    """Embossed text around the plug upper ring.

    'TRIANGULATION STATION' across the top semicircle and
    'ORDNANCE SURVEY' across the bottom, matching the casting on
    real OS triangulation station plugs.

    The text is created flat, converted to mesh, then each vertex is
    warped around a circular arc using trigonometry.  This avoids any
    reliance on Blender's text-on-curve feature and works reliably
    across all Blender versions.

    TUNEABLE PARAMETERS
    -------------------
    TEXT_R         — baseline radius from pillar centre (default: 0.032)
    EMBOSS         — text relief height above surface (default: 0.0005)
    FONT_SIZE      — character cap height (default: 0.0045)
    RESOLUTION     — curve resolution for text conversion (default: 4)
    TOP_SPAN_DEG   — angular span of top text (default: 155°)
    BTM_SPAN_DEG   — angular span of bottom text (default: 130°)
    """
    print("  Plug text ...")

    TEXT_R       = 0.033     # midpoint of the upper ring annulus
    EMBOSS       = 0.0005    # 2.0 mm engraving depth below surface
    OVERSHOOT    = 0.002     # cutter extends this far above surface
    FONT_SIZE    = 0.01    # character height
    RESOLUTION   = 4         # text mesh resolution (lower = fewer verts)
    TOP_SPAN_DEG = 155
    BTM_SPAN_DEG = 130

    z_shelf = PILLAR_HEIGHT - SPIDER_THICK / 2
    z_top   = z_shelf + PLUG_UPPER_H

    plug = bpy.data.objects['Plug']

    # (body, centre_angle°, arc_span°)
    #   Letter tops face away from centre (standard for OS plugs).
    #   Both texts read clockwise when viewed from above.
    texts = [
        ("TRIANGULATION   STATION", 90,  TOP_SPAN_DEG),
        ("ORDNANCE     SURVEY",       270, BTM_SPAN_DEG),
    ]

    for body, centre_deg, span_deg in texts:
        centre_rad = math.radians(centre_deg)
        span_rad   = math.radians(span_deg)

        # ── Create text object ────────────────────────────────────
        bpy.ops.object.text_add(location=(0, 0, 0))
        tobj = bpy.context.active_object
        tobj.data.body = body
        tobj.data.size = FONT_SIZE
        tobj.data.align_x = 'CENTER'
        tobj.data.align_y = 'CENTER'
        tobj.data.extrude = EMBOSS + OVERSHOOT
        tobj.data.resolution_u = RESOLUTION
        tobj.name = f"_plugtext_{body[:4]}"

        # Convert font object to mesh
        activate(tobj)
        bpy.ops.object.convert(target='MESH')

        # ── Warp vertices around a circular arc ───────────────────
        bm = bmesh.new()
        bm.from_mesh(tobj.data)

        # Find the horizontal extent of the flat text
        xs = [v.co.x for v in bm.verts]
        x_min, x_max = min(xs), max(xs)
        x_mid  = (x_min + x_max) / 2
        x_span = x_max - x_min

        if x_span > 1e-6:
            for v in bm.verts:
                # t: normalised position along string (−0.5 → +0.5)
                t = (v.co.x - x_mid) / x_span

                # Angular position — both texts read clockwise from above
                angle = centre_rad - t * span_rad

                # Radial position — character height maps to radial offset
                r = TEXT_R + v.co.y   # tops of letters face outward

                v.co.x = r * math.cos(angle)
                v.co.y = r * math.sin(angle)
                # Engraved: cutter starts OVERSHOOT above the surface and
                # extends downward by EMBOSS into the plug body.
                # v.co.z ranges from 0 to (EMBOSS + OVERSHOOT) after
                # extrusion — we flip so top is above, base below.
                # Top of cutter:  z_top + OVERSHOOT  (above surface)
                # Base of cutter: z_top - EMBOSS     (below surface)
                v.co.z = (z_top + OVERSHOOT) - v.co.z

        # Merge nearly-coincident verts produced by the warp, then
        # ensure manifold normals — both critical for a clean boolean.
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

        bm.to_mesh(tobj.data)
        bm.free()
        tobj.data.update()

        # Boolean-cut the text into the plug (EXACT solver)
        boolean_cut(plug, tobj)

    # ── Fix shading after boolean cuts ──────────────────────────────
    # The booleans leave stale custom-split-normal data and break the
    # smooth-by-angle shading that was applied earlier in build_plug().
    # Clear it all and re-apply.
    activate(plug)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    try:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except RuntimeError:
        pass  # no custom split normals to clear
    bpy.ops.object.mode_set(mode='OBJECT')
    smooth(plug)


def build_fixings(M):
    """Steel machine screws and anti-rotation peg.

    Two stylised allen bolts hold the plug to the spider shelf.  Each has
    a <4 mm shaft threaded into the shelf, a 7 mm head sitting inside
    the plug's clearance hole, and a 3 mm allen socket in the top.

    A horizontal 3 mm peg passes through the bottom plug annulus into
    the inner plug, preventing it from rotating.  The peg is perpendicular
    to the line of the inner plug's blind holes (i.e. along the X axis).
    """
    print("  Steel fixings ...")

    z_shelf = PILLAR_HEIGHT - SPIDER_THICK / 2

    # ── Machine screws (stylised allen bolts) ─────────────────────
    screw_d = SCREW_SPACING / 2                  # distance from centre
    z_head_top = z_shelf + SCREW_HEAD_H

    for angle_deg in (0, 180):
        a = math.radians(angle_deg)
        sx = screw_d * math.cos(a)
        sy = screw_d * math.sin(a)

        # Shaft — sits in the spider shelf hole
        bpy.ops.mesh.primitive_cylinder_add(
            radius=SCREW_SHAFT_R, depth=SCREW_SHAFT_H,
            vertices=16,
            location=(sx, sy, z_shelf - SCREW_SHAFT_H / 2))
        screw = bpy.context.active_object
        screw.name = f"Screw_{angle_deg}"

        # Head — sits on the shelf inside the plug clearance hole
        bpy.ops.mesh.primitive_cylinder_add(
            radius=SCREW_HEAD_R, depth=SCREW_HEAD_H,
            vertices=24,
            location=(sx, sy, z_shelf + SCREW_HEAD_H / 2))
        _union_into(screw, bpy.context.active_object)

        # Allen socket — blind hole in top of head
        bpy.ops.mesh.primitive_cylinder_add(
            radius=SCREW_SOCKET_R, depth=SCREW_SOCKET_DEPTH + 0.001,
            vertices=6,
            location=(sx, sy, z_head_top - SCREW_SOCKET_DEPTH / 2))
        boolean_cut(screw, bpy.context.active_object)

        assign(screw, M['aged_steel'])
        smooth(screw)

    # ── Anti-rotation peg ─────────────────────────────────────────
    # Horizontal 3 mm steel peg through the bottom plug annulus,
    # perpendicular to the inner plug's blind holes (which run along Y).
    # 10 mm hangs outside the bottom annulus.
    plug_low_r = PLUG_LOWER_R

    # Z position: mid-height of overlap between bottom annulus and
    # inner plug.  Bottom annulus: z_shelf-9 mm to z_shelf-18 mm.
    # Inner plug bottom: z_shelf+6 mm - 23 mm = z_shelf-17 mm.
    # Overlap: z_shelf-9 mm to z_shelf-17 mm → midpoint z_shelf-13 mm.
    z_peg = z_shelf - 0.013

    # Peg along +X: outer tip at plug_low_r + overhang
    peg_outer_x = plug_low_r + PEG_OVERHANG
    peg_inner_x = peg_outer_x - PEG_LENGTH
    peg_cx = (peg_outer_x + peg_inner_x) / 2

    bpy.ops.mesh.primitive_cylinder_add(
        radius=PEG_R, depth=PEG_LENGTH,
        vertices=16,
        location=(peg_cx, 0, z_peg))
    peg = bpy.context.active_object
    peg.name = "AntiRotationPeg"
    peg.rotation_euler.y = math.pi / 2       # rotate to lie along X
    activate(peg)
    bpy.ops.object.transform_apply(rotation=True)

    assign(peg, M['aged_steel'])
    smooth(peg)


def build_flush_bracket(M):
    """Flush bracket with beading and keying structure, recessed into
    one pillar face (+Y).

    The bracket is a vertical brass plate (180 × 100 mm) with 5 mm
    semicircular beading running around all four edges of the front
    face with mitred corners.  It is set back 8 mm from the pillar
    face at the top edge; because the pillar tapers, the setback is
    greater at the bottom.

    Behind the front plate a rear plate (90 % height, bottom-aligned)
    carries a T-shaped keying piece: a thin bar (10 mm high, 25 mm
    deep) widening sharply to an anchor block (35 mm high, 10 mm deep)
    that locks the assembly into the concrete.

    A recess is carved from the pillar with chamfer faces sloping from
    a rectangle on the pillar surface (FB_RECESS_MARGIN wider than the
    plate) inward to the beading on all four sides.
    """
    print("  Flush bracket ...")

    w       = FB_W                                # 100 mm
    h       = FB_H                                # 180 mm
    d       = FB_D                                # 8 mm plate thickness
    br      = FB_BEAD_R                           # 5 mm beading radius
    setback = FB_SETBACK                          # 8 mm at top
    z_bot   = FB_BTM_Z                            # bottom edge Z
    z_top   = z_bot + h                           # top edge Z
    z_mid   = z_bot + h / 2                       # centre Z
    hw      = w / 2                               # 50 mm half width

    # Bracket plate Y: set back from pillar face at the top
    face_top = pillar_hw_at(z_top)
    plate_y  = face_top - setback                 # back face of plate
    front_y  = plate_y + d                        # plate front face Y

    # ── Plate (simple box) ────────────────────────────────────
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(0, plate_y + d / 2, z_mid))
    plate = bpy.context.active_object
    plate.name = "FlushBracket"
    plate.scale = (w, d, h)
    activate(plate)
    bpy.ops.object.transform_apply(scale=True)
    assign(plate, M['brass'])

    # ── Rear plate & keying structure ────────────────────────
    # Behind the front plate a second plate (90 % of front height,
    # bottom-aligned) carries a T-shaped keying piece that anchors
    # the assembly into the concrete.  The key is a thin horizontal
    # bar (10 mm high, 25 mm deep) widening sharply to an anchor
    # block (35 mm high, 10 mm deep).
    rear_h     = h * FB_REAR_H_FRAC               # 162 mm
    rear_d     = d                                 # same thickness as front plate
    rear_z_bot = z_bot
    rear_z_top = z_bot + rear_h
    rear_z_mid = (rear_z_bot + rear_z_top) / 2
    rear_back  = plate_y - rear_d                  # back face of rear plate

    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(0, plate_y - rear_d / 2, rear_z_mid))
    rear_plate = bpy.context.active_object
    rear_plate.name = "FlushBracket_RearPlate"
    rear_plate.scale = (w, rear_d, rear_h)
    activate(rear_plate)
    bpy.ops.object.transform_apply(scale=True)
    assign(rear_plate, M['brass'])

    # Keying bar — tapered square-section bar protruding from rear plate.
    # Square at the rear-plate end (bar_h × bar_h), 25 % narrower at the
    # anchor end.  Built with bmesh for the trapezoidal plan shape.
    bar_h      = FB_BAR_H                          # 10 mm
    bar_depth  = FB_BAR_DEPTH                      # 25 mm
    bar_z_mid  = rear_z_mid                        # centred on rear plate
    bar_back   = rear_back - bar_depth             # back face of bar
    bar_w_front = bar_h                            # square at rear plate
    bar_w_back  = bar_h * 0.75                     # 25 % narrower at anchor

    bm_bar = bmesh.new()
    bhf = bar_h / 2
    bwf = bar_w_front / 2
    bwb = bar_w_back / 2
    # Front face (y = rear_back, touching rear plate)
    bf0 = bm_bar.verts.new((-bwf, rear_back, bar_z_mid - bhf))
    bf1 = bm_bar.verts.new(( bwf, rear_back, bar_z_mid - bhf))
    bf2 = bm_bar.verts.new(( bwf, rear_back, bar_z_mid + bhf))
    bf3 = bm_bar.verts.new((-bwf, rear_back, bar_z_mid + bhf))
    # Back face (y = bar_back, touching anchor)
    bb0 = bm_bar.verts.new((-bwb, bar_back, bar_z_mid - bhf))
    bb1 = bm_bar.verts.new(( bwb, bar_back, bar_z_mid - bhf))
    bb2 = bm_bar.verts.new(( bwb, bar_back, bar_z_mid + bhf))
    bb3 = bm_bar.verts.new((-bwb, bar_back, bar_z_mid + bhf))
    bm_bar.faces.new([bf3, bf2, bf1, bf0])                # front
    bm_bar.faces.new([bb0, bb1, bb2, bb3])                # back
    bm_bar.faces.new([bf3, bb3, bb2, bf2])                # top
    bm_bar.faces.new([bf0, bf1, bb1, bb0])                # bottom
    bm_bar.faces.new([bf0, bb0, bb3, bf3])                # left
    bm_bar.faces.new([bf2, bb2, bb1, bf1])                # right
    bmesh.ops.recalc_face_normals(bm_bar, faces=bm_bar.faces[:])
    mesh_bar = bpy.data.meshes.new("FlushBracket_Bar")
    bm_bar.to_mesh(mesh_bar)
    bm_bar.free()
    bar = bpy.data.objects.new("FlushBracket_Bar", mesh_bar)
    bpy.context.collection.objects.link(bar)
    assign(bar, M['brass'])

    # Anchor block — square cross-section at back of bar
    anchor_h     = FB_ANCHOR_H                     # 35 mm
    anchor_depth = FB_ANCHOR_DEPTH                 # 10 mm
    anchor_w     = anchor_h                        # square

    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(0, bar_back - anchor_depth / 2, bar_z_mid))
    anchor = bpy.context.active_object
    anchor.name = "FlushBracket_Anchor"
    anchor.scale = (anchor_w, anchor_depth, anchor_h)
    activate(anchor)
    bpy.ops.object.transform_apply(scale=True)
    assign(anchor, M['brass'])

    # ── Beading (D-shaped tube around front face perimeter) ───
    # A semicircular cross-section (flat against plate, dome forward)
    # built as four separate straight segments — one per edge — with
    # mitred end caps.  Each ring vertex is offset along the tangent
    # by ±bi (its bi-normal offset), cutting a 45° mitre so that
    # adjacent segments meet flush at each corner with no gap.
    BEAD_N = 6                                    # semicircle segments
    n_bead = BEAD_N + 1

    bm = bmesh.new()

    # Four edges: each defined by (start, end) path points.
    # Each point: (x, z, tangent_x, tangent_z).
    edge_paths = [
        [(-hw, z_bot,  1,  0), ( hw, z_bot,  1,  0)],   # bottom
        [( hw, z_bot,  0,  1), ( hw, z_top,  0,  1)],   # right
        [( hw, z_top, -1,  0), (-hw, z_top, -1,  0)],   # top
        [(-hw, z_top,  0, -1), (-hw, z_bot,  0, -1)],   # left
    ]

    for edge_path in edge_paths:
        rings = []
        for idx, (px, pz, tx, tz) in enumerate(edge_path):
            bx, bz = -tz, tx                     # bi-normal
            msign = 1 if idx == 0 else -1         # mitre direction
            ring = []
            for j in range(n_bead):
                a = -math.pi / 2 + j * math.pi / BEAD_N
                fwd = br * math.cos(a)
                bi  = br * math.sin(a)
                m   = msign * bi                  # mitre offset along tangent
                ring.append(bm.verts.new((
                    px + bi * bx + m * tx,
                    front_y + fwd,
                    pz + bi * bz + m * tz)))
            rings.append(ring)

        # Tube surface quads
        for v in range(n_bead - 1):
            bm.faces.new([rings[0][v], rings[0][v + 1],
                          rings[1][v + 1], rings[1][v]])
        # Close the D — flat back quad
        bm.faces.new([rings[0][n_bead - 1], rings[0][0],
                      rings[1][0], rings[1][n_bead - 1]])

        # Mitred end caps (coplanar on the 45° mitre plane)
        bm.faces.new(rings[0])
        bm.faces.new(rings[1][::-1])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    mesh_bead = bpy.data.meshes.new("FlushBracket_Bead")
    bm.to_mesh(mesh_bead)
    bm.free()

    bead = bpy.data.objects.new("FlushBracket_Bead", mesh_bead)
    bpy.context.collection.objects.link(bead)
    activate(bead)
    assign(bead, M['brass'])
    smooth(bead)

    # ── Recess in pillar ──────────────────────────────────────
    # The recess is a pocket behind the bracket plate, plus sloping
    # chamfer faces from the beading edge outward to a rectangle on
    # the pillar surface that is FB_RECESS_MARGIN wider than the
    # bracket plate on each side.  The chamfer angle is whatever the
    # geometry requires — not a fixed 45°.
    # Built as a 12-vertex solid:
    #   4 back verts   (pocket back, inner outline at beading)
    #   4 inner verts  (bracket level, inner outline at beading)
    #   4 outer verts  (pillar face, outer rect = plate + margin)
    pillar = bpy.data.objects['Pillar']

    recess_margin = FB_RECESS_MARGIN              # tuneable
    bead_clr = br + 0.001                         # beading outline + clearance
    inner_y  = front_y + br + 0.001               # just past beading peak

    # Inner outline (matches bracket beading outer edge)
    ixl = -(hw + bead_clr)
    ixr =  (hw + bead_clr)
    izb =  z_bot - bead_clr
    izt =  z_top + bead_clr

    # Outer outline — fixed rectangle on pillar surface
    oxl = -(hw + recess_margin)
    oxr =  (hw + recess_margin)
    ozb =  z_bot - recess_margin
    ozt =  z_top + recess_margin

    eps     = 0.002
    y_back  = plate_y - eps
    # Outer Y must extend past pillar face at each height
    oy_top  = pillar_hw_at(ozt) + eps
    oy_bot  = pillar_hw_at(ozb) + eps

    bm_c = bmesh.new()

    # Back pocket vertices (at y = plate_y - eps, inner outline)
    b_tl = bm_c.verts.new((ixl, y_back, izt))
    b_tr = bm_c.verts.new((ixr, y_back, izt))
    b_br = bm_c.verts.new((ixr, y_back, izb))
    b_bl = bm_c.verts.new((ixl, y_back, izb))

    # Inner front vertices (at bracket level, inner outline)
    i_tl = bm_c.verts.new((ixl, inner_y, izt))
    i_tr = bm_c.verts.new((ixr, inner_y, izt))
    i_br = bm_c.verts.new((ixr, inner_y, izb))
    i_bl = bm_c.verts.new((ixl, inner_y, izb))

    # Outer front vertices (at pillar face, outer outline)
    o_tl = bm_c.verts.new((oxl, oy_top, ozt))
    o_tr = bm_c.verts.new((oxr, oy_top, ozt))
    o_br = bm_c.verts.new((oxr, oy_bot, ozb))
    o_bl = bm_c.verts.new((oxl, oy_bot, ozb))

    # 10 faces forming the closed solid
    bm_c.faces.new([b_tl, b_tr, b_br, b_bl])     # back
    bm_c.faces.new([b_tl, b_tr, i_tr, i_tl])     # pocket top
    bm_c.faces.new([b_bl, b_br, i_br, i_bl])     # pocket bottom
    bm_c.faces.new([b_tl, i_tl, i_bl, b_bl])     # pocket left
    bm_c.faces.new([b_tr, b_br, i_br, i_tr])     # pocket right
    bm_c.faces.new([i_tl, i_tr, o_tr, o_tl])     # chamfer top
    bm_c.faces.new([i_bl, i_br, o_br, o_bl])     # chamfer bottom
    bm_c.faces.new([i_tl, o_tl, o_bl, i_bl])     # chamfer left
    bm_c.faces.new([i_tr, i_br, o_br, o_tr])     # chamfer right
    bm_c.faces.new([o_tl, o_tr, o_br, o_bl])     # front

    bmesh.ops.recalc_face_normals(bm_c, faces=bm_c.faces[:])
    bmesh.ops.triangulate(bm_c, faces=bm_c.faces[:])

    mesh_c = bpy.data.meshes.new("_fb_recess")
    bm_c.to_mesh(mesh_c)
    bm_c.free()

    recess = bpy.data.objects.new("_fb_recess", mesh_c)
    bpy.context.collection.objects.link(recess)
    boolean_cut(pillar, recess)

    return plate


def build_flush_bracket_logo(M):
    """Add the TrigpointingUK logo as a multi-layer brass relief on the
    flush bracket front face.

    The SVG logo is imported, each path is classified by its fill colour
    into a relief layer, converted to mesh, solidified to the appropriate
    depth, and positioned on the bracket plate.

    Layer ordering (front to back):
        1. Bright green (#63e710)  — UK map outline           (highest)
        2. Dark green   (#599d2b)  — grass
        3. Grey         (#939393)  — trigpoint / theodolite
        4. Yellow       (#fee82a)  — benchmark arrow
        5. Near-white / light grey — highlight details
        6. Black        (#000000)  — outline base             (lowest)

    TUNEABLE PARAMETERS
    -------------------
    LOGO_RELIEF  — maximum relief height (bright green layer)
    LOGO_MARGIN  — inset from plate edges
    """
    print("  Flush bracket logo ...")

    # ── Locate SVG ──────────────────────────────────────────────
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()
    svg_path = os.path.normpath(
        os.path.join(script_dir, '..', '..', 'res', LOGO_SVG))
    if not os.path.isfile(svg_path):
        print(f"    WARNING: {svg_path} not found — skipping logo.")
        return

    # ── Colour → relief fraction ────────────────────────────────
    # sRGB hex values from the SVG, mapped to fraction of LOGO_RELIEF.
    HEX_HEIGHTS = {
        (0x63, 0xe7, 0x10): 1.00,   # bright green — UK map shape
        (0x59, 0x9d, 0x2b): 0.60,   # dark green   — grass
        (0x93, 0x93, 0x93): 0.35,   # grey         — trig / theodolite
        (0xfe, 0xe8, 0x2a): 0.35,   # yellow       — benchmark arrow
        (0xf2, 0xf2, 0xf2): 0.20,   # near-white   — highlight
        (0xe6, 0xe6, 0xe6): 0.20,   # light grey   — highlight
        (0x00, 0x00, 0x00): 0.00,   # black        — outline (skip)
    }

    def _srgb_to_lin(c):
        """Convert sRGB component [0,1] to linear."""
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    # Pre-convert to linear RGB for comparison with Blender's internal colours
    lin_heights = [
        ((_srgb_to_lin(r / 255), _srgb_to_lin(g / 255), _srgb_to_lin(b / 255)), frac)
        for (r, g, b), frac in HEX_HEIGHTS.items()
    ]

    def _match_colour(dc):
        """Return relief fraction for the closest colour match."""
        best, frac = 1e9, 0.00
        for (lr, lg, lb), f in lin_heights:
            d = (dc[0] - lr) ** 2 + (dc[1] - lg) ** 2 + (dc[2] - lb) ** 2
            if d < best:
                best, frac = d, f
        return frac

    # ── Import SVG ──────────────────────────────────────────────
    existing = set(o.name for o in bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=svg_path)
    new_all = [o for o in bpy.data.objects if o.name not in existing]
    curves = [o for o in new_all if o.type == 'CURVE']

    if not curves:
        print("    WARNING: no curves imported — skipping logo.")
        for o in new_all:
            bpy.data.objects.remove(o, do_unlink=True)
        return

    # ── Bounding box of all imported curves (world XY) ──────────
    xs, ys = [], []
    for obj in curves:
        for corner in obj.bound_box:
            co = obj.matrix_world @ Vector(corner)
            xs.append(co.x)
            ys.append(co.y)
    svg_min_x, svg_max_x = min(xs), max(xs)
    svg_min_y, svg_max_y = min(ys), max(ys)
    svg_w  = max(svg_max_x - svg_min_x, 1e-6)
    svg_h  = max(svg_max_y - svg_min_y, 1e-6)
    svg_cx = (svg_min_x + svg_max_x) / 2
    svg_cy = (svg_min_y + svg_max_y) / 2

    # Uniform scale to fit within flush bracket (with margin),
    # then stretch vertically by LOGO_V_STRETCH.
    logo_max_w = FB_W - 2 * LOGO_MARGIN
    logo_max_h = (FB_H - LOGO_BTM_OFFSET - LOGO_MARGIN) / LOGO_V_STRETCH
    scale_f    = min(logo_max_w / svg_w, logo_max_h / svg_h)
    scale_x    = scale_f                    # horizontal
    scale_y    = scale_f * LOGO_V_STRETCH   # vertical (stretched)

    # After scaling, the logo's actual height:
    logo_h     = svg_h * scale_y

    # ── Flush bracket face coordinates ──────────────────────────
    z_bot   = FB_BTM_Z
    z_top   = z_bot + FB_H
    face_top = pillar_hw_at(z_top)
    plate_y  = face_top - FB_SETBACK
    front_y  = plate_y + FB_D               # front face of the plate

    # Logo bottom 10 mm above plate bottom; centre derived from that
    logo_z_bot = z_bot + LOGO_BTM_OFFSET
    logo_z_mid = logo_z_bot + logo_h / 2

    # ── Convert each curve to a relief piece ────────────────────
    logo_objs = []
    for obj in curves:
        # Relief height from material colour
        frac = 0.00
        if obj.data.materials:
            mat = obj.data.materials[0]
            if mat:
                frac = _match_colour(mat.diffuse_color)
        relief = LOGO_RELIEF * frac

        # Unparent (SVG importer may group under an empty)
        activate(obj)
        if obj.parent:
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

        # Convert curve → mesh (fills closed 2D regions)
        bpy.ops.object.convert(target='MESH')
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        # Skip zero-relief layers (e.g. black outline) and degenerate meshes
        if frac <= 0 or not obj.data.polygons:
            bpy.data.objects.remove(obj, do_unlink=True)
            continue

        # Solidify to give relief depth (+Z direction = outward after remap)
        mod = obj.modifiers.new('Solidify', 'SOLIDIFY')
        mod.thickness = relief
        mod.offset = 1.0            # extrude in +Z (outward from plate)
        activate(obj)
        bpy.ops.object.modifier_apply(modifier='Solidify')

        # ── Transform vertices to flush bracket position ────────
        # After transform_apply, vertex coords are in world space.
        # Map from XY-plane logo space to flush bracket:
        #   logo X  → -pillar X  (mirrored so logo reads correctly
        #                          when viewed from outside the trig)
        #   logo Y  →  pillar Z  (vertical — SVG importer flips Y)
        #   logo Z  →  pillar Y  (relief depth, outward from face)
        mesh = obj.data
        for v in mesh.vertices:
            lx = (v.co.x - svg_cx) * scale_x
            ly = (v.co.y - svg_cy) * scale_y  # stretched vertically
            lz = v.co.z                        # 0 … relief

            v.co.x = -lx                       # mirror for correct reading
            v.co.y = front_y + lz              # base flush with plate face
            v.co.z = logo_z_mid + ly           # bottom aligned per offset

        # Clear any residual object transform
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (1, 1, 1)

        # Bevel the sharp edges so the relief catches light.
        # Uses bmesh.ops.bevel directly (bypasses modifier pipeline
        # which was silently failing after vertex-level transforms).
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.edges.ensure_lookup_table()

        # Select edges where the dihedral angle ≥ 30° (i.e. sharp edges
        # between top/bottom faces and side walls of the solidified relief).
        angle_thresh = math.radians(30)
        sharp_edges = []
        for e in bm.edges:
            if len(e.link_faces) == 2:
                angle = e.calc_face_angle(0)
                if angle >= angle_thresh:
                    sharp_edges.append(e)

        if sharp_edges:
            bmesh.ops.bevel(
                bm,
                geom=sharp_edges,
                offset=relief * LOGO_BEVEL_FRAC,
                offset_type='OFFSET',
                segments=LOGO_BEVEL_SEGS,
                profile=0.5,
                affect='EDGES',
            )

        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        assign(obj, M['brass'])
        obj.name = f"FBLogo_{obj.name}"
        logo_objs.append(obj)

    # ── Clean up SVG empties and unused materials ───────────────
    for o in list(bpy.data.objects):
        if o.name not in existing and o.type == 'EMPTY':
            bpy.data.objects.remove(o, do_unlink=True)

    # Purge SVG-imported materials (logo pieces now use brass)
    for mat in list(bpy.data.materials):
        if mat.name.startswith('SVGMat') and mat.users == 0:
            bpy.data.materials.remove(mat)

    print(f"    {len(logo_objs)} logo relief pieces placed.")


def build_base_slab(M):
    """Concrete foundation base — rough-sided to suggest a hand-dug hole, flat on top."""
    print("  Base slab ...")
    base = make_frustum(
        "BaseSlab", BASE_BTM_HW, BASE_TOP_HW, BASE_HEIGHT,
        base_z=-BASE_HEIGHT)

    # Subdivide to add geometry, then roughen sides and bottom
    subdivide_mesh(base, cuts=3)
    roughen_mesh(base, amount=0.020, seed=123, protect_top=True)

    assign(base, M['concrete'])
    return base


def build_angle_irons(M):
    """Four angle irons spanning the pillar-to-base-slab junction.

    T-profile built directly with bmesh (no boolean union) for completely
    predictable geometry.  All four are exactly the same length with Z
    placements differing by ~10 mm.
    """
    print("  Angle irons ...")
    rng = random.Random(99)
    irons = []

    hw_mid = (PILLAR_BTM_HW + UB_HW) / 2
    base_tilt = math.atan2(PILLAR_BTM_HW - PILLAR_TOP_HW, PILLAR_HEIGHT)
    h = AI_TOTAL_H
    bz = -BASE_HEIGHT + 0.05          # starts above base slab bottom

    leg = AI_LEG
    t = AI_THICK
    half = leg / 2

    # T cross-section centred on bounding-box centre.
    # Flange at y = -half (inner face toward pillar), web centred.
    ht = t / 2                                    # half-thickness
    profile = [
        (-half,  -half),                          # flange bottom-left
        ( half,  -half),                          # flange bottom-right
        ( half,  -half + t),                      # flange top-right
        ( ht,    -half + t),                      # web right junction
        ( ht,     half),                          # web top-right
        (-ht,     half),                          # web top-left
        (-ht,    -half + t),                      # web left junction
        (-half,  -half + t),                      # flange top-left
    ]

    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
        z_jitter = rng.uniform(-0.005, 0.005)     # ±5 mm → ~10 mm spread
        tilt_x = sy * base_tilt * (1.0 + rng.uniform(-0.01, 0.01))
        tilt_y = -sx * base_tilt * (1.0 + rng.uniform(-0.01, 0.01))

        # Build T-shape with bmesh — flip profile to orient flange
        # toward (sx, sy) so it sits against the pillar face.
        bm = bmesh.new()
        top_verts = []
        btm_verts = []
        for px, py in profile:
            x, y = px * sx, py * sy
            top_verts.append(bm.verts.new((x, y,  h / 2)))
            btm_verts.append(bm.verts.new((x, y, -h / 2)))

        n = len(profile)
        # When sx*sy < 0, one axis flip reverses the winding
        rev = (sx * sy < 0)

        # Top face (+Z normal)
        bm.faces.new(top_verts[::-1] if rev else top_verts)
        # Bottom face (-Z normal)
        bm.faces.new(btm_verts if rev else btm_verts[::-1])
        # Side faces
        for j in range(n):
            k = (j + 1) % n
            if rev:
                bm.faces.new([top_verts[k], top_verts[j],
                              btm_verts[j], btm_verts[k]])
            else:
                bm.faces.new([top_verts[j], top_verts[k],
                              btm_verts[k], btm_verts[j]])

        mesh = bpy.data.meshes.new(f"AngleIron_{i}")
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()

        iron = bpy.data.objects.new(f"AngleIron_{i}", mesh)
        bpy.context.collection.objects.link(iron)

        cx = sx * (hw_mid - leg / 2)
        cy = sy * (hw_mid - leg / 2)
        cz = bz + h / 2 + z_jitter

        iron.location = (cx, cy, cz)
        iron.rotation_euler = (tilt_x, tilt_y, 0)
        assign(iron, M['rusted_steel'])
        irons.append(iron)

    return irons


def build_lower_box(M):
    """Lower wooden box — open-bottomed cover (4 sides + top, no base)."""
    print("  Lower wooden box ...")
    zt = -BASE_HEIGHT
    h = LB_HEIGHT

    # Outer shell
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, zt - h / 2))
    box = bpy.context.active_object
    box.name = "LowerBox"
    box.scale = (LB_HW * 2, LB_HW * 2, h)
    activate(box)
    bpy.ops.object.transform_apply(scale=True)

    # Inner void — shifted down so lid (top) stays solid, bottom is open
    inner = LB_HW - LB_WALL
    void_z = zt - h / 2 - LB_WALL   # top of void = zt - LB_WALL (leaves lid)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, void_z))
    v = bpy.context.active_object
    v.scale = (inner * 2, inner * 2, h)  # extends below box bottom
    activate(v)
    bpy.ops.object.transform_apply(scale=True)
    boolean_cut(box, v)

    assign(box, M['wood'])
    return box


def build_lower_block(M):
    """Lower concrete block — rough-sided to suggest a hand-dug hole, flat on top."""
    print("  Lower block ...")
    zt = -BASE_HEIGHT - LB_HEIGHT
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(0, 0, zt - LBLOCK_H / 2))
    blk = bpy.context.active_object
    blk.name = "LowerBlock"
    blk.scale = (LBLOCK_HW * 2, LBLOCK_HW * 2, LBLOCK_H)
    activate(blk)
    bpy.ops.object.transform_apply(scale=True)

    # Subdivide to add geometry, then roughen sides and bottom
    subdivide_mesh(blk, cuts=3)
    roughen_mesh(blk, amount=0.015, seed=42, protect_top=True)

    assign(blk, M['concrete'])
    return blk


def build_lower_centre_mark(M):
    """Lower centre mark — cylinder, conic section, dome and punch mark
    above the block surface; identical embedded stem+base below.

    Cross-section (top to bottom):
      - Dome (circular arc tangent-matched to cone slope)
      - Conic section (cylinder dia → 25 % at h = 20 % of dia)
      - Cylinder (78/47 × base disc dia, 3 mm thick)
      - Cylindrical stem with 5 mm fillets (shared with upper mark)
      - Base disc (shared with upper mark)

    The dome is a circular arc whose tangent at the base matches the
    conic section's slope, so the overall shape reads as a cone with
    its apex point rounded off.  A small punch mark replaces the spike.
    """
    print("  Lower centre mark ...")
    z_top = -BASE_HEIGHT - LB_HEIGHT       # top of lower block

    # ── Shared embedded dimensions (same as upper mark) ───────
    flange_r  = UCM_R
    stem_r    = 25 / 62 * flange_r
    fillet_r  = UCM_FILLET_R
    base_r    = 44 / 62 * flange_r
    base_h    = UCM_BASE_H

    # ── Above-ground dimensions ───────────────────────────────
    base_d      = base_r * 2                # base disc diameter
    cyl_r       = 78 / 47 * base_d / 2     # cylinder radius
    cyl_h       = LCM_CYL_H                # 3 mm
    conic_top_r = 0.25 * cyl_r             # 25 % of cylinder radius
    conic_h     = 0.20 * cyl_r * 2         # 20 % of cylinder diameter
    dome_r      = conic_top_r

    # Dome: circular arc whose tangent at its base matches the cone.
    # cone_alpha is the half-angle of the arc measured from the Z-axis.
    # tan(α) = conic_h / (cyl_r - conic_top_r)
    cone_alpha = math.atan2(conic_h, cyl_r - conic_top_r)
    arc_R      = dome_r / math.sin(cone_alpha)  # arc radius
    dome_h     = arc_R * (1 - math.cos(cone_alpha))

    # ── Z coordinates ─────────────────────────────────────────
    z_cyl_btm   = z_top                    # cylinder bottom (block surface)
    z_cyl_top   = z_top + cyl_h
    z_conic_top = z_cyl_top + conic_h
    z_dome_peak = z_conic_top + dome_h

    # ── Lathe profile ─────────────────────────────────────────
    N_DOME = 8
    profile = []

    # Dome: circular arc from peak (r=0) to conic top, tangent-matched
    z_arc_ctr = z_conic_top - arc_R * math.cos(cone_alpha)
    for i in range(N_DOME + 1):
        theta = cone_alpha * i / N_DOME
        profile.append((arc_R * math.sin(theta),
                         z_arc_ctr + arc_R * math.cos(theta)))

    # Conic section (truncated cone from conic_top_r to cyl_r)
    profile.append((cyl_r, z_cyl_top))

    # Cylinder outer rim (vertical)
    profile.append((cyl_r, z_cyl_btm))

    # Embedded portion (shared with upper mark)
    profile += _embedded_stem_profile(
        z_cyl_btm, stem_r, fillet_r, UCM_STEM_H, base_r, base_h)

    mesh = _lathe_mesh(profile, "LowerCentreMark")
    mark = bpy.data.objects.new("LowerCentreMark", mesh)
    bpy.context.collection.objects.link(mark)
    assign(mark, M['brass'])
    smooth(mark)

    # ── Punch mark (45° conical hole in dome top) ──────────────
    punch_r = LCM_PUNCH_R
    cone_depth = punch_r                   # 45°: depth = radius
    bpy.ops.mesh.primitive_cone_add(
        radius1=0, radius2=punch_r,
        depth=cone_depth, vertices=16,
        location=(0, 0, z_dome_peak - cone_depth / 2))
    boolean_cut(mark, bpy.context.active_object)

    return mark


def build_terrain(M):
    """Layered terrain: dome-shaped hilltop with bedrock, soil, and grass.

    The terrain is a solid volume extending from the grass surface down
    past the lower block.  During the X-ray phase, making it transparent
    reveals the underground structure (base slab, lower box, lower block)
    embedded in the soil and bedrock.

    TUNEABLE PARAMETERS
    -------------------
    TERRAIN_RADIUS   — radius of the terrain disc (module-level constant)
    DOME_HEIGHT      — height drop centre to edge (module-level constant)
    TERRAIN_DEPTH    — how far below z=0 the terrain extends
    GRID_SUBDIVS     — mesh resolution (higher = smoother undulation)
    NOISE_STRENGTH   — amplitude of surface undulation
    NOISE_SCALE      — spatial frequency of undulation
    NOISE_OCTAVES    — fractal detail layers
    """
    print("  Terrain ...")

    # ── TUNEABLE VALUES ──────────────────────────────────────────
    # TERRAIN_RADIUS and DOME_HEIGHT are module-level constants
    # (shared with build_landscape_ring).
    GRID_SUBDIVS   = 100           # vertex spacing ~12.5 cm
    NOISE_STRENGTH = 0.08         # ±4 cm undulation
    NOISE_SCALE    = 2.5          # spatial frequency
    NOISE_OCTAVES  = 4            # fractal layers
    CUT_MARGIN     = 0.005        # 5 mm gap between terrain and base slab
    # ─────────────────────────────────────────────────────────────

    # ── Derived vertical positions ───────────────────────────────
    # Ground surface: 80% up the base slab
    GROUND_Z = -BASE_HEIGHT + 0.80 * BASE_HEIGHT   # ≈ -0.061 m

    # Bedrock surface: 15% up the lower block
    lb_top = -(BASE_HEIGHT + LB_HEIGHT)             # top of lower block
    BEDROCK_Z = lb_top - LBLOCK_H + 0.20 * LBLOCK_H  # 20% up the lower block

    TERRAIN_DEPTH = GROUND_Z - BEDROCK_Z            # ≈ 0.605 m

    # ── Create subdivided grid at ground surface ─────────────────
    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=GRID_SUBDIVS,
        y_subdivisions=GRID_SUBDIVS,
        size=TERRAIN_RADIUS * 2,
        location=(0, 0, GROUND_Z))
    terrain = bpy.context.active_object
    terrain.name = "Terrain"

    # ── Displace top surface: dome + coherent noise ──────────────
    bm = bmesh.new()
    bm.from_mesh(terrain.data)

    # Simple multi-octave coherent noise using summed sine waves.
    # Each octave uses a different direction vector, giving organic
    # variation without needing external noise libraries.
    def terrain_noise(x, y):
        value = 0.0
        freq = NOISE_SCALE
        amp = NOISE_STRENGTH
        for i in range(NOISE_OCTAVES):
            # Golden-angle separated direction vectors
            angle = i * 2.399      # ~137.5° in radians
            dx = math.cos(angle)
            dy = math.sin(angle)
            value += amp * math.sin(freq * (dx * x + dy * y) + i * 7.3)
            freq *= 2.0
            amp *= 0.5
        return value

    for v in bm.verts:
        r = math.sqrt(v.co.x ** 2 + v.co.y ** 2)
        t = min(r / TERRAIN_RADIUS, 1.0)

        # Parabolic dome: highest at centre, drops DOME_HEIGHT at edge
        dome = -DOME_HEIGHT * t * t

        # Coherent noise for natural undulation
        noise_val = terrain_noise(v.co.x, v.co.y)

        # Protect the area immediately around the base slab from big
        # undulations — blend noise to zero near the centre
        slab_fade = max(0.0, min(1.0,
            (r - BASE_TOP_HW * 1.5) / (BASE_TOP_HW * 0.5)))

        v.co.z = dome + noise_val * slab_fade

    bm.to_mesh(terrain.data)
    bm.free()
    terrain.data.update()

    # ── Solidify downward to create volume ───────────────────────
    activate(terrain)
    mod = terrain.modifiers.new("Solidify", 'SOLIDIFY')
    mod.thickness = TERRAIN_DEPTH
    mod.offset = -1.0      # extrude entirely downward from top surface
    bpy.ops.object.modifier_apply(modifier="Solidify")

    # ── Trim to a circle (remove corner vertices) ────────────────
    bm = bmesh.new()
    bm.from_mesh(terrain.data)
    bm.verts.ensure_lookup_table()

    # Tag vertices outside the radius on the TOP surface for removal.
    # After solidify, top surface verts are at the displaced Z,
    # bottom verts are TERRAIN_DEPTH below.  We dissolve columns
    # whose XY distance exceeds the radius.
    to_remove = []
    for v in bm.verts:
        r = math.sqrt(v.co.x ** 2 + v.co.y ** 2)
        if r > TERRAIN_RADIUS * 0.98:     # slight inset for clean edge
            to_remove.append(v)

    if to_remove:
        bmesh.ops.delete(bm, geom=to_remove, context='VERTS')

    bm.to_mesh(terrain.data)
    bm.free()
    terrain.data.update()

    # ── Boolean cut for the base slab ────────────────────────────
    # Only cut the hole where the base slab actually sits — from
    # above the ground surface down to the slab bottom.  Below
    # that, the terrain remains solid (soil/bedrock wrapping around
    # the lower box and lower block).
    cut_top_z  = GROUND_Z + 0.05             # above surface for clean cut
    cut_btm_z  = -BASE_HEIGHT - 0.01         # just below slab bottom
    cut_height = cut_top_z - cut_btm_z
    hw_top = BASE_TOP_HW + CUT_MARGIN        # slab width at top
    hw_btm = BASE_BTM_HW + CUT_MARGIN        # slab width at bottom
    cutter = make_frustum(
        "_terrain_cut", hw_btm, hw_top, cut_height,
        base_z=cut_btm_z)
    boolean_cut(terrain, cutter)

    # ── Fix normals & mark top-surface faces ───────────────────────
    # The Boolean solver can leave normals inconsistent, which breaks
    # any downstream normal-based tests (GN scatter selection, density
    # attribute).  We fix that here and additionally store an explicit
    # face-domain boolean "IsTopFace" based on geometric proximity to
    # the known dome equation — completely independent of normals.
    bm = bmesh.new()
    bm.from_mesh(terrain.data)

    # 1. Recalculate normals so shading is correct and the density
    #    attribute in build_grass() (which checks vertex normals) works.
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bm.to_mesh(terrain.data)
    bm.free()
    terrain.data.update()

    # 2. Store a face-domain boolean attribute "IsTopFace".
    #    For each face we compare its centre Z against the expected
    #    dome height at that XY radius.  Top-surface faces sit close
    #    to the dome equation; bottom/rim faces are far below it.
    TOP_Z_TOLERANCE = max(0.25, NOISE_STRENGTH * 4)  # generous margin
    attr_top = terrain.data.attributes.get("IsTopFace")
    if attr_top is None:
        attr_top = terrain.data.attributes.new(
            name="IsTopFace", type='BOOLEAN', domain='FACE')

    mesh_data = terrain.data
    mesh_data.calc_loop_triangles()          # ensure face data is fresh

    for fi, face in enumerate(mesh_data.polygons):
        cx, cy, cz = face.center
        r = math.sqrt(cx * cx + cy * cy)
        t = min(r / TERRAIN_RADIUS, 1.0)
        expected_z = GROUND_Z + (-DOME_HEIGHT * t * t)
        attr_top.data[fi].value = (cz > expected_z - TOP_Z_TOLERANCE)

    assign(terrain, M['terrain'])
    smooth(terrain)
    return terrain


def build_landscape_ring(M):
    """Large surrounding countryside to fill the gap between the hilltop
    dome and the far horizon.

    An efficient radial mesh (concentric rings with increasing spacing)
    extends from just inside the terrain dome edge out to ~200 m.  The
    surface continues the dome's downhill slope then gradually levels off,
    simulating a broad hilltop viewed from the summit.  A procedural
    patchwork-fields material fades into atmospheric haze at distance.

    TUNEABLE PARAMETERS
    -------------------
    INNER_R         — inner radius (overlaps terrain dome edge slightly)
    OUTER_R         — outer radius (far enough for low camera angles)
    N_ANGULAR       — vertices per ring (angular resolution)
    SLOPE_RATE      — initial downhill slope (m drop per m outward)
    SLOPE_DECAY     — how quickly the slope flattens (higher = faster)
    MAX_DROP        — maximum height drop at the outer edge (metres)
    UNDULATION_AMP  — amplitude of gentle terrain undulation
    UNDULATION_FREQ — spatial frequency of undulation
    """
    print("  Landscape ring ...")

    # ── TUNEABLE VALUES ──────────────────────────────────────────
    INNER_R         = 4.6         # slightly inside terrain dome edge
    OUTER_R         = 200.0       # far horizon fill
    N_ANGULAR       = 64          # vertices per ring
    SLOPE_RATE      = 0.10        # initial slope: 10 cm drop per metre
    SLOPE_DECAY     = 0.04        # decay rate (1/e distance ≈ 25 m)
    MAX_DROP        = 8.0         # total drop to far edge (metres)
    UNDULATION_AMP  = 0.3         # gentle rolling hills (metres)
    UNDULATION_FREQ = 0.08        # spatial frequency of undulation
    # ─────────────────────────────────────────────────────────────

    # Terrain dome edge height — derived from the module-level
    # TERRAIN_RADIUS and DOME_HEIGHT (shared with build_terrain).
    GROUND_Z = -BASE_HEIGHT + 0.80 * BASE_HEIGHT   # ≈ -0.061
    t_edge = INNER_R / TERRAIN_RADIUS
    EDGE_Z = GROUND_Z + (-DOME_HEIGHT * t_edge * t_edge)

    # ── Build radial mesh with logarithmically spaced rings ───────
    # Inner rings are close together (smooth join to dome); outer rings
    # are widely spaced (far-field detail irrelevant due to haze).
    ring_radii = [INNER_R]
    r = INNER_R
    dr = 0.3          # initial ring spacing (metres)
    while r < OUTER_R:
        r += dr
        ring_radii.append(min(r, OUTER_R))
        dr *= 1.25     # increase spacing outward
    n_rings = len(ring_radii)

    # Height profile: exponential decay slope + undulation
    def landscape_z(r_val, angle):
        # Smooth continuation of dome slope, decaying to flat
        dist_from_edge = max(0.0, r_val - INNER_R)
        drop = (SLOPE_RATE / SLOPE_DECAY) * (
            1.0 - math.exp(-SLOPE_DECAY * dist_from_edge))
        drop = min(drop, MAX_DROP)

        # Gentle rolling undulation (sum of two sine waves)
        x = r_val * math.cos(angle)
        y = r_val * math.sin(angle)
        und = UNDULATION_AMP * (
            0.6 * math.sin(UNDULATION_FREQ * (x * 1.0 + y * 0.7) + 1.3)
            + 0.4 * math.sin(UNDULATION_FREQ * 1.7 * (x * 0.6 - y * 1.0) + 4.1)
        )
        # Fade undulation in (zero at inner edge, full beyond 20 m)
        und_fade = min(1.0, dist_from_edge / 15.0)

        return EDGE_Z - drop + und * und_fade

    bm = bmesh.new()

    # Create vertex rings
    vert_rings = []
    for ri, rad in enumerate(ring_radii):
        ring_verts = []
        for ai in range(N_ANGULAR):
            angle = 2.0 * math.pi * ai / N_ANGULAR
            x = rad * math.cos(angle)
            y = rad * math.sin(angle)
            z = landscape_z(rad, angle)
            ring_verts.append(bm.verts.new((x, y, z)))
        vert_rings.append(ring_verts)

    # Create faces between adjacent rings
    for ri in range(n_rings - 1):
        inner_ring = vert_rings[ri]
        outer_ring = vert_rings[ri + 1]
        for ai in range(N_ANGULAR):
            ai_next = (ai + 1) % N_ANGULAR
            # Quad: inner[ai], inner[ai+1], outer[ai+1], outer[ai]
            bm.faces.new([
                inner_ring[ai],
                inner_ring[ai_next],
                outer_ring[ai_next],
                outer_ring[ai],
            ])

    bm.normal_update()

    mesh = bpy.data.meshes.new("Landscape")
    bm.to_mesh(mesh)
    bm.free()

    landscape = bpy.data.objects.new("Landscape", mesh)
    bpy.context.collection.objects.link(landscape)

    assign(landscape, M['landscape'])
    smooth(landscape)
    return landscape


def build_grass():
    """Scatter grass blade instances over the terrain via Geometry Nodes.

    Uses Blender 4.x Geometry Nodes (Distribute Points on Faces →
    Instance on Points) rather than the legacy particle system, giving
    reliable viewport and render display without visibility-flag quirks.

    Grass density varies with distance from the pillar: bare near the
    base (worn earth, exposed rock), gradually filling in through a
    noisy transition zone to lush coverage at the hillside edges.
    The transition boundary is perturbed by coherent noise to avoid
    an artificial circular cut-off.

    TUNEABLE PARAMETERS
    -------------------
    BARE_RADIUS     — inner radius with no grass (base slab area)
    FULL_RADIUS     — full lush coverage from this radius outward
    GRASS_DENSITY   — points per m² at full coverage
    BLADE_H_MIN/MAX — blade height range (metres)
    BLADE_WIDTH     — blade width at base (metres)
    BLADE_VARIANTS  — number of different blade shapes
    NOISE_SCALE     — boundary perturbation spatial frequency
    NOISE_STRENGTH  — boundary perturbation amplitude (metres)
    GREEN_COL_A/B   — lush grass colour range
    DRY_COL         — sparse/dry tuft colour
    TRANSLUCENCY    — back-lit translucency fraction (0–1)
    """
    print("  Grass ...")

    terrain = bpy.data.objects.get("Terrain")
    if not terrain:
        print("    WARNING: Terrain not found — skipping grass.")
        return

    # ── TUNEABLE VALUES ──────────────────────────────────────────
    BARE_RADIUS    = 0.55     # no grass within 55 cm of centre
    FULL_RADIUS    = 2.50     # full coverage from 2.5 m outward
    GRASS_DENSITY  = 1400.0   # points per m² at full weight (main layer)
    GRASS_DENSITY_SHORT = 6000.0   # dense short under-layer
    WEED_DENSITY   = 4400.0     # broad-leaf weeds (sparse)
    FLOWER_DENSITY = 2.5      # flowers (very sparse)
    STONE_DENSITY  = 140.0     # visible stones (sparse)
    WEED_VARIANTS  = 4
    FLOWER_VARIANTS = 2
    STONE_VARIANTS = 6
    BLADE_H_MIN    = 0.025    # shortest blade (2.5 cm)
    BLADE_H_MAX    = 0.140    # tallest blade (14 cm)
    BLADE_WIDTH    = 0.005    # 5 mm wide at base
    BLADE_VARIANTS = 7        # distinct blade shapes (more = more short blades)
    NOISE_SCALE    = 1.5      # boundary noise frequency
    NOISE_STRENGTH = 0.5      # boundary noise ±50 cm
    SEED           = 42
    SCALE_MIN      = 0.55     # instance scale range (shorter bias)
    SCALE_MAX      = 1.20
    SCALE_BIAS     = 2.2      # >1 biases toward smaller blades
    SHORT_SCALE_MIN = 0.20
    SHORT_SCALE_MAX = 0.55
    SHORT_SCALE_BIAS = 3.2
    WEED_SCALE_MIN = 0.6
    WEED_SCALE_MAX = 1.4
    WEED_SCALE_BIAS = 1.6
    FLOWER_SCALE_MIN = 0.7
    FLOWER_SCALE_MAX = 1.4
    FLOWER_SCALE_BIAS = 2.0
    STONE_SCALE_MIN = 0.01
    STONE_SCALE_MAX = 0.05
    STONE_RAISE     = 0.05    # lift stones above ground surface (m)

    CLUMP_SCALE    = 0.25     # large-scale clump size
    CLUMP_DETAIL   = 2.0
    CLUMP_ROUGH    = 0.6
    CLUMP_MIN      = 0.20     # darkest clumps still keep some grass
    CLUMP_MAX      = 2.2

    UPWARD_MIN_Z   = 0.0      # only scatter on upward-facing surfaces
    UPWARD_FULL_Z  = 0.70     # full density by this normal Z
    UP_BLEND       = 0.65     # 0 = follow normals, 1 = world-up
    ALIGN_TO_NORMAL = 0.35    # 0 = vertical, 1 = follow surface normal
    TILT_MAX       = math.radians(7)  # random tilt angle
    WEED_EDGE_POWER = 1.5
    FLOWER_EDGE_POWER = 2.0
    STONE_EDGE_POWER = 1.3

    GREEN_COL_A    = (0.06, 0.14, 0.02, 1)   # dark rich green
    GREEN_COL_B    = (0.16, 0.24, 0.04, 1)   # lighter green
    DRY_COL        = (0.22, 0.18, 0.06, 1)   # dry yellowish
    TRANSLUCENCY   = 0.25    # 25 % back-lit translucency
    # ─────────────────────────────────────────────────────────────

    GROUND_Z = -BASE_HEIGHT + 0.80 * BASE_HEIGHT

    # ── Grass blade material ──────────────────────────────────────
    # Colour varies per instance via Object Info → Random, giving a
    # natural mix of green and dry blades.  A translucent component
    # lets light filter through back-lit blades realistically.
    grass_mat = bpy.data.materials.new("GrassBlade")
    grass_mat.use_nodes = True
    gt = grass_mat.node_tree
    gt.nodes.clear()

    obj_info = gt.nodes.new('ShaderNodeObjectInfo')
    obj_info.location = (-500, 0)

    cr_green = gt.nodes.new('ShaderNodeValToRGB')
    cr_green.location = (-300, 100)
    cr_green.label = "Green Variation"
    cr_green.color_ramp.elements[0].position = 0.0
    cr_green.color_ramp.elements[0].color = GREEN_COL_A
    cr_green.color_ramp.elements[1].position = 0.6
    cr_green.color_ramp.elements[1].color = GREEN_COL_B
    dry_stop = cr_green.color_ramp.elements.new(1.0)
    dry_stop.color = DRY_COL

    bsdf = gt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.location = (100, 100)
    bsdf.inputs['Roughness'].default_value = 0.75

    trans = gt.nodes.new('ShaderNodeBsdfTranslucent')
    trans.location = (100, -100)

    mix_sh = gt.nodes.new('ShaderNodeMixShader')
    mix_sh.location = (350, 0)
    mix_sh.inputs[0].default_value = TRANSLUCENCY

    mat_out = gt.nodes.new('ShaderNodeOutputMaterial')
    mat_out.location = (550, 0)

    gL = gt.links
    gL.new(obj_info.outputs['Random'], cr_green.inputs['Fac'])
    gL.new(cr_green.outputs['Color'], bsdf.inputs['Base Color'])
    gL.new(cr_green.outputs['Color'], trans.inputs['Color'])
    gL.new(bsdf.outputs['BSDF'], mix_sh.inputs[1])
    gL.new(trans.outputs['BSDF'], mix_sh.inputs[2])
    gL.new(mix_sh.outputs['Shader'], mat_out.inputs['Surface'])

    # ── Create blade mesh variants ────────────────────────────────
    # Each blade is a thin tapered quad with a slight forward bend.
    # Multiple variants with different heights and curvatures give
    # natural variation when picked randomly by the scatter system.
    grass_col = bpy.data.collections.new("_GrassBlades")
    bpy.context.scene.collection.children.link(grass_col)

    rng = random.Random(SEED)

    for i in range(BLADE_VARIANTS):
        # Bias the variant heights toward shorter blades
        t_var = (i / max(1, BLADE_VARIANTS - 1)) ** 2
        h = BLADE_H_MIN + (BLADE_H_MAX - BLADE_H_MIN) * t_var
        bend = rng.uniform(0.15, 0.55)
        hw = BLADE_WIDTH / 2

        bm = bmesh.new()
        SEGS = 3
        rows = []
        for s in range(SEGS + 1):
            t = s / SEGS
            z = h * t
            w = hw * (1.0 - t * 0.90)           # taper to 10 % at tip
            y_off = bend * h * t * t             # quadratic forward lean
            left = bm.verts.new((-w, y_off, z))
            right = bm.verts.new((w, y_off, z))
            rows.append((left, right))

        for s in range(SEGS):
            l0, r0 = rows[s]
            l1, r1 = rows[s + 1]
            bm.faces.new([l0, r0, r1, l1])

        mesh = bpy.data.meshes.new(f"_blade_{i}")
        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new(f"_blade_{i}", mesh)
        obj.data.materials.append(grass_mat)
        grass_col.objects.link(obj)

    # Hide source blades from viewport and render — Geometry Nodes
    # reads the mesh data directly regardless of visibility flags.
    for obj in grass_col.objects:
        obj.hide_viewport = True
        obj.hide_render = True

    # ── Weed & flower variants ───────────────────────────────────
    weed_mat = bpy.data.materials.new("WeedLeaf")
    weed_mat.use_nodes = True
    wt = weed_mat.node_tree
    wt.nodes.clear()
    w_bsdf = wt.nodes.new('ShaderNodeBsdfPrincipled')
    w_bsdf.inputs['Base Color'].default_value = (0.10, 0.18, 0.04, 1)
    w_bsdf.inputs['Roughness'].default_value = 0.80
    w_out = wt.nodes.new('ShaderNodeOutputMaterial')
    wt.links.new(w_bsdf.outputs['BSDF'], w_out.inputs['Surface'])

    flower_white = bpy.data.materials.new("FlowerDaisy")
    flower_white.use_nodes = True
    fw = flower_white.node_tree
    fw.nodes.clear()
    fw_bsdf = fw.nodes.new('ShaderNodeBsdfPrincipled')
    fw_bsdf.inputs['Base Color'].default_value = (0.85, 0.85, 0.80, 1)
    fw_bsdf.inputs['Roughness'].default_value = 0.70
    fw_out = fw.nodes.new('ShaderNodeOutputMaterial')
    fw.links.new(fw_bsdf.outputs['BSDF'], fw_out.inputs['Surface'])

    flower_yellow = bpy.data.materials.new("FlowerButtercup")
    flower_yellow.use_nodes = True
    fy = flower_yellow.node_tree
    fy.nodes.clear()
    fy_bsdf = fy.nodes.new('ShaderNodeBsdfPrincipled')
    fy_bsdf.inputs['Base Color'].default_value = (0.75, 0.65, 0.10, 1)
    fy_bsdf.inputs['Roughness'].default_value = 0.60
    fy_out = fy.nodes.new('ShaderNodeOutputMaterial')
    fy.links.new(fy_bsdf.outputs['BSDF'], fy_out.inputs['Surface'])

    stone_mat = bpy.data.materials.new("Pebble")
    stone_mat.use_nodes = True
    st = stone_mat.node_tree
    st.nodes.clear()
    st_bsdf = st.nodes.new('ShaderNodeBsdfPrincipled')
    st_bsdf.inputs['Base Color'].default_value = (0.30, 0.28, 0.26, 1)
    st_bsdf.inputs['Roughness'].default_value = 0.90
    st_out = st.nodes.new('ShaderNodeOutputMaterial')
    st.links.new(st_bsdf.outputs['BSDF'], st_out.inputs['Surface'])

    weed_col = bpy.data.collections.new("_WeedPlants")
    flower_col = bpy.data.collections.new("_FlowerPlants")
    stone_col = bpy.data.collections.new("_StonePebbles")
    bpy.context.scene.collection.children.link(weed_col)
    bpy.context.scene.collection.children.link(flower_col)
    bpy.context.scene.collection.children.link(stone_col)

    # Weed variants: 3-leaf clusters
    for i in range(WEED_VARIANTS):
        leaf_len = rng.uniform(0.03, 0.06)
        leaf_w   = rng.uniform(0.015, 0.03)
        tip_z    = rng.uniform(0.003, 0.008)

        bm = bmesh.new()
        for ang_deg in (0, 120, 240):
            a = math.radians(ang_deg + rng.uniform(-10, 10))
            ca, sa = math.cos(a), math.sin(a)
            pts = [
                (-leaf_w / 2, 0.0, 0.0),
                ( leaf_w / 2, 0.0, 0.0),
                ( 0.0,        leaf_len, tip_z),
                ( 0.0,        leaf_len * 0.15, 0.0),
            ]
            verts = []
            for x, y, z in pts:
                rx = x * ca - y * sa
                ry = x * sa + y * ca
                verts.append(bm.verts.new((rx, ry, z)))
            bm.faces.new(verts)

        mesh = bpy.data.meshes.new(f"_weed_{i}")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"_weed_{i}", mesh)
        obj.data.materials.append(weed_mat)
        weed_col.objects.link(obj)

    # Flower variants: simple discs (daisy + buttercup)
    for name, mat, r in (
        ("_daisy", flower_white, 0.018),
        ("_buttercup", flower_yellow, 0.016),
    ):
        bm = bmesh.new()
        center = bm.verts.new((0, 0, 0.004))
        ring = []
        N = 12
        for i in range(N):
            ang = 2 * math.pi * i / N
            ring.append(bm.verts.new((r * math.cos(ang), r * math.sin(ang), 0.004)))
        for i in range(N):
            bm.faces.new([center, ring[i], ring[(i + 1) % N]])
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        obj.data.materials.append(mat)
        flower_col.objects.link(obj)

    # Stone variants: low-poly pebbles (clearly 3D)
    for i in range(STONE_VARIANTS):
        r = rng.uniform(0.04, 0.12)
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r)
        # Flatten and jitter to sit on ground
        for v in bm.verts:
            v.co.x += rng.uniform(-r * 0.25, r * 0.25)
            v.co.y += rng.uniform(-r * 0.25, r * 0.25)
            v.co.z *= rng.uniform(0.7, 1.0)
            v.co.z *= rng.uniform(0.8, 1.4)
        # Shift so the lowest point sits on the ground (no half-buried discs)
        min_z = min(v.co.z for v in bm.verts)
        z_off = rng.uniform(0.005, 0.02)
        for v in bm.verts:
            v.co.z -= min_z
            v.co.z += z_off
        mesh = bpy.data.meshes.new(f"_stone_{i}")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"_stone_{i}", mesh)
        obj.data.materials.append(stone_mat)
        stone_col.objects.link(obj)

    # Hide source objects from viewport/render
    for col in (weed_col, flower_col, stone_col):
        for obj in col.objects:
            obj.hide_viewport = True
            obj.hide_render = True

    # ── Density gradient attribute ────────────────────────────────
    # Store the density as a *mesh attribute* (FLOAT, POINT domain).
    # Geometry Nodes reliably reads mesh attributes via Named Attribute.
    # (Vertex groups are not consistently exposed as attributes.)
    mesh_data = terrain.data
    attr = mesh_data.attributes.get("GrassDensity")
    if attr is None:
        attr = mesh_data.attributes.new(
            name="GrassDensity", type='FLOAT', domain='POINT')

    def _density_noise(x, y):
        """Multi-octave sine-wave noise (same method as terrain builder)."""
        value = 0.0
        freq = NOISE_SCALE
        amp = NOISE_STRENGTH
        for j in range(4):
            angle = j * 2.399
            dx = math.cos(angle)
            dy = math.sin(angle)
            value += amp * math.sin(freq * (dx * x + dy * y) + j * 7.3)
            freq *= 2.0
            amp *= 0.5
        return value

    # Use bmesh to compute normals (Mesh.calc_normals() is not available
    # in some Blender builds).
    bm = bmesh.new()
    bm.from_mesh(mesh_data)
    bm.normal_update()
    bm.verts.ensure_lookup_table()

    for i, v in enumerate(bm.verts):
        # Only assign density on upward-facing surfaces; this remains
        # stable even if the dome height changes.
        if v.normal.z < 0.05:
            attr.data[i].value = 0.0
            continue

        r = math.sqrt(v.co.x ** 2 + v.co.y ** 2)
        noise = _density_noise(v.co.x, v.co.y)

        bare_r = max(0.0, BARE_RADIUS + noise * 0.3)
        full_r = max(bare_r + 0.1, FULL_RADIUS + noise)

        if r <= bare_r:
            w = 0.0
        elif r >= full_r:
            w = 1.0
        else:
            frac = (r - bare_r) / (full_r - bare_r)
            w = frac * frac * (3.0 - 2.0 * frac)

        attr.data[i].value = w

    bm.free()
    mesh_data.update()

    # ── Geometry Nodes scatter ────────────────────────────────────
    # A node tree that distributes blade instances across the terrain
    # surface.  Geometry Nodes is the modern Blender 4.x approach —
    # more reliable than the legacy particle system for viewport and
    # render display.
    #
    # Node flow:
    #   Mesh → Distribute Points on Faces (density from vertex group)
    #        → Instance on Points (random blade from collection)
    #        → Rotate Instances (random facing direction)
    #        → Join Geometry (terrain mesh + grass instances)

    tree = bpy.data.node_groups.new("GrassScatter", 'GeometryNodeTree')
    tree.interface.new_socket(
        'Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    tree.interface.new_socket(
        'Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

    gn = tree.nodes       # geometry nodes
    gl = tree.links       # geometry links

    group_in = gn.new('NodeGroupInput')
    group_in.location = (-800, 0)

    group_out = gn.new('NodeGroupOutput')
    group_out.location = (600, 0)

    # ── Read GrassDensity attribute ──
    density_attr = gn.new('GeometryNodeInputNamedAttribute')
    density_attr.data_type = 'FLOAT'
    density_attr.inputs['Name'].default_value = "GrassDensity"
    density_attr.location = (-600, -150)

    # ── Upward-facing mask & slope factor ──
    normal_in = gn.new('GeometryNodeInputNormal')
    normal_in.location = (-800, -350)

    sep_n = gn.new('ShaderNodeSeparateXYZ')
    sep_n.location = (-600, -350)

    # Hard boolean gate: only scatter on top-surface faces.  The
    # "IsTopFace" attribute was computed in build_terrain() using the
    # known dome equation — it's True only for faces geometrically on
    # the upper terrain surface, regardless of normals.
    top_face_attr = gn.new('GeometryNodeInputNamedAttribute')
    top_face_attr.data_type = 'BOOLEAN'
    top_face_attr.inputs['Name'].default_value = "IsTopFace"
    top_face_attr.location = (-400, -280)

    slope_map = gn.new('ShaderNodeMapRange')
    slope_map.location = (-400, -350)
    slope_map.inputs['From Min'].default_value = UPWARD_MIN_Z
    slope_map.inputs['From Max'].default_value = UPWARD_FULL_Z
    slope_map.inputs['To Min'].default_value = 0.0
    slope_map.inputs['To Max'].default_value = 1.0
    slope_map.clamp = True

    # ── Orientation: blend normal with world-up ──
    up_vec = gn.new('ShaderNodeCombineXYZ')
    up_vec.location = (-800, -520)
    up_vec.inputs['Z'].default_value = 1.0

    mix_vec = gn.new('ShaderNodeMix')
    mix_vec.data_type = 'VECTOR'
    mix_vec.location = (-600, -520)
    mix_vec.inputs['Factor'].default_value = UP_BLEND

    norm_vec = gn.new('ShaderNodeVectorMath')
    norm_vec.operation = 'NORMALIZE'
    norm_vec.location = (-400, -520)

    align_vec = gn.new('FunctionNodeAlignEulerToVector')
    align_vec.location = (-200, -520)
    # Axis is a node property in Blender 4.x (not an input socket).
    try:
        align_vec.axis = 'Z'
    except Exception:
        pass

    align_factor = gn.new('ShaderNodeMath')
    align_factor.operation = 'MULTIPLY'
    align_factor.inputs[1].default_value = ALIGN_TO_NORMAL
    align_factor.location = (-400, -620)

    # ── Clump noise for density variation ──
    pos_in = gn.new('GeometryNodeInputPosition')
    pos_in.location = (-800, 150)

    clump_noise = gn.new('ShaderNodeTexNoise')
    clump_noise.location = (-600, 150)
    clump_noise.inputs['Scale'].default_value = CLUMP_SCALE
    clump_noise.inputs['Detail'].default_value = CLUMP_DETAIL
    clump_noise.inputs['Roughness'].default_value = CLUMP_ROUGH

    clump_map = gn.new('ShaderNodeMapRange')
    clump_map.location = (-400, 150)
    clump_map.inputs['From Min'].default_value = 0.0
    clump_map.inputs['From Max'].default_value = 1.0
    clump_map.inputs['To Min'].default_value = CLUMP_MIN
    clump_map.inputs['To Max'].default_value = CLUMP_MAX
    clump_map.clamp = True

    clump_mul = gn.new('ShaderNodeMath')
    clump_mul.operation = 'MULTIPLY'
    clump_mul.location = (-200, 150)

    slope_mul = gn.new('ShaderNodeMath')
    slope_mul.operation = 'MULTIPLY'
    slope_mul.location = (-50, 80)

    inv_density = gn.new('ShaderNodeMath')
    inv_density.operation = 'SUBTRACT'
    inv_density.inputs[0].default_value = 1.0
    inv_density.location = (-50, -340)

    weed_mul = gn.new('ShaderNodeMath')
    weed_mul.operation = 'MULTIPLY'
    weed_mul.location = (120, -340)

    weed_mul2 = gn.new('ShaderNodeMath')
    weed_mul2.operation = 'MULTIPLY'
    weed_mul2.location = (260, -340)

    weed_pow = gn.new('ShaderNodeMath')
    weed_pow.operation = 'POWER'
    weed_pow.inputs[1].default_value = WEED_EDGE_POWER
    weed_pow.location = (420, -340)

    flower_pow = gn.new('ShaderNodeMath')
    flower_pow.operation = 'POWER'
    flower_pow.inputs[1].default_value = FLOWER_EDGE_POWER
    flower_pow.location = (420, -420)

    stone_mul = gn.new('ShaderNodeMath')
    stone_mul.operation = 'MULTIPLY'
    stone_mul.location = (120, -500)

    stone_pow = gn.new('ShaderNodeMath')
    stone_pow.operation = 'POWER'
    stone_pow.inputs[1].default_value = STONE_EDGE_POWER
    stone_pow.location = (260, -500)

    # ── Scatter points on surface ──
    distribute = gn.new('GeometryNodeDistributePointsOnFaces')
    distribute.distribute_method = 'RANDOM'
    distribute.inputs['Density'].default_value = 1.0
    distribute.inputs['Seed'].default_value = SEED
    distribute.location = (-200, 0)

    # Density = attribute (0..1) * clump (0..2) * GRASS_DENSITY
    density_mul = gn.new('ShaderNodeMath')
    density_mul.operation = 'MULTIPLY'
    density_mul.inputs[1].default_value = GRASS_DENSITY
    density_mul.location = (0, -50)

    # Short-grass layer density
    distribute_short = gn.new('GeometryNodeDistributePointsOnFaces')
    distribute_short.distribute_method = 'RANDOM'
    distribute_short.inputs['Density'].default_value = 1.0
    distribute_short.inputs['Seed'].default_value = SEED + 101
    distribute_short.location = (-200, -200)

    density_mul_short = gn.new('ShaderNodeMath')
    density_mul_short.operation = 'MULTIPLY'
    density_mul_short.inputs[1].default_value = GRASS_DENSITY_SHORT
    density_mul_short.location = (0, -200)

    # Weeds / flowers / stones
    distribute_weed = gn.new('GeometryNodeDistributePointsOnFaces')
    distribute_weed.distribute_method = 'RANDOM'
    distribute_weed.inputs['Density'].default_value = 1.0
    distribute_weed.inputs['Seed'].default_value = SEED + 201
    distribute_weed.location = (-200, -420)

    distribute_flower = gn.new('GeometryNodeDistributePointsOnFaces')
    distribute_flower.distribute_method = 'RANDOM'
    distribute_flower.inputs['Density'].default_value = 1.0
    distribute_flower.inputs['Seed'].default_value = SEED + 301
    distribute_flower.location = (-200, -520)

    distribute_stone = gn.new('GeometryNodeDistributePointsOnFaces')
    distribute_stone.distribute_method = 'RANDOM'
    distribute_stone.inputs['Density'].default_value = 1.0
    distribute_stone.inputs['Seed'].default_value = SEED + 401
    distribute_stone.location = (-200, -620)

    density_mul_weed = gn.new('ShaderNodeMath')
    density_mul_weed.operation = 'MULTIPLY'
    density_mul_weed.inputs[1].default_value = WEED_DENSITY
    density_mul_weed.location = (0, -420)

    density_mul_flower = gn.new('ShaderNodeMath')
    density_mul_flower.operation = 'MULTIPLY'
    density_mul_flower.inputs[1].default_value = FLOWER_DENSITY
    density_mul_flower.location = (0, -520)

    density_mul_stone = gn.new('ShaderNodeMath')
    density_mul_stone.operation = 'MULTIPLY'
    density_mul_stone.inputs[1].default_value = STONE_DENSITY
    density_mul_stone.location = (0, -620)

    # ── Blade collection reference ──
    col_info = gn.new('GeometryNodeCollectionInfo')
    col_info.inputs[0].default_value = grass_col      # Collection
    col_info.inputs['Separate Children'].default_value = True
    col_info.inputs['Reset Children'].default_value = True
    col_info.location = (-400, -300)

    col_weed = gn.new('GeometryNodeCollectionInfo')
    col_weed.inputs[0].default_value = weed_col
    col_weed.inputs['Separate Children'].default_value = True
    col_weed.inputs['Reset Children'].default_value = True
    col_weed.location = (-400, -420)

    col_flower = gn.new('GeometryNodeCollectionInfo')
    col_flower.inputs[0].default_value = flower_col
    col_flower.inputs['Separate Children'].default_value = True
    col_flower.inputs['Reset Children'].default_value = True
    col_flower.location = (-400, -520)

    col_stone = gn.new('GeometryNodeCollectionInfo')
    col_stone.inputs[0].default_value = stone_col
    col_stone.inputs['Separate Children'].default_value = True
    col_stone.inputs['Reset Children'].default_value = True
    col_stone.location = (-400, -620)

    # ── Random integer for picking a blade variant ──
    # FunctionNodeRandomValue inputs by index:
    #   0/1 = Min/Max Vector, 2/3 = Min/Max Float,
    #   4/5 = Min/Max Int, 7 = ID, 8 = Seed
    # Outputs: 0 = Vector, 1 = Float, 2 = Int, 3 = Bool
    rand_idx = gn.new('FunctionNodeRandomValue')
    rand_idx.data_type = 'INT'
    rand_idx.inputs[4].default_value = 0                   # Min Int
    rand_idx.inputs[5].default_value = BLADE_VARIANTS - 1  # Max Int
    rand_idx.location = (-200, -250)

    rand_idx_weed = gn.new('FunctionNodeRandomValue')
    rand_idx_weed.data_type = 'INT'
    rand_idx_weed.inputs[4].default_value = 0
    rand_idx_weed.inputs[5].default_value = WEED_VARIANTS - 1
    rand_idx_weed.location = (-200, -420)

    rand_idx_flower = gn.new('FunctionNodeRandomValue')
    rand_idx_flower.data_type = 'INT'
    rand_idx_flower.inputs[4].default_value = 0
    rand_idx_flower.inputs[5].default_value = FLOWER_VARIANTS - 1
    rand_idx_flower.location = (-200, -520)

    rand_idx_stone = gn.new('FunctionNodeRandomValue')
    rand_idx_stone.data_type = 'INT'
    rand_idx_stone.inputs[4].default_value = 0
    rand_idx_stone.inputs[5].default_value = STONE_VARIANTS - 1
    rand_idx_stone.location = (-200, -620)

    # ── Instance blade meshes at scattered points ──
    instance_on = gn.new('GeometryNodeInstanceOnPoints')
    instance_on.inputs['Pick Instance'].default_value = True
    instance_on.location = (150, 0)

    instance_on_short = gn.new('GeometryNodeInstanceOnPoints')
    instance_on_short.inputs['Pick Instance'].default_value = True
    instance_on_short.location = (150, -200)

    instance_on_weed = gn.new('GeometryNodeInstanceOnPoints')
    instance_on_weed.inputs['Pick Instance'].default_value = True
    instance_on_weed.location = (150, -420)

    instance_on_flower = gn.new('GeometryNodeInstanceOnPoints')
    instance_on_flower.inputs['Pick Instance'].default_value = True
    instance_on_flower.location = (150, -520)

    instance_on_stone = gn.new('GeometryNodeInstanceOnPoints')
    instance_on_stone.inputs['Pick Instance'].default_value = True
    instance_on_stone.location = (150, -620)

    # ── Random facing direction (rotate around local Z) ──
    rand_rot = gn.new('FunctionNodeRandomValue')
    rand_rot.data_type = 'FLOAT'
    rand_rot.inputs[2].default_value = 0.0                 # Min Float
    rand_rot.inputs[3].default_value = 2 * math.pi         # Max Float
    rand_rot.location = (0, -450)

    axis_rot = gn.new('FunctionNodeAxisAngleToRotation')
    axis_rot.inputs['Axis'].default_value = (0, 0, 1)
    axis_rot.location = (150, -450)

    rotate = gn.new('GeometryNodeRotateInstances')
    rotate.inputs['Local Space'].default_value = True
    rotate.location = (350, 0)

    rotate_short = gn.new('GeometryNodeRotateInstances')
    rotate_short.inputs['Local Space'].default_value = True
    rotate_short.location = (350, -200)

    rotate_weed = gn.new('GeometryNodeRotateInstances')
    rotate_weed.inputs['Local Space'].default_value = True
    rotate_weed.location = (350, -420)

    rotate_flower = gn.new('GeometryNodeRotateInstances')
    rotate_flower.inputs['Local Space'].default_value = True
    rotate_flower.location = (350, -520)

    rotate_stone = gn.new('GeometryNodeRotateInstances')
    rotate_stone.inputs['Local Space'].default_value = True
    rotate_stone.location = (350, -620)

    translate_stone = gn.new('GeometryNodeTranslateInstances')
    translate_stone.location = (520, -620)
    translate_stone.inputs['Translation'].default_value = (0.0, 0.0, STONE_RAISE)

    # ── Random tilt (small X/Y rotation) ──
    rand_tilt_x = gn.new('FunctionNodeRandomValue')
    rand_tilt_x.data_type = 'FLOAT'
    rand_tilt_x.inputs[2].default_value = -TILT_MAX
    rand_tilt_x.inputs[3].default_value = TILT_MAX
    rand_tilt_x.location = (0, -520)

    rand_tilt_y = gn.new('FunctionNodeRandomValue')
    rand_tilt_y.data_type = 'FLOAT'
    rand_tilt_y.inputs[2].default_value = -TILT_MAX
    rand_tilt_y.inputs[3].default_value = TILT_MAX
    rand_tilt_y.location = (0, -560)

    tilt_vec = gn.new('ShaderNodeCombineXYZ')
    tilt_vec.location = (150, -540)

    rotate_tilt = gn.new('GeometryNodeRotateInstances')
    rotate_tilt.inputs['Local Space'].default_value = True
    rotate_tilt.location = (520, 0)

    rotate_tilt_short = gn.new('GeometryNodeRotateInstances')
    rotate_tilt_short.inputs['Local Space'].default_value = True
    rotate_tilt_short.location = (520, -200)

    # ── Scale bias toward shorter blades ──
    rand_scale = gn.new('FunctionNodeRandomValue')
    rand_scale.data_type = 'FLOAT'
    rand_scale.inputs[2].default_value = 0.0                # Min Float
    rand_scale.inputs[3].default_value = 1.0                # Max Float
    rand_scale.location = (0, -600)

    scale_pow = gn.new('ShaderNodeMath')
    scale_pow.operation = 'POWER'
    scale_pow.inputs[1].default_value = SCALE_BIAS
    scale_pow.location = (150, -600)

    scale_map = gn.new('ShaderNodeMapRange')
    scale_map.inputs['From Min'].default_value = 0.0
    scale_map.inputs['From Max'].default_value = 1.0
    scale_map.inputs['To Min'].default_value = SCALE_MIN
    scale_map.inputs['To Max'].default_value = SCALE_MAX
    scale_map.clamp = True
    scale_map.location = (350, -600)

    scale_vec = gn.new('ShaderNodeCombineXYZ')
    scale_vec.location = (550, -600)

    # Short-grass scale chain
    rand_scale_s = gn.new('FunctionNodeRandomValue')
    rand_scale_s.data_type = 'FLOAT'
    rand_scale_s.inputs[2].default_value = 0.0
    rand_scale_s.inputs[3].default_value = 1.0
    rand_scale_s.location = (0, -750)

    scale_pow_s = gn.new('ShaderNodeMath')
    scale_pow_s.operation = 'POWER'
    scale_pow_s.inputs[1].default_value = SHORT_SCALE_BIAS
    scale_pow_s.location = (150, -750)

    scale_map_s = gn.new('ShaderNodeMapRange')
    scale_map_s.inputs['From Min'].default_value = 0.0
    scale_map_s.inputs['From Max'].default_value = 1.0
    scale_map_s.inputs['To Min'].default_value = SHORT_SCALE_MIN
    scale_map_s.inputs['To Max'].default_value = SHORT_SCALE_MAX
    scale_map_s.clamp = True
    scale_map_s.location = (350, -750)

    scale_vec_s = gn.new('ShaderNodeCombineXYZ')
    scale_vec_s.location = (550, -750)

    # Weed scale
    rand_scale_w = gn.new('FunctionNodeRandomValue')
    rand_scale_w.data_type = 'FLOAT'
    rand_scale_w.inputs[2].default_value = 0.0
    rand_scale_w.inputs[3].default_value = 1.0
    rand_scale_w.location = (0, -900)

    scale_pow_w = gn.new('ShaderNodeMath')
    scale_pow_w.operation = 'POWER'
    scale_pow_w.inputs[1].default_value = WEED_SCALE_BIAS
    scale_pow_w.location = (150, -900)

    scale_map_w = gn.new('ShaderNodeMapRange')
    scale_map_w.inputs['From Min'].default_value = 0.0
    scale_map_w.inputs['From Max'].default_value = 1.0
    scale_map_w.inputs['To Min'].default_value = WEED_SCALE_MIN
    scale_map_w.inputs['To Max'].default_value = WEED_SCALE_MAX
    scale_map_w.clamp = True
    scale_map_w.location = (350, -900)

    scale_vec_w = gn.new('ShaderNodeCombineXYZ')
    scale_vec_w.location = (550, -900)

    # Flower scale
    rand_scale_f = gn.new('FunctionNodeRandomValue')
    rand_scale_f.data_type = 'FLOAT'
    rand_scale_f.inputs[2].default_value = 0.0
    rand_scale_f.inputs[3].default_value = 1.0
    rand_scale_f.location = (0, -1020)

    scale_pow_f = gn.new('ShaderNodeMath')
    scale_pow_f.operation = 'POWER'
    scale_pow_f.inputs[1].default_value = FLOWER_SCALE_BIAS
    scale_pow_f.location = (150, -1020)

    scale_map_f = gn.new('ShaderNodeMapRange')
    scale_map_f.inputs['From Min'].default_value = 0.0
    scale_map_f.inputs['From Max'].default_value = 1.0
    scale_map_f.inputs['To Min'].default_value = FLOWER_SCALE_MIN
    scale_map_f.inputs['To Max'].default_value = FLOWER_SCALE_MAX
    scale_map_f.clamp = True
    scale_map_f.location = (350, -1020)

    scale_vec_f = gn.new('ShaderNodeCombineXYZ')
    scale_vec_f.location = (550, -1020)

    # Stone scale
    rand_scale_t = gn.new('FunctionNodeRandomValue')
    rand_scale_t.data_type = 'FLOAT'
    rand_scale_t.inputs[2].default_value = 0.0
    rand_scale_t.inputs[3].default_value = 1.0
    rand_scale_t.location = (0, -1140)

    scale_map_t = gn.new('ShaderNodeMapRange')
    scale_map_t.inputs['From Min'].default_value = 0.0
    scale_map_t.inputs['From Max'].default_value = 1.0
    scale_map_t.inputs['To Min'].default_value = STONE_SCALE_MIN
    scale_map_t.inputs['To Max'].default_value = STONE_SCALE_MAX
    scale_map_t.clamp = True
    scale_map_t.location = (350, -1140)

    scale_vec_t = gn.new('ShaderNodeCombineXYZ')
    scale_vec_t.location = (550, -1140)

    realize = gn.new('GeometryNodeRealizeInstances')
    realize.location = (520, 0)

    realize_short = gn.new('GeometryNodeRealizeInstances')
    realize_short.location = (520, -200)

    realize_weed = gn.new('GeometryNodeRealizeInstances')
    realize_weed.location = (520, -420)

    realize_flower = gn.new('GeometryNodeRealizeInstances')
    realize_flower.location = (520, -520)

    realize_stone = gn.new('GeometryNodeRealizeInstances')
    realize_stone.location = (680, -620)

    set_mat_stone = gn.new('GeometryNodeSetMaterial')
    set_mat_stone.location = (820, -620)
    set_mat_stone.inputs['Material'].default_value = stone_mat

    # ── Combine terrain mesh + grass instances ──
    join = gn.new('GeometryNodeJoinGeometry')
    join.location = (700, 0)

    # ── Wire the node tree ──
    # Input mesh → scatter + passthrough to join
    gl.new(group_in.outputs[0], distribute.inputs['Mesh'])
    gl.new(group_in.outputs[0], distribute_short.inputs['Mesh'])
    gl.new(group_in.outputs[0], distribute_weed.inputs['Mesh'])
    gl.new(group_in.outputs[0], distribute_flower.inputs['Mesh'])
    gl.new(group_in.outputs[0], distribute_stone.inputs['Mesh'])
    gl.new(group_in.outputs[0], join.inputs['Geometry'])

    # Restrict all scatter to the top terrain surface only —
    # the IsTopFace boolean attribute (set in build_terrain from the
    # dome equation) excludes bedrock / rim faces entirely.
    gl.new(top_face_attr.outputs['Attribute'], distribute.inputs['Selection'])
    gl.new(top_face_attr.outputs['Attribute'], distribute_short.inputs['Selection'])
    gl.new(top_face_attr.outputs['Attribute'], distribute_weed.inputs['Selection'])
    gl.new(top_face_attr.outputs['Attribute'], distribute_flower.inputs['Selection'])
    gl.new(top_face_attr.outputs['Attribute'], distribute_stone.inputs['Selection'])

    # Upward-facing slope factor + orientation vector
    gl.new(normal_in.outputs['Normal'], sep_n.inputs['Vector'])
    gl.new(sep_n.outputs['Z'], slope_map.inputs['Value'])
    gl.new(normal_in.outputs['Normal'], mix_vec.inputs['B'])
    gl.new(up_vec.outputs['Vector'], mix_vec.inputs['A'])
    gl.new(slope_map.outputs['Result'], align_factor.inputs[0])
    gl.new(align_factor.outputs['Value'], mix_vec.inputs['Factor'])
    gl.new(mix_vec.outputs[2], norm_vec.inputs[0])
    gl.new(norm_vec.outputs['Vector'], align_vec.inputs['Vector'])

    # Clump noise
    gl.new(pos_in.outputs['Position'], clump_noise.inputs['Vector'])
    gl.new(clump_noise.outputs['Fac'], clump_map.inputs['Value'])
    gl.new(density_attr.outputs['Attribute'], clump_mul.inputs[0])
    gl.new(clump_map.outputs['Result'], clump_mul.inputs[1])
    gl.new(clump_mul.outputs['Value'], slope_mul.inputs[0])
    gl.new(slope_map.outputs['Result'], slope_mul.inputs[1])

    # Edge / centre masks for weeds, flowers, stones
    gl.new(density_attr.outputs['Attribute'], inv_density.inputs[1])
    gl.new(density_attr.outputs['Attribute'], weed_mul.inputs[0])
    gl.new(clump_map.outputs['Result'], weed_mul.inputs[1])
    gl.new(weed_mul.outputs['Value'], weed_mul2.inputs[0])
    gl.new(slope_map.outputs['Result'], weed_mul2.inputs[1])
    gl.new(weed_mul2.outputs['Value'], weed_pow.inputs[0])
    gl.new(weed_mul2.outputs['Value'], flower_pow.inputs[0])

    gl.new(inv_density.outputs['Value'], stone_mul.inputs[0])
    gl.new(slope_map.outputs['Result'], stone_mul.inputs[1])
    gl.new(stone_mul.outputs['Value'], stone_pow.inputs[0])

    # Attribute weight → density (main + short)
    gl.new(slope_mul.outputs['Value'], density_mul.inputs[0])
    gl.new(slope_mul.outputs['Value'], density_mul_short.inputs[0])
    gl.new(density_mul.outputs['Value'], distribute.inputs['Density'])
    gl.new(density_mul_short.outputs['Value'], distribute_short.inputs['Density'])

    gl.new(weed_pow.outputs['Value'], density_mul_weed.inputs[0])
    gl.new(flower_pow.outputs['Value'], density_mul_flower.inputs[0])
    gl.new(stone_pow.outputs['Value'], density_mul_stone.inputs[0])
    gl.new(density_mul_weed.outputs['Value'], distribute_weed.inputs['Density'])
    gl.new(density_mul_flower.outputs['Value'], distribute_flower.inputs['Density'])
    gl.new(density_mul_stone.outputs['Value'], distribute_stone.inputs['Density'])

    # Scattered points → instance placement (main)
    gl.new(distribute.outputs['Points'], instance_on.inputs['Points'])
    gl.new(align_vec.outputs['Rotation'], instance_on.inputs['Rotation'])
    gl.new(col_info.outputs[0], instance_on.inputs['Instance'])
    gl.new(rand_idx.outputs[2], instance_on.inputs['Instance Index'])

    # Scattered points → instance placement (short)
    gl.new(distribute_short.outputs['Points'], instance_on_short.inputs['Points'])
    gl.new(align_vec.outputs['Rotation'], instance_on_short.inputs['Rotation'])
    gl.new(col_info.outputs[0], instance_on_short.inputs['Instance'])
    gl.new(rand_idx.outputs[2], instance_on_short.inputs['Instance Index'])

    gl.new(distribute_weed.outputs['Points'], instance_on_weed.inputs['Points'])
    gl.new(align_vec.outputs['Rotation'], instance_on_weed.inputs['Rotation'])
    gl.new(col_weed.outputs[0], instance_on_weed.inputs['Instance'])
    gl.new(rand_idx_weed.outputs[2], instance_on_weed.inputs['Instance Index'])

    gl.new(distribute_flower.outputs['Points'], instance_on_flower.inputs['Points'])
    gl.new(align_vec.outputs['Rotation'], instance_on_flower.inputs['Rotation'])
    gl.new(col_flower.outputs[0], instance_on_flower.inputs['Instance'])
    gl.new(rand_idx_flower.outputs[2], instance_on_flower.inputs['Instance Index'])

    gl.new(distribute_stone.outputs['Points'], instance_on_stone.inputs['Points'])
    gl.new(align_vec.outputs['Rotation'], instance_on_stone.inputs['Rotation'])
    gl.new(col_stone.outputs[0], instance_on_stone.inputs['Instance'])
    gl.new(rand_idx_stone.outputs[2], instance_on_stone.inputs['Instance Index'])

    # Main instances → rotation → tilt → realize
    gl.new(instance_on.outputs['Instances'], rotate.inputs['Instances'])
    gl.new(rand_rot.outputs[1], axis_rot.inputs['Angle'])
    gl.new(axis_rot.outputs['Rotation'], rotate.inputs['Rotation'])
    gl.new(rand_scale.outputs[1], scale_pow.inputs[0])
    gl.new(scale_pow.outputs['Value'], scale_map.inputs['Value'])
    gl.new(scale_map.outputs['Result'], scale_vec.inputs['X'])
    gl.new(scale_map.outputs['Result'], scale_vec.inputs['Y'])
    gl.new(scale_map.outputs['Result'], scale_vec.inputs['Z'])
    gl.new(scale_vec.outputs['Vector'], instance_on.inputs['Scale'])
    gl.new(rand_tilt_x.outputs[1], tilt_vec.inputs['X'])
    gl.new(rand_tilt_y.outputs[1], tilt_vec.inputs['Y'])
    gl.new(tilt_vec.outputs['Vector'], rotate_tilt.inputs['Rotation'])
    gl.new(rotate.outputs['Instances'], rotate_tilt.inputs['Instances'])
    gl.new(rotate_tilt.outputs['Instances'], realize.inputs['Geometry'])

    # Short instances → rotation → tilt → realize
    gl.new(instance_on_short.outputs['Instances'], rotate_short.inputs['Instances'])
    gl.new(axis_rot.outputs['Rotation'], rotate_short.inputs['Rotation'])
    gl.new(rand_scale_s.outputs[1], scale_pow_s.inputs[0])
    gl.new(scale_pow_s.outputs['Value'], scale_map_s.inputs['Value'])
    gl.new(scale_map_s.outputs['Result'], scale_vec_s.inputs['X'])
    gl.new(scale_map_s.outputs['Result'], scale_vec_s.inputs['Y'])
    gl.new(scale_map_s.outputs['Result'], scale_vec_s.inputs['Z'])
    gl.new(scale_vec_s.outputs['Vector'], instance_on_short.inputs['Scale'])
    gl.new(tilt_vec.outputs['Vector'], rotate_tilt_short.inputs['Rotation'])
    gl.new(rotate_short.outputs['Instances'], rotate_tilt_short.inputs['Instances'])
    gl.new(rotate_tilt_short.outputs['Instances'], realize_short.inputs['Geometry'])

    gl.new(axis_rot.outputs['Rotation'], rotate_weed.inputs['Rotation'])
    gl.new(axis_rot.outputs['Rotation'], rotate_flower.inputs['Rotation'])
    gl.new(axis_rot.outputs['Rotation'], rotate_stone.inputs['Rotation'])

    gl.new(rand_scale_w.outputs[1], scale_pow_w.inputs[0])
    gl.new(scale_pow_w.outputs['Value'], scale_map_w.inputs['Value'])
    gl.new(scale_map_w.outputs['Result'], scale_vec_w.inputs['X'])
    gl.new(scale_map_w.outputs['Result'], scale_vec_w.inputs['Y'])
    gl.new(scale_map_w.outputs['Result'], scale_vec_w.inputs['Z'])
    gl.new(scale_vec_w.outputs['Vector'], instance_on_weed.inputs['Scale'])
    gl.new(instance_on_weed.outputs['Instances'], rotate_weed.inputs['Instances'])
    gl.new(rotate_weed.outputs['Instances'], realize_weed.inputs['Geometry'])

    gl.new(rand_scale_f.outputs[1], scale_pow_f.inputs[0])
    gl.new(scale_pow_f.outputs['Value'], scale_map_f.inputs['Value'])
    gl.new(scale_map_f.outputs['Result'], scale_vec_f.inputs['X'])
    gl.new(scale_map_f.outputs['Result'], scale_vec_f.inputs['Y'])
    gl.new(scale_map_f.outputs['Result'], scale_vec_f.inputs['Z'])
    gl.new(scale_vec_f.outputs['Vector'], instance_on_flower.inputs['Scale'])
    gl.new(instance_on_flower.outputs['Instances'], rotate_flower.inputs['Instances'])
    gl.new(rotate_flower.outputs['Instances'], realize_flower.inputs['Geometry'])

    gl.new(scale_map_t.outputs['Result'], scale_vec_t.inputs['X'])
    gl.new(scale_map_t.outputs['Result'], scale_vec_t.inputs['Y'])
    gl.new(scale_map_t.outputs['Result'], scale_vec_t.inputs['Z'])
    gl.new(rand_scale_t.outputs[1], scale_map_t.inputs['Value'])
    gl.new(scale_vec_t.outputs['Vector'], instance_on_stone.inputs['Scale'])
    gl.new(instance_on_stone.outputs['Instances'], rotate_stone.inputs['Instances'])
    gl.new(rotate_stone.outputs['Instances'], translate_stone.inputs['Instances'])
    gl.new(translate_stone.outputs['Instances'], realize_stone.inputs['Geometry'])

    # Join all geometry and output
    gl.new(realize.outputs['Geometry'], join.inputs['Geometry'])
    gl.new(realize_short.outputs['Geometry'], join.inputs['Geometry'])
    gl.new(realize_weed.outputs['Geometry'], join.inputs['Geometry'])
    gl.new(realize_flower.outputs['Geometry'], join.inputs['Geometry'])
    gl.new(realize_stone.outputs['Geometry'], set_mat_stone.inputs['Geometry'])
    gl.new(set_mat_stone.outputs['Geometry'], join.inputs['Geometry'])
    gl.new(join.outputs['Geometry'], group_out.inputs[0])

    # ── Apply the Geometry Nodes modifier to the terrain ──
    gn_mod = terrain.modifiers.new("Grass", 'NODES')
    gn_mod.node_group = tree

    print(f"    Density: {GRASS_DENSITY:.0f} pts/m², "
          f"{BLADE_VARIANTS} blade variants")
    print(f"    Bare r < {BARE_RADIUS} m → full r > {FULL_RADIUS} m")
    print(f"    Noise: scale={NOISE_SCALE}, strength=±{NOISE_STRENGTH} m")

    return terrain


# =====================================================================
# SCENE SETUP
# =====================================================================

def setup_scene():
    """Add camera, procedural sky, sun light, fog, and configure render.

    Lighting strategy — fully procedural, no external HDRI:
      - Nishita physically-based sky provides ambient fill, sky colour,
        and reflections in brass/steel surfaces.  Heavy dust and air
        density settings wash it out to an overcast look; desaturation
        and cloud noise complete the British-gloom aesthetic.
      - Sun lamp aligned to rake across the flush bracket (+Y face)
        so the logo bevels catch highlights.
      - Sighting-hole point light for box interior illumination.
      - Procedural cloud modulation adds local variation to suggest
        uneven overcast thickness without external assets.

    TUNEABLE PARAMETERS
    -------------------
    Sky atmosphere
        SKY_AIR_DENSITY   — Rayleigh scattering (higher = denser blue)
        SKY_DUST_DENSITY  — Mie scattering / haze (higher = whiter)
        SKY_OZONE_DENSITY — warm tinge at the horizon
        SKY_SUN_INTENSITY — brightness of the sun disc in the sky
        SKY_SUN_SIZE      — apparent size of the sun disc (degrees)
        SKY_SATURATION    — colour saturation (0 = greyscale, 1 = full)
        SKY_VALUE         — overall brightness tweak
        SKY_STRENGTH      — world background emission strength
    Cloud modulation
        CLOUD_SCALE       — spatial frequency (lower = bigger patches)
        CLOUD_DETAIL      — fractal octaves in the noise
        CLOUD_ROUGHNESS   — inter-octave amplitude ratio
        CLOUD_AMOUNT      — brightness variation amplitude
        CLOUD_CONTRAST    — cloud pattern contrast (higher = punchier)
    Sun lamp
        SUN_ENERGY        — sun lamp intensity
        SUN_ALTITUDE      — elevation angle (degrees from horizontal)
        SUN_AZIMUTH       — compass bearing (0° = +X, 90° = +Y)
    """
    print("  Scene setup ...")

    # ── TUNEABLE VALUES ──────────────────────────────────────────

    # Nishita sky — heavy atmosphere for washed-out overcast look
    SKY_AIR_DENSITY    = 3.0       # dense Rayleigh scattering
    SKY_DUST_DENSITY   = 6.0       # thick Mie haze → overcast white-out
    SKY_OZONE_DENSITY  = 2.0       # warm horizon tinge
    SKY_SUN_INTENSITY  = 0.3       # dim, diffused sun disc
    SKY_SUN_SIZE       = 3.0       # bloated disc (degrees) — cloud-diffused
    SKY_SATURATION     = 0.25      # heavily desaturated — British gloom
    SKY_VALUE          = 0.50      # pull back washed-out highlights
    SKY_STRENGTH       = 0.60

    # Cloud noise overlay — large-scale noise modulates sky brightness
    CLOUD_SCALE        = 2.5       # spatial frequency
    CLOUD_DETAIL       = 6.0       # fractal octaves
    CLOUD_ROUGHNESS    = 0.6       # inter-octave amplitude ratio
    CLOUD_AMOUNT       = 0.38      # brightness variation ± (0 = none)
    CLOUD_CONTRAST     = 8.2       # emphasise local cloud-thickness variation

    SUN_ENERGY      = 1.2
    SUN_ALTITUDE    = 40          # degrees above horizon
    SUN_AZIMUTH     = 50          # degrees — between +X and +Y,
                                  # raking across the +Y flush bracket face

    # Below-horizon safety gradient — catches any gap between the
    # landscape ring edge and the sky.  Uses the ray direction Z
    # component: positive = above horizon, negative = below.
    HORIZON_UPPER   = 0.52        # blend starts just above true horizon
    HORIZON_LOWER   = -0.08       # fully landscape colour by this angle
    HORIZON_COL     = (0.52, 0.54, 0.50)   # overcast haze (match landscape)
    HORIZON_STRENGTH_RATIO = 1.0  # relative to SKY_STRENGTH
    # ─────────────────────────────────────────────────────────────

    # Camera — positioned to see the full pillar
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (2.0, -2.0, 1.0)
    cam_obj.rotation_euler = (math.radians(72), 0, math.radians(45))
    bpy.context.scene.camera = cam_obj

    # ── Procedural world shader ────────────────────────────────────
    # Unified Nishita sky for all ray types (camera, reflection,
    # diffuse, glossy) — no external HDRI required.  The sky is
    # desaturated and cloud-modulated to evoke overcast Britain.

    world = bpy.data.worlds.new("ProceduralSky")
    bpy.context.scene.world = world
    world.use_nodes = True
    wtree = world.node_tree
    wtree.nodes.clear()

    # ── Sky texture: Nishita atmospheric model ─────────────────────
    sky_tex = wtree.nodes.new('ShaderNodeTexSky')
    sky_tex.location = (-800, 200)
    sky_tex.sky_type = 'NISHITA'
    sky_tex.sun_elevation = math.radians(SUN_ALTITUDE)
    sky_tex.sun_rotation = math.radians(SUN_AZIMUTH)
    sky_tex.air_density = SKY_AIR_DENSITY
    sky_tex.dust_density = SKY_DUST_DENSITY
    sky_tex.ozone_density = SKY_OZONE_DENSITY
    sky_tex.sun_intensity = SKY_SUN_INTENSITY
    sky_tex.sun_size = math.radians(SKY_SUN_SIZE)
    sky_tex.altitude = 0

    # ── Desaturate — drain colour to match overcast Britain ────────
    hsv = wtree.nodes.new('ShaderNodeHueSaturation')
    hsv.location = (-600, 200)
    hsv.inputs['Saturation'].default_value = SKY_SATURATION
    hsv.inputs['Value'].default_value = SKY_VALUE

    # ── Cloud modulation ────────────────────────────────────────────
    # Large-scale 3D noise sampled from the viewing direction
    # modulates sky brightness, giving local variation that reads as
    # uneven cloud thickness.
    #
    # Approach: noise → MapRange [1−A, 1+A] → VectorMath SCALE on
    # the sky colour.  This avoids ShaderNodeMix whose Color socket
    # indices shift between Blender versions (Rotation sockets were
    # added in 4.1, pushing Color from [6]/[7] to [7]/[8]).
    tex_coord = wtree.nodes.new('ShaderNodeTexCoord')
    tex_coord.location = (-800, -100)

    cloud_noise = wtree.nodes.new('ShaderNodeTexNoise')
    cloud_noise.location = (-600, -100)
    cloud_noise.noise_dimensions = '3D'
    cloud_noise.inputs['Scale'].default_value = CLOUD_SCALE
    cloud_noise.inputs['Detail'].default_value = CLOUD_DETAIL
    cloud_noise.inputs['Roughness'].default_value = CLOUD_ROUGHNESS

    # Shape the noise for stronger local contrast:
    # noise -> centred (-0.5..0.5) -> contrast -> offset (+1.0)
    cloud_center = wtree.nodes.new('ShaderNodeMath')
    cloud_center.location = (-400, -100)
    cloud_center.operation = 'SUBTRACT'
    cloud_center.inputs[1].default_value = 0.5

    cloud_contrast = wtree.nodes.new('ShaderNodeMath')
    cloud_contrast.location = (-220, -100)
    cloud_contrast.operation = 'MULTIPLY'
    cloud_contrast.inputs[1].default_value = CLOUD_CONTRAST * CLOUD_AMOUNT

    cloud_offset = wtree.nodes.new('ShaderNodeMath')
    cloud_offset.location = (-40, -100)
    cloud_offset.operation = 'ADD'
    cloud_offset.inputs[1].default_value = 1.0

    # Multiply desaturated sky colour by the noise-driven brightness
    cloud_scale = wtree.nodes.new('ShaderNodeVectorMath')
    cloud_scale.location = (140, 200)
    cloud_scale.operation = 'SCALE'

    # ── Background + output ────────────────────────────────────────
    bg = wtree.nodes.new('ShaderNodeBackground')
    bg.location = (320, 200)
    bg.label = "Sky"
    bg.inputs['Strength'].default_value = SKY_STRENGTH

    # ── Below-horizon landscape gradient (safety net) ─────────────
    # If the camera ray looks below the horizon and sees past the
    # landscape ring, show hazy overcast green instead of black void.
    # Uses the Generated texture coordinates: in a world shader the
    # Generated output is the normalised ray direction, so Z > 0 is
    # above the horizon and Z < 0 is below.
    sep_ray = wtree.nodes.new('ShaderNodeSeparateXYZ')
    sep_ray.location = (-400, -400)

    horizon_mask = wtree.nodes.new('ShaderNodeMapRange')
    horizon_mask.location = (-200, -400)
    horizon_mask.inputs['From Min'].default_value = HORIZON_LOWER
    horizon_mask.inputs['From Max'].default_value = HORIZON_UPPER
    horizon_mask.inputs['To Min'].default_value = 1.0   # below = landscape
    horizon_mask.inputs['To Max'].default_value = 0.0   # above = sky
    horizon_mask.clamp = True

    land_bg = wtree.nodes.new('ShaderNodeBackground')
    land_bg.location = (320, -400)
    land_bg.label = "Horizon Haze"
    land_bg.inputs['Color'].default_value = (*HORIZON_COL, 1.0)
    land_bg.inputs['Strength'].default_value = SKY_STRENGTH * HORIZON_STRENGTH_RATIO

    mix_horizon = wtree.nodes.new('ShaderNodeMixShader')
    mix_horizon.location = (520, 200)

    output = wtree.nodes.new('ShaderNodeOutputWorld')
    output.location = (720, 200)

    # ── Wire everything up ─────────────────────────────────────────
    wL = wtree.links
    # Sky chain: Nishita → desaturate → cloud brightness modulation
    wL.new(sky_tex.outputs['Color'], hsv.inputs['Color'])
    wL.new(tex_coord.outputs['Generated'], cloud_noise.inputs['Vector'])
    wL.new(cloud_noise.outputs['Fac'], cloud_center.inputs[0])
    wL.new(cloud_center.outputs['Value'], cloud_contrast.inputs[0])
    wL.new(cloud_contrast.outputs['Value'], cloud_offset.inputs[0])
    wL.new(hsv.outputs['Color'], cloud_scale.inputs[0])           # Vector
    wL.new(cloud_offset.outputs['Value'], cloud_scale.inputs['Scale'])
    wL.new(cloud_scale.outputs['Vector'], bg.inputs['Color'])
    # Horizon detection: Generated Z → mask
    wL.new(tex_coord.outputs['Generated'], sep_ray.inputs['Vector'])
    wL.new(sep_ray.outputs['Z'], horizon_mask.inputs['Value'])
    # Mix sky (above) with haze (below), then to output
    wL.new(horizon_mask.outputs['Result'], mix_horizon.inputs['Fac'])
    wL.new(bg.outputs['Background'], mix_horizon.inputs[1])
    wL.new(land_bg.outputs['Background'], mix_horizon.inputs[2])
    wL.new(mix_horizon.outputs['Shader'], output.inputs['Surface'])

    # ── Sun light ─────────────────────────────────────────────────
    # Direction: shining from the azimuth/altitude towards the origin.
    # The flush bracket is on the +Y face.  An azimuth of ~50° puts
    # the sun roughly from the +X/+Y quadrant, raking obliquely
    # across the bracket face so the bevelled logo edges catch bright
    # highlights on one side and fall into shadow on the other.
    #
    # Blender's sun lamp direction is set by its rotation; we convert
    # altitude/azimuth to Euler angles.  The sun direction vector is
    # (-cos(alt)*cos(az), -cos(alt)*sin(az), -sin(alt)), but the
    # lamp's default direction is -Z, so we rotate to align.
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = SUN_ENERGY
    sun_obj = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun_obj)

    alt_r = math.radians(SUN_ALTITUDE)
    az_r  = math.radians(SUN_AZIMUTH)
    # Lamp default emits along its local -Z.  After XYZ Euler rotation
    # (θx, 0, θz), the world-space light direction becomes:
    #   x = -sin(θz) · sin(θx)
    #   y =  cos(θz) · sin(θx)
    #   z = -cos(θx)
    # Matching this to a sun FROM (cos(A)·cos(Az), cos(A)·sin(Az), sin(A)):
    #   θx = π/2 - altitude,  θz = azimuth + π/2
    sun_obj.rotation_euler = (
        math.radians(90) - alt_r,   # tilt from vertical
        0,
        az_r + math.pi / 2          # +π/2 aligns azimuth correctly
    )

    # Point light at the East sighting hole — illuminates the box interior
    # when looking through the sighting tubes
    sh_data = bpy.data.lights.new("SightingHoleLight", 'POINT')
    sh_data.energy = 5
    sh_data.shadow_soft_size = 0.02
    sh_obj = bpy.data.objects.new("SightingHoleLight", sh_data)
    bpy.context.collection.objects.link(sh_obj)
    sh_hw = PILLAR_BTM_HW + (PILLAR_TOP_HW - PILLAR_BTM_HW) * (ST_Z / PILLAR_HEIGHT)
    sh_obj.location = (sh_hw + 0.05, 0, ST_Z)

    # Render engine
    try:
        bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        bpy.context.scene.render.engine = 'BLENDER_EEVEE'
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080

    # Switch viewport to Material Preview (only works in GUI mode)
    try:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        break
    except (AttributeError, RuntimeError):
        pass  # headless mode


def setup_camera_animation():
    """Flythrough camera: descend → orbit → sighting-hole pass → pull back.

    The camera uses a Track To constraint pointed at an animated empty
    ("CameraTarget"), so it always faces the action.  Both the camera
    and the target have keyframed locations defining the trajectory.

    Segment map (30 fps):
      1–120     Fly down from high above
      120–480   Full 360° orbit around the pillar
      480–600   Approach the east sighting hole
      600–690   Fly through the sighting tube
      690–810   Pull back to a 3/4 view
      810–900   Hold the final composition

    TUNEABLE PARAMETERS
    -------------------
    ORBIT_R / ORBIT_Z   — orbit radius and height
    LENS_MM             — camera focal length (lower = wider / more dramatic)
    FPS / TOTAL_FRAMES  — animation timing
    Individual keyframe positions can be adjusted in the code or
    interactively in Blender's Graph Editor after running.
    """
    print("  Camera animation ...")

    # ── TUNEABLE VALUES ──────────────────────────────────────────
    FPS          = 30
    TOTAL_FRAMES = 900
    ORBIT_R      = 2.5       # metres from pillar centre
    ORBIT_Z      = 1.5       # orbit altitude
    ORBIT_STEPS  = 72        # keyframes per full revolution (every 5°)
    LENS_MM      = 35        # focal length — 35 mm for dramatic perspective
    CLIP_START   = 0.001     # 1 mm — needed for sighting tube close-ups
    # ─────────────────────────────────────────────────────────────

    # ── Frame boundaries ─────────────────────────────────────────
    F_FLY_END   = 120        # end of fly-down
    F_ORB_END   = 480        # end of orbit
    F_APP_END   = 600        # end of approach
    F_THR_END   = 690        # end of flythrough
    F_PULL_END  = 810        # end of pull-back
    # 810–900 = hold

    # ── Derived positions ────────────────────────────────────────
    TARGET_MID = (0, 0, PILLAR_HEIGHT * 0.5)  # general look-at point
    SH_Z       = ST_Z                          # sighting hole height

    # ── Remove any existing camera ───────────────────────────────
    for name in ("Camera", "FlyCamera"):
        old = bpy.data.objects.get(name)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)

    # ── Create camera ────────────────────────────────────────────
    cam_data = bpy.data.cameras.new("FlyCamera")
    cam_data.lens = LENS_MM
    cam_data.clip_start = CLIP_START
    cam = bpy.data.objects.new("FlyCamera", cam_data)
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    # ── Create look-at target (animated empty) ───────────────────
    target = bpy.data.objects.new("CameraTarget", None)
    target.empty_display_type = 'PLAIN_AXES'
    target.empty_display_size = 0.1
    bpy.context.collection.objects.link(target)

    # Track To constraint — camera always faces the target
    track = cam.constraints.new('TRACK_TO')
    track.target = target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    # ── Timeline settings ────────────────────────────────────────
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES

    # ── Keyframe helper ──────────────────────────────────────────
    def kf(obj, frame, loc):
        """Insert a location keyframe."""
        obj.location = loc
        obj.keyframe_insert(data_path="location", frame=int(round(frame)))

    # =================================================================
    # SEGMENT 1 — Fly down from above  (frames 1 → 120)
    # =================================================================
    # Start high up to the south-east, descend to orbit entry (east).
    kf(cam, 1,                  (2.0, -3.0, 8.0))
    kf(cam, F_FLY_END * 0.5,   (2.5, -1.0, 4.0))
    kf(cam, F_FLY_END,         (ORBIT_R, 0, ORBIT_Z))

    # Target: look at mid-pillar throughout the descent
    kf(target, 1,          TARGET_MID)
    kf(target, F_FLY_END,  TARGET_MID)

    # =================================================================
    # SEGMENT 2 — 360° orbit  (frames 120 → 480)
    # =================================================================
    # Counter-clockwise from east (+X).  Keyframes every 15° for a
    # smooth Bézier-interpolated circle.
    orbit_dur = F_ORB_END - F_FLY_END          # 360 frames
    for i in range(ORBIT_STEPS + 1):
        angle = math.radians(i * 360.0 / ORBIT_STEPS)
        x = ORBIT_R * math.cos(angle)
        y = ORBIT_R * math.sin(angle)
        f = F_FLY_END + i * orbit_dur / ORBIT_STEPS
        kf(cam, f, (x, y, ORBIT_Z))

    kf(target, F_ORB_END, TARGET_MID)

    # =================================================================
    # SEGMENT 3 — Approach east sighting hole  (frames 480 → 600)
    # =================================================================
    # Camera descends from orbit altitude to sighting-hole height,
    # closing in on the east face.
    f_app_mid = (F_ORB_END + F_APP_END) // 2     # frame 540
    kf(cam, f_app_mid, (1.2, 0, 0.5))
    kf(cam, F_APP_END, (0.6, 0, SH_Z))

    # Target shifts to look straight through the sighting hole
    kf(target, f_app_mid, (0, 0, 0.3))
    kf(target, F_APP_END, (-3.0, 0, SH_Z))

    # =================================================================
    # SEGMENT 4 — Fly through the sighting tube  (frames 600 → 690)
    # =================================================================
    # Straight-line flight along the X axis at sighting-hole height.
    # The tube inner diameter is 44 mm — Blender's camera is a point
    # so it fits, and the 1 mm clip distance captures the tube walls.
    f_thr_mid = (F_APP_END + F_THR_END) // 2     # frame 645
    kf(cam, f_thr_mid, (0, 0, SH_Z))
    kf(cam, F_THR_END, (-0.6, 0, SH_Z))

    kf(target, F_THR_END, (-3.0, 0, SH_Z))

    # =================================================================
    # SEGMENT 5 — Pull back to 3/4 view  (frames 690 → 810)
    # =================================================================
    # Camera retreats south-west and rises, while the target
    # transitions back to mid-pillar for a classic 3/4 composition.
    f_pull_mid = (F_THR_END + F_PULL_END) // 2    # frame 750
    kf(cam, f_pull_mid, (-2.0, -1.5, 0.8))
    kf(cam, F_PULL_END, (-3.0, -2.5, 1.5))

    kf(target, f_pull_mid, (-0.5, 0, 0.4))
    kf(target, F_PULL_END, TARGET_MID)

    # =================================================================
    # SEGMENT 6 — Hold final view  (frames 810 → 900)
    # =================================================================
    kf(cam, TOTAL_FRAMES, (-3.0, -2.5, 1.5))
    kf(target, TOTAL_FRAMES, TARGET_MID)

    # ── Summary ──────────────────────────────────────────────────
    dur = TOTAL_FRAMES / FPS
    print(f"    {TOTAL_FRAMES} frames @ {FPS} fps = {dur:.0f} seconds")
    print(f"    Orbit: r={ORBIT_R} m, z={ORBIT_Z} m, {ORBIT_STEPS} steps")
    print(f"    Lens: {LENS_MM} mm, clip: {CLIP_START*1000:.0f} mm")
    print("    Segments:")
    print(f"      1–{F_FLY_END}:    Fly down")
    print(f"      {F_FLY_END}–{F_ORB_END}:  360° orbit")
    print(f"      {F_ORB_END}–{F_APP_END}:  Approach sighting hole")
    print(f"      {F_APP_END}–{F_THR_END}:  Fly through sighting tube")
    print(f"      {F_THR_END}–{F_PULL_END}:  Pull back to 3/4 view")
    print(f"      {F_PULL_END}–{TOTAL_FRAMES}:  Hold final composition")

    # ── Smooth keyframe handles ──────────────────────────────────
    # AUTO_CLAMPED prevents overshoot at segment boundaries while
    # still giving smooth curves.
    for obj in (cam, target):
        if obj.animation_data and obj.animation_data.action:
            for fc in obj.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.handle_left_type = 'AUTO_CLAMPED'
                    kp.handle_right_type = 'AUTO_CLAMPED'


def setup_final_render():
    """Configure Cycles GPU rendering for high-quality output.

    Renders to a PNG image sequence in a 'frames/' subdirectory next
    to this script.  Use the companion render.sh script to render
    headlessly and assemble the video with FFmpeg.

    TUNEABLE PARAMETERS
    -------------------
    SAMPLES       — Cycles samples per pixel (higher = cleaner, slower)
    RESOLUTION    — output resolution (width, height)
    USE_DENOISER  — enable AI denoising (highly recommended)
    """
    print("  Render settings ...")

    # ── TUNEABLE VALUES ──────────────────────────────────────────
    SAMPLES      = 256
    RESOLUTION   = (1920, 1080)
    USE_DENOISER = True
    # ─────────────────────────────────────────────────────────────

    scene  = bpy.context.scene
    render = scene.render

    # ── Cycles engine with GPU ───────────────────────────────────
    render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.cycles.samples = SAMPLES
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.01

    # Prefer OptiX (fastest on RTX), fall back to CUDA
    prefs = bpy.context.preferences.addons['cycles'].preferences
    gpu_type = 'CPU'
    for dt in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = dt
            prefs.get_devices()
            gpus = [d for d in prefs.devices if d.type != 'CPU']
            if gpus:
                gpu_type = dt
                break
        except Exception:
            continue

    # Enable all available devices (GPUs + CPU fallback)
    for device in prefs.devices:
        device.use = True

    # ── Denoiser ─────────────────────────────────────────────────
    denoiser_name = "none"
    if USE_DENOISER:
        scene.cycles.use_denoising = True
        # Try denoisers in preference order
        for dn in ('OPENIMAGEDENOISE', 'OPTIX'):
            try:
                scene.cycles.denoiser = dn
                denoiser_name = dn
                break
            except TypeError:
                continue
        else:
            # No denoiser available — compensate with more samples
            scene.cycles.use_denoising = False
            scene.cycles.samples = max(SAMPLES, 512)
            denoiser_name = "none (samples raised to 512)"

    # ── Light path optimisation ─────────────────────────────────
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 8
    scene.cycles.transparent_max_bounces = 8
    scene.cycles.sample_clamp_indirect = 10.0    # reduce fireflies

    # ── Resolution ───────────────────────────────────────────────
    render.resolution_x = RESOLUTION[0]
    render.resolution_y = RESOLUTION[1]
    render.resolution_percentage = 100

    # ── Output: PNG image sequence ───────────────────────────────
    # Determine output directory relative to this script
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()

    frames_dir = os.path.join(script_dir, "frames", "")
    os.makedirs(frames_dir, exist_ok=True)

    render.filepath = frames_dir
    render.image_settings.file_format = 'PNG'
    render.image_settings.color_mode = 'RGB'
    render.image_settings.color_depth = '8'
    render.use_overwrite = False          # skip already-rendered frames
    render.use_file_extension = True

    # ── Performance ──────────────────────────────────────────────
    render.use_persistent_data = True     # keep BVH between frames
    if gpu_type == 'OPTIX':
        scene.cycles.tile_size = 2048     # OptiX works best with large tiles
    else:
        scene.cycles.tile_size = 256      # good for CUDA

    print(f"    Engine:     Cycles ({gpu_type})")
    print(f"    Samples:    {scene.cycles.samples} (adaptive)")
    print(f"    Denoiser:   {denoiser_name}")
    print(f"    Resolution: {RESOLUTION[0]}×{RESOLUTION[1]}")
    print(f"    Output:     {frames_dir}")
    print(f"    Overwrite:  off (resume-safe)")


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("\n=== OS Trig Point (Hotine Pillar) Generator ===\n")
    clear_scene()

    # Materials — procedural PBR (see PROCEDURAL MATERIAL BUILDERS section)
    M = {
        'concrete':     make_concrete_material(),
        'brass':        make_brass_material(),
        'rusted_steel': make_rusted_steel_material(),
        'aged_steel':   make_aged_steel_material(),
        'wood':         make_wood_material(),
        'terrain':      make_terrain_material(),
        'landscape':    make_landscape_material(),
    }

    # Build all components
    build_pillar(M)
    build_centre_pipe(M)
    build_sighting_tubes(M)
    build_upper_box(M)
    build_concrete_fill(M)
    build_upper_centre_mark(M)
    build_spider(M)

    # Cut spider-footprint cavity from the pillar.  The spider is
    # embedded in the pillar top; concrete rises to PILLAR_HEIGHT
    # between the arms but is removed within the spider's outline
    # (arms, annulus, fillets) so grooves, bore, etc. are air.
    print("  Cutting spider cavity from pillar ...")
    outline = _spider_outline()
    spider_base_z = PILLAR_HEIGHT - SPIDER_THICK
    n = len(outline)

    bm = bmesh.new()
    bot = [bm.verts.new((x, y, spider_base_z - 0.001)) for x, y in outline]
    top = [bm.verts.new((x, y, PILLAR_HEIGHT + 0.001)) for x, y in outline]
    bm.faces.new(bot[::-1])
    bm.faces.new(top)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([bot[i], bot[j], top[j], top[i]])
    bmesh.ops.triangulate(bm, faces=bm.faces[:])

    mesh_cut = bpy.data.meshes.new("_spider_cavity")
    bm.to_mesh(mesh_cut)
    bm.free()

    cavity = bpy.data.objects.new("_spider_cavity", mesh_cut)
    bpy.context.collection.objects.link(cavity)
    boolean_cut(bpy.data.objects['Pillar'], cavity)

    build_plug(M)
    build_plug_text(M)
    build_fixings(M)
    build_brass_loops(M)
    build_flush_bracket(M)
    build_flush_bracket_logo(M)
    build_base_slab(M)
    build_angle_irons(M)
    build_lower_box(M)
    build_lower_block(M)
    build_lower_centre_mark(M)
    build_terrain(M)
    build_landscape_ring(M)
    build_grass()

    # Scene (lights, viewport settings)
    setup_scene()

    # Camera flythrough trajectory
    setup_camera_animation()

    # High-quality render settings (Cycles GPU, PNG sequence)
    setup_final_render()

    bpy.ops.object.select_all(action='DESELECT')
    n = len(bpy.data.objects)
    print(f"\nDone — {n} objects created.")
    print("Tip: Press Space in the Timeline to preview the camera flythrough.")
    print("     Press Numpad-0 to toggle the camera view.\n")



if __name__ == "__main__":
    main()

