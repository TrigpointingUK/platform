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
CP_PROTRUDE_TOP     = 0.050     # [E] protrusion above pillar top

# --- Sighting Tubes ---
ST_OUTER_R          = 0.025     # [E] 2" OD / 2
ST_INNER_R          = 0.022     # [E] ~1.75" ID / 2
ST_TILT             = math.radians(2)   # [E] 2° drainage tilt
ST_Z                = 0.107     # [E] aimed at top of dome / base of spike

# --- Upper Wooden Box (internal) ---
UB_HW               = 0.127     # [E] ~10" outer / 2
UB_HEIGHT           = 0.203     # [E] ~8"
UB_WALL             = 0.015     # 15 mm timber
UB_BASE_Z           = 0.000     # box base sits on top of the base slab

# --- Concrete Fill in Upper Box ---
FILL_HEIGHT         = 0.076     # [E] top 5 mm below bottom of sighting-tube holes

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
LOOP_WIRE_R         = 0.003     # [E] ¼" wire / 2
LOOP_H              = 0.020     # [E] ~¾" standing height
LOOP_W              = 0.016     # [E] ~⅝" width
LOOP_RECESS         = 0.006     # [D] ¼" sunk below spider

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
FB_W                = 0.102     # [E] ~4" wide
FB_H                = 0.127     # [E] ~5" tall
FB_D                = 0.010     # [E] ~3/8" deep
FB_Z                = 0.813     # [E] centre height ~2'8" above base

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

    # --- Centre-pipe channel (pillar top → box top face) ---
    cp_void_len = PILLAR_HEIGHT - box_top_z + 0.002
    cp_void_z = (box_top_z - 0.001 + PILLAR_HEIGHT + 0.001) / 2
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
    """Vertical steel tube — from above the pillar top down to just inside the box lid."""
    print("  Centre pipe ...")
    # Top of pipe: protrudes above pillar
    z_top = PILLAR_HEIGHT + CP_PROTRUDE_TOP
    # Bottom of pipe: protrudes a small, slightly random amount below the box lid
    lid_inner_z = UB_BASE_Z + UB_HEIGHT - UB_WALL
    protrude = 0.020 + random.Random(70).uniform(-0.008, 0.008)
    z_btm = lid_inner_z - protrude

    total_h = z_top - z_btm
    z_centre = (z_top + z_btm) / 2
    pipe = make_tube("CentrePipe", CP_OUTER_R, CP_INNER_R,
                     total_h, loc=(0, 0, z_centre))
    assign(pipe, M['steel'])
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
        assign(t, M['steel'])
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

    # ── Fillet geometry (local frame: arm along +Y) ───────────────
    fc_x    = arm_hw + fr                           # fillet centre X (right side)
    fc_dist = outer_r + fr                          # distance from origin to fillet centre
    fc_y    = math.sqrt(fc_dist**2 - fc_x**2)      # fillet centre Y

    # Right-side tangent on annulus outer circle
    t_ann_x = outer_r * fc_x / fc_dist
    t_ann_y = outer_r * fc_y / fc_dist

    # Right fillet arc angles (measured from right fillet centre)
    fa_ann = math.atan2(t_ann_y - fc_y, t_ann_x - fc_x)
    fa_arm = math.pi                                # toward arm tangent
    if fa_ann < fa_arm:                             # ensure short (clockwise) arc
        fa_ann += 2 * math.pi

    # Left fillet arc angles (from left fillet centre at (-fc_x, fc_y))
    fl_arm = 0.0                                    # toward arm tangent
    fl_ann = math.atan2(t_ann_y - fc_y, fc_x - t_ann_x)

    FILLET_N = 8       # segments per fillet arc
    ARC_N    = 12      # segments per annulus arc between arms

    # ── Build outer boundary (counter-clockwise) ─────────────────
    outline = []

    for ai in range(3):
        theta = arm_angles[ai]
        rot   = theta - math.pi / 2
        cr, sr = math.cos(rot), math.sin(rot)

        def xf(lx, ly, _c=cr, _s=sr):
            """Transform from local arm frame to global XY."""
            return (lx * _c - ly * _s, lx * _s + ly * _c)

        # Right fillet: annulus tangent → arm tangent
        for j in range(FILLET_N + 1):
            t = j / FILLET_N
            a = fa_ann + t * (fa_arm - fa_ann)
            outline.append(xf(fc_x + fr * math.cos(a),
                              fc_y + fr * math.sin(a)))

        # Right arm side → tip
        outline.append(xf(arm_hw, tip_r))

        # Arm tip (right → left)
        outline.append(xf(-arm_hw, tip_r))

        # Left fillet: arm tangent → annulus tangent
        for j in range(FILLET_N + 1):
            t = j / FILLET_N
            a = fl_arm + t * (fl_ann - fl_arm)
            outline.append(xf(-fc_x + fr * math.cos(a),
                              fc_y + fr * math.sin(a)))

        # Annulus arc to next arm's right fillet
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
    outline = cleaned

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
    """Three brass loops set into the pillar top between spider arms."""
    print("  Brass loops ...")
    zt = PILLAR_HEIGHT - LOOP_RECESS
    loops = []
    for i in range(3):
        # Between spider arms (offset 60° from arm positions)
        angle = math.radians(90 + 60 + i * 120)
        r = SPIDER_ANNULUS_OUTER_R + 0.012
        cx = r * math.cos(angle)
        cy = r * math.sin(angle)

        bpy.ops.mesh.primitive_torus_add(
            major_radius=LOOP_W / 2, minor_radius=LOOP_WIRE_R,
            major_segments=24, minor_segments=8,
            location=(cx, cy, zt))
        lp = bpy.context.active_object
        lp.name = f"BrassLoop_{i}"
        lp.scale.z = LOOP_H / LOOP_W
        lp.rotation_euler.z = angle
        activate(lp)
        bpy.ops.object.transform_apply(scale=True, rotation=True)

        # Remove bottom half (below surface)
        bpy.ops.mesh.primitive_cube_add(
            size=LOOP_W * 4, location=(cx, cy, zt - LOOP_W * 2))
        boolean_cut(lp, bpy.context.active_object)

        assign(lp, M['brass'])
        smooth(lp)
        loops.append(lp)
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

        assign(screw, M['steel'])
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

    assign(peg, M['steel'])
    smooth(peg)


def build_flush_bracket(M):
    """Simplified flush bracket on one pillar face (+Y / North)."""
    print("  Flush bracket ...")
    hw = pillar_hw_at(FB_Z)
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(0, hw + FB_D / 2 - 0.001, FB_Z))
    fb = bpy.context.active_object
    fb.name = "FlushBracket"
    fb.scale = (FB_W, FB_D, FB_H)
    activate(fb)
    bpy.ops.object.transform_apply(scale=True)
    assign(fb, M['brass'])
    return fb


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
        assign(iron, M['steel'])
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


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("\n=== OS Trig Point (Hotine Pillar) Generator ===\n")
    clear_scene()

    # Materials
    M = {
        'concrete': make_material("Concrete", (0.65, 0.63, 0.60), 0.0, 0.85),
        'steel':    make_material("Steel",    (0.40, 0.42, 0.44), 0.9, 0.30),
        'brass':    make_material("Brass",    (0.78, 0.62, 0.20), 0.9, 0.25),
        'wood':     make_material("Wood",     (0.45, 0.30, 0.15), 0.0, 0.80),
    }

    # Build all components
    build_pillar(M)
    build_centre_pipe(M)
    build_sighting_tubes(M)
    build_upper_box(M)
    build_concrete_fill(M)
    build_upper_centre_mark(M)
    build_spider(M)
    build_plug(M)
    build_fixings(M)
    build_brass_loops(M)
    build_flush_bracket(M)
    build_base_slab(M)
    build_angle_irons(M)
    build_lower_box(M)
    build_lower_block(M)
    build_lower_centre_mark(M)

    # Scene
    setup_scene()

    bpy.ops.object.select_all(action='DESELECT')
    n = len(bpy.data.objects)
    print(f"\nDone — {n} objects created.")
    print("Tip: hide the Pillar object in the Outliner to see internal components.\n")


if __name__ == "__main__":
    main()

