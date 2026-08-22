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

from dataclasses import dataclass

from build123d import Compound, Pos, Rot, export_step

from common.export import export_watertight_stl, validate
from common.specs import ThreadSpec
from common.paths import CAD_DIR, STEP_DIR, STL_DIR
from models.plug.inner_plug import build_inner_plug
from models.plug.params import PLUG
from models.plug.plug import build_plug
from models.plug.top_surfaces import DEFAULT, PRESETS

@dataclass(frozen=True)
class PrintVariant:
    """How one print process deviates from the brass original.

    ``clearance`` is the radial allowance on the spider thread (and the
    locking-screw hole). ``bore_joint`` optionally swaps the inner-plug/bore
    joint for one suited to the process.

    The bore joint's allowance is given **per member**, because both members of
    that joint are printed: putting the full allowance on each doubles the slop
    actually seen by the assembled pair. ``None`` means "same as ``clearance``",
    which reproduces the original behaviour of allowing on both.
    """

    clearance: float
    bore_joint: object = None                      # None = brass thread
    bore_clearance_external: float | None = None   # on the inner plug
    bore_clearance_internal: float | None = None   # on the plug's bore


# The inner-plug/bore joint, redrawn for FDM. Both members of this joint are
# printed and it never has to mate with brass, so it is free to be whatever
# prints best -- unlike the spider joint, which must fit a real pillar spider
# and therefore keeps the original 8 TPI Whitworth whatever the cost.
#
# The brass joint is 14 TPI Whitworth: a 0.30 mm crest flat (narrower than one
# 0.42 mm extrusion, so the crest simply never forms) and flanks overhanging at
# 62.5 deg. Coarsening it would not help -- a V-form thread overhangs 62.5 deg
# at every pitch. Assuming a 0.4 mm nozzle and 0.2 mm layers, this replaces it
# with a 45 deg trapezoid at 4 mm pitch: 1.2 mm deep, 0.8 mm (two beads) at both
# crest and root gap, 20 layers per turn, and a radial step of one layer height
# per layer so nothing is unsupported. Major diameter stays Ø39.3 so the part
# still looks right and no wall thickness changes.
FDM_BORE_JOINT = ThreadSpec(
    name="innerplug-to-bore (FDM)",
    major_diameter=39.3,
    pitch=4.0,
    form="trapezoid",
    crest_flat=0.8,
    provenance="[S]",
    note="Printability-driven, not a measurement. FDM parts mate only with "
         "each other, never with brass.",
)

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
#
# NB resin keeps the brass thread and its existing allowance untouched: it was
# measured on the first print at 0.18 mm clearance with 0.97 mm engagement,
# close to the brass pair itself, so resin parts stay interchangeable with brass
# originals. Only FDM gets the redrawn joint.
#
# FDM's bore allowance is applied ONCE, to the external member only. Applying it
# to both (as the spider joint must, since only one member is printed) gave a
# printed pair double the intended slop -- 0.5 mm radial -- and that is what let
# the inner plug tilt and cross-thread before the malformed crests could catch.
STL_VARIANTS = {
    "resin": PrintVariant(clearance=0.10),   # SLA resolves fine threads well
    "fdm": PrintVariant(                     # FDM is coarser -> generous
        clearance=0.25,
        bore_joint=FDM_BORE_JOINT,
        bore_clearance_external=0.30,        # the whole allowance, on the shaft
        bore_clearance_internal=0.0,         # bore stays nominal
    ),
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
        for variant, cfg in STL_VARIANTS.items():
            tv = time.time()
            clr = cfg.clearance
            part = build_plug(PLUG, threads=True, clearance=clr,
                              bore_joint=cfg.bore_joint,
                              bore_clearance=cfg.bore_clearance_internal)
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
        for variant, cfg in STL_VARIANTS.items():
            tv = time.time()
            clr = cfg.clearance
            # Printed STLs get a plain tap-drill locking-screw hole (hand-tapped
            # later); the fine thread lives only in the STEP master.
            part = build_inner_plug(PLUG, threads=True, clearance=clr, top=top,
                                    locking_screw_thread=False,
                                    lock_counterbore_d=PRINTED_LOCK_COUNTERBORE_D,
                                    bore_joint=cfg.bore_joint,
                                    bore_clearance=cfg.bore_clearance_external)
            validate(part, f"inner_plug[{top}] ({variant})")
            stl_path = STL_DIR / f"inner_plug{suffix}_{variant}.stl"
            note = export_watertight_stl(part, stl_path, f"inner_plug[{top}] ({variant})")
            print(f"    {variant}: clearance={clr} mm radial [{note}] "
                  f"-> {stl_path.relative_to(CAD_DIR)}  ({time.time()-tv:.1f}s)")

    # ---- Combined STEP: both parts, assembled, as separate named objects ---
    plug_master.label = "Plug"
    # Seat the inner plug in the bore with its top flush with the plug top.
    seat = (PLUG.lower_h + PLUG.middle_h + PLUG.upper_h) - PLUG.ip_h
    # Spin the inner plug so its pivot hole meets the plug's cotter hole. This
    # is a placement choice, not a change to the part: the inner plug is a screw,
    # so where its features land relative to the plug depends on how far it is
    # wound in. Its own datum stays put -- the pivot hole is deliberately at
    # right angles to the two side blind holes, and rotating the part itself
    # would drive the pivot straight through one of them.
    phase = PLUG.cotter_bearing - PLUG.ip_pivot_bearing
    inner = Pos(0, 0, seat) * Rot(0, 0, phase) * inner_flat_master
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
