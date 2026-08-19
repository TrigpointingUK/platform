"""Build recipe for the plug + inner-plug component.

Exposes ``run(*, threads, skip_stl)`` for the top-level orchestrator. Outputs
land in the shared ``step/``/``stl/`` dirs with component-prefixed filenames:

    step/plug_assembly.step         both parts assembled, as named solids
    stl/plug_<variant>.stl          per-process printable plug meshes
    stl/inner_plug[_<top>]_<variant>.stl

STL variants apply a radial thread clearance for a running fit; the STEP master
is always nominal (zero clearance) so the "true" geometry is never contaminated.
"""

from __future__ import annotations

import time

from build123d import Compound, Pos, export_step

from common.export import export_watertight_stl, validate
from common.paths import CAD_DIR, STEP_DIR, STL_DIR
from models.plug.inner_plug import build_inner_plug
from models.plug.params import PLUG
from models.plug.plug import build_plug
from models.plug.top_surfaces import DEFAULT, PRESETS

# Radial thread clearance per process (mm). Tune after trial fits.
#
# First trial fit (FDM, printed 2026-08): the spider thread's crest measured
# 63.0 mm against a 63.30 mm STL -- but the mesh of the day had only 42 facets
# per revolution, so a caliper across two opposite flats would read 63.12 mm.
# That leaves ~0.12 mm of genuine process loss on diameter, i.e. the printed
# thread lands close to the modelled crest and this 0.25 mm allowance is doing
# roughly what it says. Left alone until a fit against a real spider says
# otherwise; both the mesh and the nominal diameter have since been corrected,
# so the next print is the first clean measurement of this number.
STL_VARIANTS = {
    "resin": 0.10,   # SLA resolves fine threads well -> tight
    "fdm": 0.25,     # FDM is coarser -> generous
}

# Locking-screw head recess for PRINTED parts only (mm). The brass original
# takes a cap head that the modelled Ø6.3 mm counterbore fits exactly, and the
# STEP master keeps that. But that exact screw could not be sourced as a BOM
# part, so printed assemblies use a cheese head instead -- Ø7 mm across the head
# at worst -- which needs the recess opened up to clear it. The threaded portion
# is untouched: an FDM part, once tapped, still takes the original brass screw.
PRINTED_LOCK_COUNTERBORE_D = 7.5

# Inner-plug top-surface presets to render (see top_surfaces.PRESETS). The
# assembly STEP always uses the flat top; the others are produced as extra STLs
# named inner_plug_<label>_<variant>.stl. Trim this list to speed up a build.
INNER_TOPS = ["flat", "tuk-logo", "tuk-logo-emboss", "trig-5169-qr"]


def run(*, threads: bool = True, skip_stl: bool = False) -> None:
    """Build, validate and export the plug + inner plug."""
    # ---- Outer plug -------------------------------------------------------
    t0 = time.time()
    plug_master = build_plug(PLUG, threads=threads, clearance=0.0)
    validate(plug_master, "plug (master)")
    print(f"plug: master volume={plug_master.volume:.0f} mm^3 valid "
          f"({time.time()-t0:.1f}s)")
    if not skip_stl:
        for variant, clr in STL_VARIANTS.items():
            tv = time.time()
            part = build_plug(PLUG, threads=True, clearance=clr)
            validate(part, f"plug ({variant})")
            stl_path = STL_DIR / f"plug_{variant}.stl"
            note = export_watertight_stl(part, stl_path, f"plug ({variant})")
            print(f"    {variant}: clearance={clr} mm radial [{note}] "
                  f"-> {stl_path.relative_to(CAD_DIR)}  ({time.time()-tv:.1f}s)")

    # ---- Inner plug, once per top-surface preset --------------------------
    # The flat master feeds the assembly; every preset gets its own STLs.
    inner_flat_master = None
    for top in INNER_TOPS:
        suffix = "" if top == DEFAULT else f"_{PRESETS[top].label}"
        tv = time.time()
        if top == DEFAULT:
            inner_flat_master = build_inner_plug(PLUG, threads=threads, clearance=0.0)
            validate(inner_flat_master, "inner_plug (master)")
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
                                    locking_screw_thread=False,
                                    lock_counterbore_d=PRINTED_LOCK_COUNTERBORE_D)
            validate(part, f"inner_plug[{top}] ({variant})")
            stl_path = STL_DIR / f"inner_plug{suffix}_{variant}.stl"
            note = export_watertight_stl(part, stl_path, f"inner_plug[{top}] ({variant})")
            print(f"    {variant}: clearance={clr} mm radial [{note}] "
                  f"-> {stl_path.relative_to(CAD_DIR)}  ({time.time()-tv:.1f}s)")

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
          f"-> {step_path.relative_to(CAD_DIR)}")


if __name__ == "__main__":
    from common.paths import ensure_dirs

    ensure_dirs()
    run()
