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
UB_WALL             = 0.025     # [E] ~1" timber
UB_BASE_Z           = 0.000     # box base sits on top of the base slab

# --- Concrete Fill in Upper Box ---
FILL_HEIGHT         = 0.100     # [E] fills to near sighting tube level

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
SPIDER_OUTER_R      = 0.076     # [E] ~6" dia / 2
SPIDER_ANNULUS_R    = 0.044     # [E] ~3.5" dia / 2
SPIDER_HOLE_R       = 0.022     # [E] threaded hole ~1.75" dia / 2
SPIDER_THICK        = 0.010     # [E] ~3/8"
SPIDER_ARM_W        = 0.025     # [E] arm width ~1"

# --- Brass Loops ---
LOOP_WIRE_R         = 0.003     # [E] ¼" wire / 2
LOOP_H              = 0.020     # [E] ~¾" standing height
LOOP_W              = 0.016     # [E] ~⅝" width
LOOP_RECESS         = 0.006     # [D] ¼" sunk below spider

# --- Plug ---
PLUG_OUTER_R        = 0.022     # [E] matches spider hole
PLUG_INNER_R        = 0.016     # [E] inner thread
PLUG_H              = 0.016     # [E] ~⅝"

# --- Inner Plug ---
IPLUG_R             = 0.016     # [E] matches plug inner
IPLUG_H             = 0.022     # [E] ~⅞"

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
    """
    activate(target)
    mod = target.modifiers.new("_bool", 'BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    mod.solver = solver
    bpy.ops.object.modifier_apply(modifier="_bool")
    bpy.data.objects.remove(cutter, do_unlink=True)


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
    """Main concrete pillar body with holes for centre pipe and sighting tubes.

    Boolean voids are sized to cut only through the concrete portions of the
    pillar — they stop at the upper wooden box boundary so that no stray
    cylindrical geometry extends into the box interior.
    """
    print("  Pillar body ...")
    pillar = make_frustum(
        "Pillar", PILLAR_BTM_HW, PILLAR_TOP_HW, PILLAR_HEIGHT,
        base_z=0, bevel_r=BEVEL_RADIUS, bevel_n=BEVEL_SEGMENTS)

    # --- Cut centre-pipe channel (only through concrete above the box lid) ---
    lid_z = UB_BASE_Z + UB_HEIGHT
    cp_void_len = PILLAR_HEIGHT - lid_z + 0.02
    cp_void_z = (lid_z - 0.01 + PILLAR_HEIGHT + 0.01) / 2
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CP_OUTER_R + 0.005,
        depth=cp_void_len,
        vertices=32,
        location=(0, 0, cp_void_z))
    boolean_cut(pillar, bpy.context.active_object, solver='FAST')

    # --- Cut sighting-tube channels through concrete ---
    # Use generous radius (3× clearance) and FAST solver for reliability.
    # The channel runs from well inside the box interior to past the pillar face.
    cut_r = ST_OUTER_R + 0.005          # 5 mm clearance around the tube
    hw = pillar_hw_at(ST_Z)
    max_protrude = 0.025
    void_inner = (UB_HW - UB_WALL) - max_protrude - 0.015
    void_outer = hw + 0.015             # extend well past pillar face
    void_len = void_outer - void_inner
    void_mid = (void_inner + void_outer) / 2

    for dx, dy, rot in (
        ( 1,  0, (0,  math.pi / 2, 0)),   # +X face (East)
        (-1,  0, (0, -math.pi / 2, 0)),   # -X face (West)
        ( 0,  1, (-math.pi / 2, 0, 0)),   # +Y face (North)
        ( 0, -1, ( math.pi / 2, 0, 0)),   # -Y face (South)
    ):
        bpy.ops.mesh.primitive_cylinder_add(
            radius=cut_r, depth=void_len, vertices=32,
            location=(dx * void_mid, dy * void_mid, ST_Z))
        c = bpy.context.active_object
        c.rotation_euler = rot
        activate(c)
        bpy.ops.object.transform_apply(rotation=True)
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
    """Four slightly-angled sighting tubes — each protrudes a slightly different
    amount into the box interior, suggesting rough hand-assembly."""
    print("  Sighting tubes ...")
    rng = random.Random(55)
    hw = pillar_hw_at(ST_Z)
    box_inner = UB_HW - UB_WALL           # inner box wall distance from centre
    outer_end = hw + 0.005                 # just past pillar face
    a = ST_TILT

    directions = [
        ("ST_East",  ( 1, 0), (0,  math.pi / 2 + a, 0)),
        ("ST_West",  (-1, 0), (0, -(math.pi / 2 + a), 0)),
        ("ST_North", (0,  1), (-(math.pi / 2 + a), 0, 0)),
        ("ST_South", (0, -1), ( (math.pi / 2 + a), 0, 0)),
    ]
    tubes = []
    for name, (dx, dy), rot in directions:
        # Each tube protrudes a slightly different amount past the inner box wall
        protrude = 0.015 + rng.uniform(-0.008, 0.010)
        inner_end = box_inner - protrude
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
    """Upper wooden box (bottomless, with lid) that holds the tube assembly.

    Boolean operations are ordered so that all holes are cut while the box
    is still a solid block — this gives the EXACT boolean solver clean,
    thick geometry to work with and avoids silent failures when cutting
    through thin walls.
    """
    print("  Upper wooden box ...")
    outer = UB_HW
    h = UB_HEIGHT
    bz = UB_BASE_Z

    # Start with a solid block
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, bz + h / 2))
    box = bpy.context.active_object
    box.name = "UpperBox"
    box.scale = (outer * 2, outer * 2, h)
    activate(box)
    bpy.ops.object.transform_apply(scale=True)

    # 1) Cut holes FIRST — while the box is still solid

    # Centre-pipe hole through top — FAST solver for reliability
    bpy.ops.mesh.primitive_cylinder_add(
        radius=CP_OUTER_R + 0.005, depth=UB_WALL * 3,
        vertices=32, location=(0, 0, bz + h))
    boolean_cut(box, bpy.context.active_object, solver='FAST')

    # Sighting-tube holes through four walls — FAST solver for reliability
    for dx, dy, rot in (
        ( 1, 0, (0,  math.pi / 2, 0)),
        (-1, 0, (0, -math.pi / 2, 0)),
        ( 0, 1, (-math.pi / 2, 0, 0)),
        ( 0,-1, ( math.pi / 2, 0, 0)),
    ):
        # Very generous cutter: 5 mm clearance, spans full box width
        bpy.ops.mesh.primitive_cylinder_add(
            radius=ST_OUTER_R + 0.005, depth=outer * 3,
            vertices=32, location=(dx * outer, dy * outer, ST_Z))
        c = bpy.context.active_object
        c.rotation_euler = rot
        activate(c)
        bpy.ops.object.transform_apply(rotation=True)
        boolean_cut(box, c, solver='FAST')

    # 2) Hollow out the interior LAST — FAST solver for reliability
    inner = outer - UB_WALL
    void_h = h  # tall enough to extend below box bottom
    void_z = bz + h / 2 - UB_WALL  # top of void = bz + h - UB_WALL
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, void_z))
    v = bpy.context.active_object
    v.scale = (inner * 2, inner * 2, void_h)
    activate(v)
    bpy.ops.object.transform_apply(scale=True)
    boolean_cut(box, v, solver='FAST')

    assign(box, M['wood'])
    return box


def build_concrete_fill(M):
    """Concrete fill at the bottom of the upper wooden box, with a recess
    cut out for the upper centre mark so it isn't hidden in solid view."""
    print("  Concrete fill ...")
    s = (UB_HW - UB_WALL) * 2 - 0.004  # slightly smaller than box interior
    bpy.ops.mesh.primitive_cube_add(
        size=1, location=(0, 0, UB_BASE_Z + FILL_HEIGHT / 2))
    f = bpy.context.active_object
    f.name = "ConcreteFill"
    f.scale = (s, s, FILL_HEIGHT)
    activate(f)
    bpy.ops.object.transform_apply(scale=True)

    # Cut a cylindrical recess for the upper centre mark (embedded pillar + base)
    dome_d = UCM_R * 2
    recess_r = dome_d / 2 + 0.002           # slightly wider than the mark
    recess_h = FILL_HEIGHT + 0.002           # full depth of fill
    bpy.ops.mesh.primitive_cylinder_add(
        radius=recess_r, depth=recess_h, vertices=32,
        location=(0, 0, UB_BASE_Z + FILL_HEIGHT / 2))
    boolean_cut(f, bpy.context.active_object)

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
    """Brass spider fitting at the top of the pillar."""
    print("  Spider ...")
    zt = PILLAR_HEIGHT
    zmid = zt - SPIDER_THICK / 2

    # Central annulus disc
    bpy.ops.mesh.primitive_cylinder_add(
        radius=SPIDER_ANNULUS_R, depth=SPIDER_THICK,
        vertices=64, location=(0, 0, zmid))
    spider = bpy.context.active_object
    spider.name = "Spider"

    # Cut centre hole
    bpy.ops.mesh.primitive_cylinder_add(
        radius=SPIDER_HOLE_R, depth=SPIDER_THICK + 0.004,
        vertices=32, location=(0, 0, zmid))
    boolean_cut(spider, bpy.context.active_object)

    # Three arms at 120° intervals (first arm points toward +Y / North)
    for i in range(3):
        angle = math.radians(90 + i * 120)
        arm_len = SPIDER_OUTER_R - SPIDER_ANNULUS_R + 0.005
        dist = SPIDER_ANNULUS_R + arm_len / 2 - 0.003
        cx = dist * math.cos(angle)
        cy = dist * math.sin(angle)

        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(cx, cy, zmid))
        arm = bpy.context.active_object
        arm.scale = (arm_len, SPIDER_ARM_W, SPIDER_THICK)
        arm.rotation_euler.z = angle
        activate(arm)
        bpy.ops.object.transform_apply(scale=True, rotation=True)

        # Union arm to spider body
        activate(spider)
        mod = spider.modifiers.new("_bool", 'BOOLEAN')
        mod.operation = 'UNION'
        mod.object = arm
        mod.solver = 'EXACT'
        bpy.ops.object.modifier_apply(modifier="_bool")
        bpy.data.objects.remove(arm, do_unlink=True)

    assign(spider, M['brass'])
    return spider


def build_brass_loops(M):
    """Three brass loops set into the pillar top between spider arms."""
    print("  Brass loops ...")
    zt = PILLAR_HEIGHT - LOOP_RECESS
    loops = []
    for i in range(3):
        # Between spider arms (offset 60° from arm positions)
        angle = math.radians(90 + 60 + i * 120)
        r = SPIDER_ANNULUS_R + 0.012
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
    """Brass plug and inner plug in the spider's central hole."""
    print("  Plug & inner plug ...")
    zt = PILLAR_HEIGHT

    # Outer plug (annulus)
    plug = make_tube("Plug", PLUG_OUTER_R, PLUG_INNER_R, PLUG_H,
                     loc=(0, 0, zt - PLUG_H / 2))
    assign(plug, M['brass'])
    smooth(plug)

    # Inner plug (solid cylinder)
    bpy.ops.mesh.primitive_cylinder_add(
        radius=IPLUG_R, depth=IPLUG_H, vertices=32,
        location=(0, 0, zt - IPLUG_H / 2))
    ip = bpy.context.active_object
    ip.name = "InnerPlug"
    assign(ip, M['brass'])
    smooth(ip)

    return plug, ip


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
    """Four angle irons — roughly parallel to pillar taper, placed halfway
    between pillar edges and box edges, with ~10% random variation in
    length and angle to suggest hand-placement."""
    print("  Angle irons ...")
    rng = random.Random(99)
    irons = []

    # Halfway between pillar corners and box corners
    hw_mid = (PILLAR_BTM_HW + UB_HW) / 2

    # Base tilt angle to follow the pillar's tapered sides
    base_tilt = math.atan2(PILLAR_BTM_HW - PILLAR_TOP_HW, PILLAR_HEIGHT)

    # Vertical span: from inside the base up into the pillar
    bz = -BASE_HEIGHT + 0.05
    base_h = AI_TOTAL_H

    # L-profile offset: distance from L's centre to each leg's centreline
    l_offset = (AI_LEG - AI_THICK) / 2

    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (1, 1), (-1, 1)]):
        # All irons are exactly the same length
        h = base_h

        # Tilt to follow pillar slope, with tiny random wobble (±1%)
        tilt_x = sy * base_tilt * (1.0 + rng.uniform(-0.01, 0.01))
        tilt_y = -sx * base_tilt * (1.0 + rng.uniform(-0.01, 0.01))

        # Leg 1: extends in X, offset toward the corner in Y
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(0, sy * l_offset, 0))
        leg1 = bpy.context.active_object
        leg1.scale = (AI_LEG, AI_THICK, h)
        activate(leg1)
        bpy.ops.object.transform_apply(scale=True)

        # Leg 2: extends in Y, offset toward the corner in X
        bpy.ops.mesh.primitive_cube_add(
            size=1, location=(sx * l_offset, 0, 0))
        leg2 = bpy.context.active_object
        leg2.scale = (AI_THICK, AI_LEG, h)
        activate(leg2)
        bpy.ops.object.transform_apply(scale=True)

        # Union the two legs
        activate(leg1)
        mod = leg1.modifiers.new("_bool", 'BOOLEAN')
        mod.operation = 'UNION'
        mod.object = leg2
        mod.solver = 'EXACT'
        bpy.ops.object.modifier_apply(modifier="_bool")
        bpy.data.objects.remove(leg2, do_unlink=True)

        # Re-centre origin on the L-shape geometry
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')

        # Final position (with tiny random offset) and rotation
        cx = sx * (hw_mid - AI_LEG / 2) + rng.uniform(-0.001, 0.001)
        cy = sy * (hw_mid - AI_LEG / 2) + rng.uniform(-0.001, 0.001)
        cz = bz + h / 2

        leg1.location = (cx, cy, cz)
        leg1.rotation_euler = (tilt_x, tilt_y, 0)

        leg1.name = f"AngleIron_{i}"
        assign(leg1, M['steel'])
        irons.append(leg1)
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

