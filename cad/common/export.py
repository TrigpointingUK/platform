"""Validation and watertight-STL export helpers shared by every model.

The STEP master is always the exact B-rep; only meshes are repaired here. These
were lifted verbatim from the original single-component ``build.py`` so their
behaviour (and output) is unchanged.
"""

from __future__ import annotations

from pathlib import Path

import trimesh
from build123d import export_stl
from OCP.BRepCheck import BRepCheck_Analyzer

# Mesh quality for STL (mm / degrees). Fine enough that helix flanks stay smooth
# and OCCT does not skip whole thread faces (which would leave real holes).
STL_LINEAR_TOL = 0.02
STL_ANGULAR_TOL = 0.3


def validate(part, label: str) -> None:
    """Assert ``part`` is a valid single solid, else raise."""
    if not BRepCheck_Analyzer(part.wrapped).IsValid():
        raise RuntimeError(f"{label}: BRepCheck reports invalid geometry")
    n = len(part.solids())
    if n != 1:
        raise RuntimeError(f"{label}: expected 1 solid, got {n}")


def export_watertight_stl(part, path: Path, label: str) -> str:
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
