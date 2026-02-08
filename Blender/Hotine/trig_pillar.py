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
from mathutils import Vector


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
UCM_R               = 0.016     # [E] ~1.25" dia / 2
UCM_H               = 0.012     # [E] dome height

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
LOOP_RECESS_L       = 0.040     # [D] 40 mm recess length (radial)
LOOP_RECESS_W       = 0.015     # [D] 15 mm recess width (tangential)
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
SCREW_SOCKET_R      = 0.0015    # [D] 3 mm allen socket dia / 2
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

# --- Lower Wooden Box ---
LB_HW               = 0.127     # [E] ~10" / 2
LB_HEIGHT           = 0.102     # [E] ~4"
LB_WALL             = 0.025     # [E] 1"

# --- Lower Block ---
LBLOCK_HW           = 0.152     # [D] 1'0" / 2
LBLOCK_H            = 0.305     # [E] ~12"

# --- Lower Centre Mark ---
LCM_R               = 0.016     # [E] same as upper
LCM_H               = 0.012     # [E] dome height


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

    Use solver='FAST' for cuts where EXACT fails silently (e.g. cylindrical
    holes through complex geometry).

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
    STAIN_STRENGTH     = 0.35
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
    GRASS_BUMP     = 0.08
    GRASS_DRY_AMT  = 0.20                  # proportion of dry patches
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

    grass_mix = N('ShaderNodeMixRGB', (-300, -200), "Grass + Dry")
    grass_mix.blend_type = 'MIX'
    grass_mix.inputs[0].default_value = 1.0   # use dry mask as factor
    L.new(dry_cr.outputs['Color'], grass_mix.inputs['Fac'])
    L.new(grass_cr.outputs['Color'], grass_mix.inputs['Color1'])
    grass_mix.inputs['Color2'].default_value = (*GRASS_COL_DRY, 1)

    # ── Combine layers: bedrock → soil → grass ───────────────────
    mix_bs = N('ShaderNodeMixRGB', (-100, 300), "Bedrock→Soil Mix")
    mix_bs.blend_type = 'MIX'
    L.new(map_bs.outputs['Result'], mix_bs.inputs['Fac'])
    L.new(rock_cr.outputs['Color'], mix_bs.inputs['Color1'])
    L.new(soil_cr.outputs['Color'], mix_bs.inputs['Color2'])

    mix_sg = N('ShaderNodeMixRGB', (100, 100), "→Grass Mix")
    mix_sg.blend_type = 'MIX'
    L.new(map_sg.outputs['Result'], mix_sg.inputs['Fac'])
    L.new(mix_bs.outputs['Color'], mix_sg.inputs['Color1'])
    L.new(grass_mix.outputs['Color'], mix_sg.inputs['Color2'])

    # ── Roughness: blend per layer (bedrock → soil → grass) ─────
    rough_bs = N('ShaderNodeMixRGB', (-100, -200), "Rough B→S")
    rough_bs.blend_type = 'MIX'
    L.new(map_bs.outputs['Result'], rough_bs.inputs['Fac'])
    rough_bs.inputs['Color1'].default_value = (BEDROCK_ROUGH, BEDROCK_ROUGH, BEDROCK_ROUGH, 1)
    rough_bs.inputs['Color2'].default_value = (SOIL_ROUGH, SOIL_ROUGH, SOIL_ROUGH, 1)

    rough_final = N('ShaderNodeMixRGB', (100, -200), "Rough →G")
    rough_final.blend_type = 'MIX'
    L.new(map_sg.outputs['Result'], rough_final.inputs['Fac'])
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
    L.new(map_sg.outputs['Result'], bump_mul.inputs[1])

    bump = N('ShaderNodeBump', (100, -500), "Bump")
    bump.inputs['Strength'].default_value = GRASS_BUMP
    L.new(bump_mul.outputs['Value'], bump.inputs['Height'])

    # ── BSDF ─────────────────────────────────────────────────────
    bsdf = N('ShaderNodeBsdfPrincipled', (400, 100), "Terrain BSDF")
    L.new(mix_sg.outputs['Color'], bsdf.inputs['Base Color'])
    # Feed the R channel of the blended roughness colour into Roughness
    sep_rough = N('ShaderNodeSeparateColor', (250, -200), "Sep Rough")
    L.new(rough_final.outputs['Color'], sep_rough.inputs['Color'])
    L.new(sep_rough.outputs['Red'], bsdf.inputs['Roughness'])
    L.new(bump.outputs['Normal'], bsdf.inputs['Normal'])

    output = N('ShaderNodeOutputMaterial', (700, 100))
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
    boolean_cut(pillar, v, solver='FAST')

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
    boolean_cut(pillar, bpy.context.active_object, solver='FAST')

    # --- Four sighting-tube channels (pillar face → box outer face) ---
    # Each is a separate cylinder that stops at the box wall — concrete
    # does NOT extend into the box interior.
    chan_r = ST_OUTER_R + 0.001         # 1 mm clearance — tight fit
    hw = pillar_hw_at(ST_Z)
    box_face = UB_HW                    # box outer face distance from centre

    # Channel spans from 2 mm inside the box wall to 5 mm past the pillar face
    chan_inner = box_face - 0.002
    chan_outer = hw + 0.005
    chan_len = chan_outer - chan_inner
    chan_mid = (chan_outer + chan_inner) / 2

    for dx, dy, ry, rx in (
        (0, -1, 0, -math.pi / 2),      # South
        (0, +1, 0, +math.pi / 2),      # North
        (+1, 0, -math.pi / 2, 0),      # East
        (-1, 0, +math.pi / 2, 0),      # West
    ):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=chan_r, depth=chan_len, vertices=32,
            location=(dx * chan_mid, dy * chan_mid, ST_Z))
        c = bpy.context.active_object
        c.rotation_euler = (rx, ry, 0)
        activate(c)
        bpy.ops.object.transform_apply(rotation=True)
        boolean_cut(pillar, c, solver='FAST')

    # Bevelled entrance at each sighting hole — conical chamfer, 8 mm deep
    bevel_face_r = ST_OUTER_R + 0.012   # wider at the pillar surface
    bevel_inner_r = chan_r               # matches channel
    bevel_depth = 0.008

    for face_x, face_y, ry, rx in (
        (0, -hw, 0, -math.pi / 2),      # South
        (0, +hw, 0, +math.pi / 2),      # North
        (+hw, 0, -math.pi / 2, 0),      # East
        (-hw, 0, +math.pi / 2, 0),      # West
    ):
        bpy.ops.mesh.primitive_cone_add(
            radius1=bevel_face_r, radius2=bevel_inner_r,
            depth=bevel_depth, vertices=32,
            location=(face_x, face_y, ST_Z))
        c = bpy.context.active_object
        c.rotation_euler = (rx, ry, 0)
        activate(c)
        bpy.ops.object.transform_apply(rotation=True)
        shift_x = -face_x / hw * bevel_depth / 2 if face_x != 0 else 0
        shift_y = -face_y / hw * bevel_depth / 2 if face_y != 0 else 0
        c.location = (face_x + shift_x, face_y + shift_y, ST_Z)
        boolean_cut(pillar, c, solver='FAST')

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
    boolean_cut(box, bpy.context.active_object, solver='FAST')

    # Sighting-tube holes through four side walls
    for dx, dy, rot in (
        ( 0, -1, ( math.pi / 2, 0, 0)),
        ( 0,  1, (-math.pi / 2, 0, 0)),
        ( 1,  0, (0,  math.pi / 2, 0)),
        (-1,  0, (0, -math.pi / 2, 0)),
    ):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ST_OUTER_R + 0.001, depth=UB_WALL * 3,
            vertices=32, location=(dx * ow, dy * ow, ST_Z))
        c = bpy.context.active_object
        c.rotation_euler = rot
        activate(c)
        bpy.ops.object.transform_apply(rotation=True)
        boolean_cut(box, c, solver='FAST')

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


def build_upper_centre_mark(M):
    """Upper centre mark — two stepped disks with sloping edges, a low dome,
    a pencil-point, and a brass pillar + base cylinder embedded below.

    All proportions are relative to the overall dome diameter (UCM_R * 2).
    """
    print("  Upper centre mark ...")
    z0 = UB_BASE_Z + FILL_HEIGHT           # top of concrete fill
    dome_d = UCM_R * 2                      # overall diameter (32 mm)

    # ── Above the concrete surface ──────────────────────────────

    # Lower step — truncated cone (sloping edge, wider at bottom)
    ls_btm_r = dome_d / 2                   # full diameter
    ls_top_r = dome_d / 2 * 0.88            # slight inward slope
    ls_h = 0.0025                            # 2.5 mm
    bpy.ops.mesh.primitive_cone_add(
        radius1=ls_btm_r, radius2=ls_top_r,
        depth=ls_h, vertices=32,
        location=(0, 0, z0 + ls_h / 2))
    mark = bpy.context.active_object
    mark.name = "UpperCentreMark"

    # Upper step — smaller truncated cone
    us_btm_r = dome_d / 2 * 0.70
    us_top_r = dome_d / 2 * 0.60
    us_h = 0.002                             # 2 mm
    z_us = z0 + ls_h + us_h / 2
    bpy.ops.mesh.primitive_cone_add(
        radius1=us_btm_r, radius2=us_top_r,
        depth=us_h, vertices=32,
        location=(0, 0, z_us))
    _union_into(mark, bpy.context.active_object)

    # Flat rounded dome — 80% of upper step diameter, ~2.7 mm tall (⅓ of 8 mm)
    fd_r = us_top_r * 0.80
    fd_h = 0.0027
    z_fd = z0 + ls_h + us_h
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=fd_r, segments=32, ring_count=16,
        location=(0, 0, z_fd))
    dome_obj = bpy.context.active_object
    dome_obj.scale.z = fd_h / fd_r
    activate(dome_obj)
    bpy.ops.object.transform_apply(scale=True)
    # Cut the bottom half
    bpy.ops.mesh.primitive_cube_add(
        size=fd_r * 4, location=(0, 0, z_fd - fd_r * 2))
    boolean_cut(dome_obj, bpy.context.active_object)
    _union_into(mark, dome_obj)

    # Point — 5 mm diameter rod with 45° cone tip
    # (kept as a separate object to avoid boolean-union artefacts at this scale)
    pt_r = 0.005 / 2                        # 2.5 mm radius
    rod_h = 0.005                            # 5 mm cylinder
    cone_h = pt_r                            # 2.5 mm (45° → height = radius)
    z_rod = z_fd + fd_h + rod_h / 2
    z_cone = z_fd + fd_h + rod_h + cone_h / 2

    # Cylinder (rod portion)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=pt_r, depth=rod_h, vertices=16,
        location=(0, 0, z_rod))
    spike = bpy.context.active_object
    spike.name = "UpperCentreMark_Spike"

    # Cone tip
    bpy.ops.mesh.primitive_cone_add(
        radius1=pt_r, radius2=0,
        depth=cone_h, vertices=16,
        location=(0, 0, z_cone))
    _union_into(spike, bpy.context.active_object)

    assign(spike, M['brass'])
    smooth(spike)

    # ── Below the concrete surface (embedded) ───────────────────

    # Brass pillar — 40% of dome diameter, height 150% of dome diameter
    pil_r = dome_d * 0.40 / 2
    pil_h = dome_d * 1.50
    z_pil = z0 - pil_h / 2
    bpy.ops.mesh.primitive_cylinder_add(
        radius=pil_r, depth=pil_h, vertices=32,
        location=(0, 0, z_pil))
    _union_into(mark, bpy.context.active_object)

    # Base cylinder — 130% of pillar diameter, 15% of pillar height
    base_r = pil_r * 1.30
    base_h = pil_h * 0.15
    z_base = z0 - pil_h - base_h / 2
    bpy.ops.mesh.primitive_cylinder_add(
        radius=base_r, depth=base_h, vertices=32,
        location=(0, 0, z_base))
    _union_into(mark, bpy.context.active_object)

    assign(mark, M['brass'])
    smooth(mark)
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
    cham_r      = 0.010                           # 10 mm nominal rounded chamfer
    half_str    = (rl - rw) / 2                   # 12.5 mm half straight
    CHAM_N      = 6                               # quarter-circle chamfer segments
    SEMI_N      = 8                               # semicircle depth segments
    CAP_N       = 6                               # end-cap taper slices
    EPS         = 0.001                           # overshoot above surface

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

        # ── Recess cutter (stadium plan, rounded profile) ────────
        # Cross-section: quarter-circle chamfer at top flowing into
        # semicircular trough at bottom, with straight walls between
        # (when depth allows).  Chamfer radius is capped at hw_loc so
        # at full width (7.5 mm) the chamfer and semicircle merge
        # seamlessly — one continuous smooth curve, no flat walls.
        bm_r = bmesh.new()
        rings = []

        def _add_ring(x, hw_loc):
            """Append a rounded-profile ring at position x."""
            cr = min(cham_r, hw_loc)              # cap chamfer at ring width
            wh = rd - hw_loc - cr                 # wall height (may be 0)
            pts = []
            # — Above surface, right
            pts.append((hw_loc + cr, EPS))
            # — Right chamfer arc (quarter circle, surface → wall)
            #   Centre at (hw_loc + cr, -cr)
            for j in range(1, CHAM_N + 1):
                theta = math.pi / 2 + j * (math.pi / 2) / CHAM_N
                pts.append(((hw_loc + cr) + cr * math.cos(theta),
                            -cr + cr * math.sin(theta)))
            # — Wall bottom right
            pts.append((hw_loc, -(cr + wh)))
            # — Semicircle bottom (right → left)
            for j in range(1, SEMI_N):
                a = j * (-math.pi / SEMI_N)
                pts.append((hw_loc * math.cos(a),
                            -(cr + wh) + hw_loc * math.sin(a)))
            # — Wall bottom left
            pts.append((-hw_loc, -(cr + wh)))
            # — Left chamfer arc (quarter circle, wall → surface)
            #   Centre at (-(hw_loc + cr), -cr)
            for j in range(1, CHAM_N + 1):
                theta = j * (math.pi / 2) / CHAM_N
                pts.append((-(hw_loc + cr) + cr * math.cos(theta),
                            -cr + cr * math.sin(theta)))
            # — Above surface, left
            pts.append((-(hw_loc + cr), EPS))
            ring = [bm_r.verts.new((x, y, z)) for y, z in pts]
            rings.append(ring)

        # Left end cap (far end first → centre)
        for k in range(CAP_N, 0, -1):
            dx = hw * k / CAP_N
            hw_loc = math.sqrt(max(0, hw**2 - dx**2))
            if hw_loc < 0.0005:
                continue
            _add_ring(-(half_str + dx), hw_loc)

        # Straight section ends
        _add_ring(-half_str, hw)
        _add_ring( half_str, hw)

        # Right end cap (centre → far end)
        for k in range(1, CAP_N + 1):
            dx = hw * k / CAP_N
            hw_loc = math.sqrt(max(0, hw**2 - dx**2))
            if hw_loc < 0.0005:
                continue
            _add_ring(half_str + dx, hw_loc)

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

        # Top face (stadium outline at z = EPS)
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

    TEXT_R       = 0.032     # midpoint of the upper ring annulus
    EMBOSS       = 0.0020    # 2.0 mm engraving depth below surface
    OVERSHOOT    = 0.002     # cutter extends this far above surface
    FONT_SIZE    = 0.0045    # character height
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
        ("TRIANGULATION STATION", 90,  TOP_SPAN_DEG),
        ("ORDNANCE SURVEY",       270, BTM_SPAN_DEG),
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
            vertices=12,
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
    """Flush bracket with beading, recessed into one pillar face (+Y).

    The bracket is a vertical brass plate (180 × 100 mm) with 5 mm
    semicircular beading running around all four edges of the front
    face, including rounded corners.  It is set back 8 mm from the
    pillar face at the top edge; because the pillar tapers, the
    setback is greater at the bottom.

    A recess is carved from the pillar with 45° chamfers sloping from
    the pillar face to the beading on all four sides.
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

    # ── Beading (D-shaped tube around front face perimeter) ───
    # A semicircular cross-section (flat against plate, dome forward)
    # swept around the rectangular perimeter with rounded corners.
    BEAD_N   = 6                                  # semicircle segments
    CORNER_N = 4                                  # samples per corner arc

    bm = bmesh.new()

    # Build the perimeter path on the plate's front face.
    # Each entry: (x, z, tangent_x, tangent_z).
    # Corners follow quarter-circle arcs of radius br.
    path = []

    # Bottom edge (+X)
    path.append((-hw + br, z_bot, 1, 0))
    path.append(( hw - br, z_bot, 1, 0))

    # BR corner — centre (hw - br, z_bot + br), arc -π/2 → 0
    cx, cz = hw - br, z_bot + br
    for k in range(1, CORNER_N + 1):
        th = -math.pi / 2 + k * (math.pi / 2) / CORNER_N
        path.append((cx + br * math.cos(th), cz + br * math.sin(th),
                      -math.sin(th), math.cos(th)))

    # Right edge (+Z)
    path.append((hw, z_top - br, 0, 1))

    # TR corner — centre (hw - br, z_top - br), arc 0 → π/2
    cx, cz = hw - br, z_top - br
    for k in range(1, CORNER_N + 1):
        th = k * (math.pi / 2) / CORNER_N
        path.append((cx + br * math.cos(th), cz + br * math.sin(th),
                      -math.sin(th), math.cos(th)))

    # Top edge (-X)
    path.append((-hw + br, z_top, -1, 0))

    # TL corner — centre (-hw + br, z_top - br), arc π/2 → π
    cx, cz = -hw + br, z_top - br
    for k in range(1, CORNER_N + 1):
        th = math.pi / 2 + k * (math.pi / 2) / CORNER_N
        path.append((cx + br * math.cos(th), cz + br * math.sin(th),
                      -math.sin(th), math.cos(th)))

    # Left edge (-Z)
    path.append((-hw, z_bot + br, 0, -1))

    # BL corner — centre (-hw + br, z_bot + br), arc π → 3π/2
    # Omit final point (coincides with path[0] to close the loop).
    cx, cz = -hw + br, z_bot + br
    for k in range(1, CORNER_N):
        th = math.pi + k * (math.pi / 2) / CORNER_N
        path.append((cx + br * math.cos(th), cz + br * math.sin(th),
                      -math.sin(th), math.cos(th)))

    # Create a D-shaped cross-section ring at each path point.
    # The semicircle's flat side sits on the plate front face.
    # Bi-normal B = tangent × Y gives the "sideways" direction.
    rings = []
    n_bead = BEAD_N + 1
    for px, pz, tx, tz in path:
        bx, bz = -tz, tx                         # bi-normal
        ring = []
        for j in range(n_bead):
            a = -math.pi / 2 + j * math.pi / BEAD_N
            fwd = br * math.cos(a)
            bi  = br * math.sin(a)
            ring.append(bm.verts.new((
                px + bi * bx,
                front_y + fwd,
                pz + bi * bz)))
        rings.append(ring)

    # Connect adjacent rings with quads (closed loop)
    n_path = len(rings)
    for s in range(n_path):
        sn = (s + 1) % n_path
        for v in range(n_bead - 1):
            bm.faces.new([rings[s][v], rings[s][v + 1],
                          rings[sn][v + 1], rings[sn][v]])
        # Close the D — flat back face (last vert → first vert)
        bm.faces.new([rings[s][n_bead - 1], rings[s][0],
                      rings[sn][0], rings[sn][n_bead - 1]])

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
    # The recess is a pocket + 45° chamfer on all four sides.
    # Built as a 12-vertex solid:
    #   4 back verts   (pocket back, inner outline)
    #   4 inner verts  (bracket level, inner outline)
    #   4 outer verts  (pillar face, expanded by 45° chamfer)
    pillar = bpy.data.objects['Pillar']

    bead_ext = br + 0.001                         # beading outline + clearance
    inner_y  = front_y + br + 0.001               # just past beading peak

    # Inner outline (matches bracket beading)
    ixl = -(hw + bead_ext)
    ixr =  (hw + bead_ext)
    izb =  z_bot - bead_ext
    izt =  z_top + bead_ext

    # Gap from beading to pillar face (depth of chamfer)
    gap_top = max(0.001, pillar_hw_at(z_top) - inner_y)
    gap_bot = max(0.001, pillar_hw_at(z_bot) - inner_y)

    # Outer outline (at pillar face, expanded by gap = 45° chamfer)
    ozt = izt + gap_top
    ozb = izb - gap_bot
    oxl_t = ixl - gap_top                         # sides narrower at top
    oxr_t = ixr + gap_top
    oxl_b = ixl - gap_bot                         # sides wider at bottom
    oxr_b = ixr + gap_bot

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

    # Outer front vertices (at pillar face, expanded outline)
    o_tl = bm_c.verts.new((oxl_t, oy_top, ozt))
    o_tr = bm_c.verts.new((oxr_t, oy_top, ozt))
    o_br = bm_c.verts.new((oxr_b, oy_bot, ozb))
    o_bl = bm_c.verts.new((oxl_b, oy_bot, ozb))

    # 10 faces forming the closed solid
    bm_c.faces.new([b_tl, b_tr, b_br, b_bl])     # back
    bm_c.faces.new([b_tl, b_tr, i_tr, i_tl])     # pocket top
    bm_c.faces.new([b_bl, b_br, i_br, i_bl])     # pocket bottom
    bm_c.faces.new([b_tl, i_tl, i_bl, b_bl])     # pocket left
    bm_c.faces.new([b_tr, b_br, i_br, i_tr])     # pocket right
    bm_c.faces.new([i_tl, i_tr, o_tr, o_tl])     # chamfer top (45°)
    bm_c.faces.new([i_bl, i_br, o_br, o_bl])     # chamfer bottom (45°)
    bm_c.faces.new([i_tl, o_tl, o_bl, i_bl])     # chamfer left (45°)
    bm_c.faces.new([i_tr, i_br, o_br, o_tr])     # chamfer right (45°)
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

    L-profile built directly with bmesh (no boolean union) for completely
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

    # Standard L cross-section centred on bounding-box centre.
    # Inner corner faces (+X, +Y).
    profile = [
        (-half,     -half),
        ( half,     -half),
        ( half,     -half + t),
        (-half + t, -half + t),
        (-half + t,  half),
        (-half,      half),
    ]

    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
        z_jitter = rng.uniform(-0.005, 0.005)     # ±5 mm → ~10 mm spread
        tilt_x = sy * base_tilt * (1.0 + rng.uniform(-0.01, 0.01))
        tilt_y = -sx * base_tilt * (1.0 + rng.uniform(-0.01, 0.01))

        # Build L-shape with bmesh — flip profile to orient inner corner
        # toward (sx, sy) so it grips the pillar edge.
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
    """Brass centre mark: dome + tapered stalk + base disk.

    Proportions are relative to dome diameter (dome_dia):
      - Stalk height:      1.0  × dome_dia
      - Stalk top width:   0.25 × dome_dia
      - Stalk bottom width: 0.35 × dome_dia
      - Disk diameter:     0.5  × dome_dia
      - Disk height:       0.2  × dome_dia
    """
    print("  Lower centre mark ...")
    z_top = -BASE_HEIGHT - LB_HEIGHT       # top of lower block
    dome_dia = LCM_R * 2                   # full dome diameter

    # --- Dome (top) ---
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=LCM_R, segments=32, ring_count=16, location=(0, 0, z_top))
    mark = bpy.context.active_object
    mark.name = "LowerCentreMark"
    mark.scale.z = LCM_H / LCM_R
    activate(mark)
    bpy.ops.object.transform_apply(scale=True)

    # Cut bottom half to make a dome
    bpy.ops.mesh.primitive_cube_add(
        size=LCM_R * 4, location=(0, 0, z_top - LCM_R * 2))
    boolean_cut(mark, bpy.context.active_object)

    # --- Stalk (tapered cylinder below dome) ---
    stalk_h = dome_dia                             # height = dome diameter
    stalk_top_r = 0.25 * dome_dia / 2             # 0.25× dome dia as radius
    stalk_btm_r = 0.35 * dome_dia / 2             # 0.35× dome dia as radius
    stalk_z = z_top - stalk_h / 2                  # centre of stalk

    bpy.ops.mesh.primitive_cone_add(
        radius1=stalk_btm_r, radius2=stalk_top_r,
        depth=stalk_h, vertices=32,
        location=(0, 0, stalk_z))
    stalk = bpy.context.active_object
    stalk.name = "_lcm_stalk"

    # Union stalk to dome
    activate(mark)
    mod = mark.modifiers.new("_bool", 'BOOLEAN')
    mod.operation = 'UNION'
    mod.object = stalk
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier="_bool")
    bpy.data.objects.remove(stalk, do_unlink=True)

    # --- Base disk ---
    disk_r = 0.5 * dome_dia / 2                   # 0.5× dome dia as radius
    disk_h = 0.2 * dome_dia                        # 0.2× dome dia
    disk_z = z_top - stalk_h - disk_h / 2          # sits below stalk

    bpy.ops.mesh.primitive_cylinder_add(
        radius=disk_r, depth=disk_h, vertices=32,
        location=(0, 0, disk_z))
    disk = bpy.context.active_object
    disk.name = "_lcm_disk"

    # Union disk to dome+stalk
    activate(mark)
    mod = mark.modifiers.new("_bool", 'BOOLEAN')
    mod.operation = 'UNION'
    mod.object = disk
    mod.solver = 'EXACT'
    bpy.ops.object.modifier_apply(modifier="_bool")
    bpy.data.objects.remove(disk, do_unlink=True)

    assign(mark, M['brass'])
    smooth(mark)
    return mark


def build_terrain(M):
    """Layered terrain: dome-shaped hilltop with bedrock, soil, and grass.

    The terrain is a solid volume extending from the grass surface down
    past the lower block.  During the X-ray phase, making it transparent
    reveals the underground structure (base slab, lower box, lower block)
    embedded in the soil and bedrock.

    TUNEABLE PARAMETERS
    -------------------
    TERRAIN_RADIUS   — radius of the terrain disc (metres)
    TERRAIN_DEPTH    — how far below z=0 the terrain extends
    GRID_SUBDIVS     — mesh resolution (higher = smoother undulation)
    DOME_HEIGHT      — height drop from centre to edge
    NOISE_STRENGTH   — amplitude of surface undulation
    NOISE_SCALE      — spatial frequency of undulation
    NOISE_OCTAVES    — fractal detail layers
    """
    print("  Terrain ...")

    # ── TUNEABLE VALUES ──────────────────────────────────────────
    TERRAIN_RADIUS = 5.0          # 10 m across — fills the frame
    GRID_SUBDIVS   = 80           # vertex spacing ~12.5 cm
    DOME_HEIGHT    = 0.25         # gentle 25 cm dome
    NOISE_STRENGTH = 0.04         # ±4 cm undulation
    NOISE_SCALE    = 1.5          # spatial frequency
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

    assign(terrain, M['terrain'])
    smooth(terrain)
    return terrain


# =====================================================================
# SCENE SETUP
# =====================================================================

def setup_scene():
    """Add camera, lights, and configure render settings."""
    # Camera — positioned to see the full pillar
    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = 50
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    cam_obj.location = (2.0, -2.0, 1.0)
    cam_obj.rotation_euler = (math.radians(72), 0, math.radians(45))
    bpy.context.scene.camera = cam_obj

    # Sun light
    sun_data = bpy.data.lights.new("Sun", 'SUN')
    sun_data.energy = 3
    sun_obj = bpy.data.objects.new("Sun", sun_data)
    bpy.context.collection.objects.link(sun_obj)
    sun_obj.rotation_euler = (
        math.radians(40), math.radians(15), math.radians(30))

    # Fill light
    fill_data = bpy.data.lights.new("Fill", 'AREA')
    fill_data.energy = 50
    fill_data.size = 2.0
    fill_obj = bpy.data.objects.new("Fill", fill_data)
    bpy.context.collection.objects.link(fill_obj)
    fill_obj.location = (-2, 3, 2)
    fill_obj.rotation_euler = (
        math.radians(55), 0, math.radians(-130))

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

    # Enable CUDA device(s)
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'CUDA'
    prefs.get_devices()
    for device in prefs.devices:
        device.use = True    # enable all available GPUs + CPU

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
    scene.cycles.tile_size = 256          # good for GPU

    print(f"    Engine:     Cycles (GPU/CUDA)")
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
    build_base_slab(M)
    build_angle_irons(M)
    build_lower_box(M)
    build_lower_block(M)
    build_lower_centre_mark(M)
    build_terrain(M)

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

