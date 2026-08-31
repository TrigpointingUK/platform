"""Parametric dimensions for the **screw-stashing driver tool** (v3).

All dimensions in **millimetres** (build123d's native unit). Provenance tags
match the convention used by the earlier drivers and the plug model:

    [D]  Dimensioned  - taken from a mating part / a measured original.
    [E]  Estimated    - a plausible guess, tune on the first print.
    [S]  Spec         - a nominal engineering-standard value (e.g. a tap drill).

v3 is the v2 key-storing driver (``models.driver_v2``) with two additions:

* a **pair of spare screws stashed in the top face** (``ScrewStashParams``).
  The screws are spares for the spider shelf screws -- the ones that pass
  through the plug's two Ø9 mm upper-ring clearance holes -- so losing one on a
  windy summit does not end the job.
* a **magnetic tray recessed into the base** (``BaseTrayParams``), for the small
  ferrous oddments a plug swap generates.

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


@dataclass(frozen=True)
class BaseTrayParams:
    """A magnetic parts tray recessed into the tool's flat base.

    **Every dimension here is set by printability, not by taste.** The tool is
    printed base-down on the plate (a smooth base, symmetric elliptical layer
    marks on top -- it works, so nothing should force a re-orientation), which
    makes this tray a cavity whose roof the printer has to close *over air*. The
    chamfers below are what keep the slicer from needing support inside it:

    * **Chamfers, never fillets, on anything facing the plate.** A concave fillet
      between the tray wall and its roof sweeps through every overhang angle from
      0 deg to 90 deg, and the fully horizontal part is right where it meets the
      roof. Worse, the slicer reads it as a *sloped surface* rather than a bridge,
      so it gets none of the bridge flow / fan / anchoring treatment and simply
      droops. A 45 deg chamfer holds one constant, self-supporting angle instead.
      (A sharp 90 deg corner is second best -- the slicer at least recognises a
      clean bridge. The fillet is the worst of the three.)
    * Each chamfer below is **45 deg by construction**: its height equals its
      radial run, so no field can be edited into an unprintable overhang.
    * ``roof_chamfer`` also shortens the one span that no chamfer can remove --
      the flat roof, which must bridge whatever the wall does.
    """

    # ---- The tray --------------------------------------------------------
    dia: float = 35.0  # [E] mouth Ø at the base face
    depth: float = 5.0  # [E] to the roof
    roof_chamfer: float = 2.0  # [E] 45 deg, closing the wall into the roof. The
    #                              roof is therefore Ø(dia - 2*this) = Ø31, which
    #                              is the span the printer bridges. Raise it to
    #                              shorten that bridge (at 5.0 the tray becomes a
    #                              fully drafted Ø35 -> Ø25 cone, the safest
    #                              possible shape); lower it only if something
    #                              has to sit flat and full-width in the tray.
    mouth_chamfer: float = 0.5  # [E] 45 deg at the base face. Absorbs the
    #                               first-layer squish ("elephant's foot"), which
    #                               would otherwise leave the mouth slightly
    #                               undersize with a rolled lip.

    # ---- Retention magnet (BOM item; only its pocket is modelled) --------
    # Same convention as the dowel bores and v2's magnet: a clearance pocket for
    # an epoxy annulus, never an interference fit into printed plastic.
    magnet_dia: float = 8.0  # [D] Ø8 disc
    magnet_thick: float = 3.0  # [D] 3 mm thick
    magnet_pocket_dia: float = 8.3  # [E] glue clearance: ~0.3 mm epoxy annulus
    magnet_pocket_depth: float = 3.3  # [E] a touch over the disc, so it seats
    #                                     just below the tray roof
    magnet_mouth_chamfer: float = 0.5  # [E] 45 deg where the pocket opens into
    #                                      the roof. This one earns its keep
    #                                      twice: it is the usual lead-in and
    #                                      glue fillet, AND it is what keeps the
    #                                      pocket printable. The pocket's mouth
    #                                      is a hole in the middle of the roof's
    #                                      bridge layer, so its perimeter is laid
    #                                      down in mid-air and sags inward; the
    #                                      chamfer puts that sagging loop at
    #                                      Ø(pocket + 2*this), clear of the bore,
    #                                      so droop cannot foul the magnet.


# Single shared instances; import and override fields as measurements arrive.
SCREWSTASH = ScrewStashParams()
BASETRAY = BaseTrayParams()
