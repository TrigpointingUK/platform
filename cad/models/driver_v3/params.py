"""Parametric dimensions for the **screw-stashing driver tool** (v3).

All dimensions in **millimetres** (build123d's native unit). Provenance tags
match the convention used by the earlier drivers and the plug model:

    [D]  Dimensioned  - taken from a mating part / a measured original.
    [E]  Estimated    - a plausible guess, tune on the first print.
    [S]  Spec         - a nominal engineering-standard value (e.g. a tap drill).

v3 is the v2 key-storing driver (``models.driver_v2``) with a **pair of spare
screws stashed in the top face**. The screws are spares for the spider shelf
screws -- the ones that pass through the plug's two Ø9 mm upper-ring clearance
holes -- so losing one on a windy summit does not end the job.

Each stash is a single blind bore on the **major axis**, sunk from the flat top
plateau, in three coaxial sections (top to bottom):

    1. **head recess**  Ø = the plug's clearance hole, ``head_depth`` deep.
       The head is ``head_h`` tall, so a seated screw sits *below* flush and
       nothing protrudes to catch the palm when the tool is gripped.
    2. **shaft hole**   Ø ``tap_drill_dia``, ``shaft_len`` deep. Printed plain
       and **tapped by hand after printing** -- the screw threads into its own
       stash and cannot rattle or fall out when the tool is upside-down in a bag.
    3. **tap relief**   Ø ``relief_dia``, ``relief_depth`` deep. A taper tap's
       first several threads are only partly formed; without somewhere for that
       lead to run out, the full-form thread never reaches the bottom of section
       2. ``relief_dia`` is *over* the screw's major diameter, so the lead spins
       free and cuts nothing -- and the screw tip can never bottom out either.

The head-recess **diameter is owned by the plug** (``clr_hole_r``) and read from
there at build time, exactly as v1 reads the peg spacing: it is a physical
interface (the same screw passes through both), not a driver-local choice.

Coordinate frame is the driver's: z = 0 at the flat base, +z upward, major axis
along X (through the pegs), minor along Y.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from common.specs import ThreadSpec


@dataclass(frozen=True)
class ScrewStashParams:
    # ---- The stashed screw (BOM item; only its stash is modelled) --------
    screw_thread: ThreadSpec = field(
        default_factory=lambda: ThreadSpec(
            name="stash-screw",
            major_diameter=4.6,  # [D] measured over the thread crests
            pitch=0.8,  # [E] NOT yet gauged. The two candidates are 0.8 mm
            #                metric and 30 TPI (25.4/30 = 0.847 mm); they differ
            #                by 0.05 mm, which is below the tap-drill resolution
            #                (see tap_drill_dia), so the printed hole suits both.
            form="iso",
            provenance="[D]",
            note="Ø4.6 crest measured; pitch 0.8 mm or 30 TPI, not yet gauged. "
                 "Ø4.6/0.8 is also within a whisker of 2BA (Ø4.70, 0.81 mm), "
                 "which would be unsurprising on OS-era brass hardware. The "
                 "thread is NOT modelled -- the hole is printed plain and tapped "
                 "by hand -- so the form here is nominal only.",
        )
    )
    head_h: float = 4.8  # [D] head height, measured with calipers
    shaft_len: float = 10.0  # [D] under-head shaft length

    # ---- Stash bore: 1. head recess --------------------------------------
    # Diameter is read from the plug at build time (2 x PLUG.clr_hole_r = Ø9).
    head_depth: float = 5.0  # [D] head_h (4.8) rounded up: the head seats 0.2 mm
    #                            BELOW the plateau, so nothing protrudes into the
    #                            palm. Raise if a different screw head is taller.
    mouth_chamfer: float = 0.5  # [E] lead-in at the plateau, and it takes the
    #                               sharp printed edge off the rim

    # ---- Stash bore: 2. shaft hole (tapped by hand after printing) -------
    tap_drill_dia: float = 3.8  # [S] tap drill = major - pitch: 4.6 - 0.80 = 3.80
    #                               for a 0.8 mm pitch, 4.6 - 0.847 = 3.75 for
    #                               30 TPI. One Ø3.8 hole therefore suits either
    #                               (~76% and ~100% thread respectively -- both
    #                               tap comfortably in plastic, which forms as
    #                               much as it cuts). If your printer runs
    #                               vertical holes undersize, add the measured
    #                               shrinkage here rather than fighting the tap.
    tap_lead_chamfer: float = 0.5  # [E] countersink where the shaft hole opens
    #                                  into the head recess: it starts the tap
    #                                  square and stops the first thread tearing

    # ---- Stash bore: 3. tap relief ---------------------------------------
    relief_dia: float = 5.0  # [E] clear of the Ø4.6 crest, so the tap's tapered
    #                            lead spins free here and full-form thread runs
    #                            right to the bottom of the shaft section. Set
    #                            <= tap_drill_dia to disable the relief entirely.
    relief_depth: float = 8.0  # [E] ~9 threads at 0.85 mm pitch -- enough for a
    #                              taper (first) tap's whole lead, and far more
    #                              than a plug or bottoming tap needs

    # ---- Placement -------------------------------------------------------
    # On the major axis (y = 0), one stash each side of the logo. 23.0 mm centres
    # the Ø9 recess in the clear corridor of the top face: the embossed logo ends
    # at x = 9.1 and the sighting groove starts at x = 36.5 (the vent hole itself
    # at 37.75), so the corridor midpoint is 22.8. At 23.0 the recess spans
    # x = 18.5..27.5 -- wholly on the FLAT plateau (which runs to x = 28), so the
    # recess floor is a true flat counterbore and the tap starts square. Deeper
    # down, the Ø5 relief spans 20.5..25.5, well clear of the peg bore's keying
    # grooves at 33.55. ``build_driver_v3`` re-checks all of this at build time.
    stash_x: float = 23.0  # [E] stash centres at x = +/- this


# Single shared instance; import and override fields as measurements arrive.
SCREWSTASH = ScrewStashParams()
