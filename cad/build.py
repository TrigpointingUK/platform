"""Build, validate and export the plug and inner plug.

    python build.py                 # STEP masters + all STL variants
    python build.py --step-only     # just the nominal STEP masters
    python build.py --fast          # no threads (quick dimensional preview)

Outputs:
    step/plug_assembly.step     nominal master: both parts assembled, as two
                                separate named solids (Plug, InnerPlug)
    stl/<part>_<variant>.stl    per-process printable meshes (one file per part)

STL variants apply a radial thread clearance for a running fit. Values are
starting points for the first Bondar Labs test prints; refine once real prints
are trial-fitted. The STEP master is always nominal so the "true" geometry is
never contaminated by a print allowance.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import trimesh
from build123d import Compound, Pos, export_step, export_stl
from OCP.BRepCheck import BRepCheck_Analyzer

from inner_plug import build_inner_plug
from params import PLUG
from plug import build_plug
from top_surfaces import DEFAULT, PRESETS

HERE = Path(__file__).parent
STEP_DIR = HERE / "step"
STL_DIR = HERE / "stl"

# Radial thread clearance per process (mm). Tune after trial fits.
STL_VARIANTS = {
    "resin": 0.10,   # SLA resolves fine threads well -> tight
    "fdm": 0.25,     # FDM is coarser -> generous
}

# Mesh quality for STL (mm / degrees). Fine enough that helix flanks stay smooth
# and OCCT does not skip whole thread faces (which would leave real holes).
STL_LINEAR_TOL = 0.02
STL_ANGULAR_TOL = 0.3

# Inner-plug top-surface presets to render (see top_surfaces.PRESETS). The
# assembly STEP always uses the flat top; the others are produced as extra STLs
# named inner_plug_<label>_<variant>.stl. Trim this list to speed up a build.
INNER_TOPS = ["flat", "tuk-logo", "tuk-logo-emboss", "trig-5169-qr"]


def _validate(part, label: str) -> None:
    if not BRepCheck_Analyzer(part.wrapped).IsValid():
        raise RuntimeError(f"{label}: BRepCheck reports invalid geometry")
    n = len(part.solids())
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 solid, got {n}")


def _export_watertight_stl(part, path: Path, label: str) -> str:
    """Export a gap-free STL and return a short quality note.

    On the fine, rotated locking-screw thread OCCT's mesher emits a few zero-area
    triangles and a handful of non-manifold "pinch" edges (surfaces meeting
    along an edge). Neither is a leak. We strip the slivers, fill any face OCCT
    skipped, then *assert the mesh is gap-free* (no open/boundary edges) -- the
    real requirement for printing; a genuine hole fails the build. A few pinch
    edges are tolerated (slicers handle them) and reported. The STEP master is
    the exact B-rep; only the mesh is repaired here."""
    export_stl(part, str(path), tolerance=STL_LINEAR_TOL,
               angular_tolerance=STL_ANGULAR_TOL)
    mesh = trimesh.load(str(path), process=True)
    mesh.update_faces(mesh.nondegenerate_faces(height=1e-8))  # drop zero-area slivers
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    trimesh.repair.fill_holes(mesh)  # close any single faces OCCT skipped
    trimesh.repair.fix_normals(mesh)
    open_edges = trimesh.grouping.group_rows(mesh.edges_sorted, require_count=1)
    if len(open_edges) > 0:
        raise RuntimeError(f"{label}: STL has {len(open_edges)} open edges (a leak)")
    mesh.export(str(path))
    pinch = 0 if mesh.is_watertight else "some"
    return "gap-free" if mesh.is_watertight else f"gap-free ({pinch} pinch edges)"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--step-only", action="store_true", help="skip STL export")
    ap.add_argument(
        "--fast",
        action="store_true",
        help="build without threads (fast dimensional preview)",
    )
    args = ap.parse_args()

    STEP_DIR.mkdir(exist_ok=True)
    STL_DIR.mkdir(exist_ok=True)
    threads = not args.fast

    skip_stl = args.step_only or args.fast

    # ---- Outer plug -------------------------------------------------------
    t0 = time.time()
    plug_master = build_plug(PLUG, threads=threads, clearance=0.0)
    _validate(plug_master, "plug (master)")
    print(f"plug: master volume={plug_master.volume:.0f} mm^3 valid "
          f"({time.time()-t0:.1f}s)")
    if not skip_stl:
        for variant, clr in STL_VARIANTS.items():
            tv = time.time()
            part = build_plug(PLUG, threads=True, clearance=clr)
            _validate(part, f"plug ({variant})")
            stl_path = STL_DIR / f"plug_{variant}.stl"
            note = _export_watertight_stl(part, stl_path, f"plug ({variant})")
            print(f"    {variant}: clearance={clr} mm radial [{note}] "
                  f"-> {stl_path.relative_to(HERE)}  ({time.time()-tv:.1f}s)")

    # ---- Inner plug, once per top-surface preset --------------------------
    # The flat master feeds the assembly; every preset gets its own STLs.
    inner_flat_master = None
    for top in INNER_TOPS:
        suffix = "" if top == DEFAULT else f"_{PRESETS[top].label}"
        tv = time.time()
        if top == DEFAULT:
            inner_flat_master = build_inner_plug(PLUG, threads=threads, clearance=0.0)
            _validate(inner_flat_master, "inner_plug (master)")
            print(f"inner_plug: master volume={inner_flat_master.volume:.0f} "
                  f"mm^3 valid ({time.time()-tv:.1f}s)")
        else:
            print(f"inner_plug[{top}]:")
        if skip_stl:
            continue
        for variant, clr in STL_VARIANTS.items():
            tv = time.time()
            # Printed STLs get a plain tap-drill locking-screw hole (hand-tapped
            # later); the fine thread lives only in the STEP master.
            part = build_inner_plug(PLUG, threads=True, clearance=clr, top=top,
                                    locking_screw_thread=False)
            _validate(part, f"inner_plug[{top}] ({variant})")
            stl_path = STL_DIR / f"inner_plug{suffix}_{variant}.stl"
            note = _export_watertight_stl(part, stl_path, f"inner_plug[{top}] ({variant})")
            print(f"    {variant}: clearance={clr} mm radial [{note}] "
                  f"-> {stl_path.relative_to(HERE)}  ({time.time()-tv:.1f}s)")

    # ---- Combined STEP: both parts, assembled, as separate named objects ---
    plug_master.label = "Plug"
    # Seat the inner plug in the bore with its top flush with the plug top.
    seat = (PLUG.lower_h + PLUG.middle_h + PLUG.upper_h) - PLUG.ip_h
    inner = Pos(0, 0, seat) * inner_flat_master
    inner.label = "InnerPlug"
    assembly = Compound(children=[plug_master, inner])
    assembly.label = "PlugAssembly"
    step_path = STEP_DIR / "plug_assembly.step"
    export_step(assembly, str(step_path))
    print(f"assembly: Plug + InnerPlug (seated {seat:.0f} mm) "
          f"-> {step_path.relative_to(HERE)}")


if __name__ == "__main__":
    main()
