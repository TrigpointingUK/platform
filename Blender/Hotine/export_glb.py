"""
export_glb.py — Export a web-friendly GLB of the trig pillar.

Usage:
    blender --background --python trig_pillar.py --python export_glb.py

Or interactively: build the scene first (run trig_pillar.py), then run
this script from Blender's text editor.

Outputs:  ../../web/public/models/trig.glb
Also:     ../../res/models/trig.glb  (source copy)
"""

import bpy
import os
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Objects to KEEP — everything else gets deleted before export
KEEP_NAMES = {
    "Pillar", "CentrePipe",
    "ST_East", "ST_West", "ST_North", "ST_South",
    "UpperBox", "LowerBox",
    "ConcreteFill",
    "UpperCentreMark", "UpperCentreMark_Spike",
    "Spider",
    "Plug", "InnerPlug",
    "BrassLoop_0", "BrassLoop_1", "BrassLoop_2", "BrassLoop_3",
    "FlushBracket", "FlushBracket_Bead",
    "BaseSlab",
    "AngleIron_0", "AngleIron_1", "AngleIron_2", "AngleIron_3",
    "LowerBlock", "LowerBox",
    "LowerCentreMark",
    "Screw_0", "Screw_180",
    "AntiRotationPeg",
}

# Max faces per object before decimation kicks in
DECIMATE_THRESHOLD = 8000
DECIMATE_TARGET    = 4000


def run():
    print("\n=== GLB Export for Web Viewer ===\n")

    # ── 1. Delete unwanted objects ─────────────────────────────────
    to_delete = []
    for obj in list(bpy.data.objects):
        if obj.name not in KEEP_NAMES:
            to_delete.append(obj)

    for obj in to_delete:
        bpy.data.objects.remove(obj, do_unlink=True)
    print(f"  Removed {len(to_delete)} non-structural objects")

    # ── 2. Clear all animation data ────────────────────────────────
    for obj in bpy.data.objects:
        obj.animation_data_clear()
        # Reset transforms that may have been keyframed
        obj.hide_render = False
        obj.hide_viewport = False
    print("  Cleared animation data")

    # ── 3. Unparent all objects (flatten hierarchy) ────────────────
    for obj in bpy.data.objects:
        if obj.parent:
            # Apply the parent transform so geometry stays in place
            mat = obj.matrix_world.copy()
            obj.parent = None
            obj.matrix_world = mat
    print("  Flattened object hierarchy")

    # ── 4. Decimate high-poly meshes ───────────────────────────────
    decimated = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        face_count = len(obj.data.polygons)
        if face_count > DECIMATE_THRESHOLD:
            ratio = DECIMATE_TARGET / face_count
            mod = obj.modifiers.new("_decimate", 'DECIMATE')
            mod.ratio = ratio
            mod.use_collapse_triangulate = True
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier="_decimate")
            new_count = len(obj.data.polygons)
            print(f"    Decimated {obj.name}: {face_count} → {new_count} faces")
            decimated += 1

    if decimated == 0:
        print("  No objects needed decimation")

    # ── 5. Strip all materials (applied client-side in three.js) ───
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.data.materials.clear()
    print("  Stripped materials")

    # ── 6. Report totals ───────────────────────────────────────────
    total_verts = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == 'MESH')
    total_faces = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == 'MESH')
    n_objects = len([o for o in bpy.data.objects if o.type == 'MESH'])
    print(f"\n  {n_objects} mesh objects, {total_verts:,} vertices, {total_faces:,} faces")

    # ── 7. Export GLB ──────────────────────────────────────────────
    out_web = os.path.normpath(os.path.join(SCRIPT_DIR, "../../web/public/models/trig.glb"))
    out_res = os.path.normpath(os.path.join(SCRIPT_DIR, "../../res/models/trig.glb"))

    # Select all mesh objects for export
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            obj.select_set(True)

    bpy.ops.export_scene.gltf(
        filepath=out_web,
        export_format='GLB',
        use_selection=True,
        export_apply=True,           # apply modifiers
        export_animations=False,
        export_materials='NONE',     # no materials in GLB
        export_colors=False,
        export_normals=True,
        export_yup=True,             # three.js convention: Y-up
    )

    size_kb = os.path.getsize(out_web) / 1024
    print(f"\n  Exported: {out_web}  ({size_kb:.0f} KB)")

    # Copy to res/ as well
    os.makedirs(os.path.dirname(out_res), exist_ok=True)
    shutil.copy2(out_web, out_res)
    print(f"  Copied:   {out_res}")

    print("\n=== Export complete ===\n")


if __name__ == "__main__":
    run()