"""Validation and watertight-STL export helpers shared by every model.

The STEP master is always the exact B-rep; only meshes are repaired here.
"""

from __future__ import annotations

from pathlib import Path

import trimesh
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer

# Mesh quality for STL. ``STL_LINEAR_TOL`` is an **absolute** chord deflection in
# mm: the furthest the flat mesh is allowed to stray from the true surface. It is
# the knob that matters, and it is radius-adaptive -- a big cylinder gets many
# facets, a small hole few -- so quality is bought only where it is needed.
#
# NB we mesh via OCCT directly rather than build123d's ``export_stl``, which
# hardcodes ``isRelative=True``: that scales the deflection by each edge's own
# size, making the facet count *independent of radius*. The first printed
# prototype was exported that way (0.02 relative / 0.3 rad) and every circle,
# large or small, came out with just 42 facets. On the Ø92 mm upper ring that is
# a 6.9 mm chord deviating 129 um from true, and the n-gon was obvious across
# the room.
#
# At 0.005 mm absolute that ring gets ~300 facets deviating 2.5 um -- an order of
# magnitude below a resin printer's XY pixel, and far below what FDM can place --
# while a Ø6 mm hole needs only ~77, so the meshes stay a sane size.
#
# ``STL_ANGULAR_TOL`` (radians) is left as a backstop for curves too small for
# the chord criterion to divide sensibly, chiefly the lettering and logo
# outlines. Held at the prototype's value so nothing is *coarser* than before;
# tightening it inflates those tops enormously for no visible gain.
#
# Both values are also fine enough that helix flanks stay smooth and OCCT does
# not skip whole thread faces (which would leave real holes).
STL_LINEAR_TOL = 0.005  # mm, absolute chord deflection
STL_ANGULAR_TOL = 0.3  # radians


def _write_stl(part, path: Path) -> None:
    """Mesh ``part`` at the module's tolerances and write a binary STL.

    Equivalent to ``build123d.export_stl`` except the linear tolerance is an
    absolute distance rather than a fraction of each edge's size.
    """
    mesher = BRepMesh_IncrementalMesh(
        part.wrapped, STL_LINEAR_TOL, False, STL_ANGULAR_TOL, True
    )
    mesher.Perform()
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    if not writer.Write(part.wrapped, str(path)):
        raise RuntimeError(f"STL write failed: {path}")


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
    _write_stl(part, path)
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
