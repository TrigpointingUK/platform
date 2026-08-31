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
* a **second pin spanner in the +X end** (``SidePinParams``), so the one tool
  also drives the *inner* plug. Two Ø6 steel pins drop into the inner plug's two
  Ø6.7 blind holes; the tool is then held with its major axis vertical and turned
  about that axis.

Those side pins force two changes to the shared body, so v3 does not use the
stock ``DRIVER``/``KEYSTORE`` instances -- it overrides them below into
``DRIVER_V3``/``KEYSTORE_V3``, leaving v1 and v2 exactly as they were printed:

* **The tool gets thicker** (40 -> 45 mm) **and squarer in profile**. The pins
  must be spaced 27 mm apart *vertically*, not across the tool: at the +X end the
  plan ellipse has narrowed so fast that a Y-spaced pair's bores would break out
  through the side wall 3.7 mm before reaching the surface. Stacked vertically
  they need 27 + 6.3 = 33.3 mm of *straight knurl band* to sit in, plus a wall
  top and bottom. v1's 40 mm body has only 25 mm of band, so the bores would
  break clean out of it. 45 mm buys 5 mm; the other 9 comes out of the shoulders,
  which shrink from 8 mm of rounded base edge and 7 mm of sculpted top to 3 mm of
  each. That is the real price of the side pins -- the tool keeps its plan
  ellipse exactly, but its profile is noticeably squarer, a thick knurled disc
  with softened edges rather than a discus.
* **The knurl fades out at both ends.** Every feature that breaks the rim there
  -- the pin mouths, and on the -X end the key flare, the short-arm slot and the
  finger scoop -- would otherwise truncate whatever teeth it landed on into thin
  sharp spikes.

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

from dataclasses import dataclass, field, replace

from common.specs import ThreadSpec
from models.driver_v1.params import DRIVER
from models.driver_v2.params import KEYSTORE


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


@dataclass(frozen=True)
class SidePinParams:
    """Ø6 steel pins in the +X end, for driving the **inner** plug.

    The inner plug has two blind holes in its top face (``PLUG.ip_side_spacing``
    apart, Ø``2*ip_side_r`` x ``ip_side_depth`` deep) -- the pin-spanner pattern.
    Two pins protruding from this end drop into them, so the same tool that
    breaks the big spider joint also turns the inner plug out of the bore. The
    pins are glued into blind bores exactly as v1's dowel pegs are: a clearance
    fit with annular keying grooves, a mouth chamfer and a vent, never a press
    fit (an interference fit wedges printed layers apart).

    They sit at **y = 0**, where the surface normal is exactly +X, so both bores
    meet the end square. Their **spacing is owned by the plug** and read from
    there at build time, like the peg spacing.

    **The mouths need a spherical dish, not a chamfer.** The +X tip has a plan
    radius of curvature of only 15 mm and is *narrower than the bore*: the body
    is 6.3 mm wide only 0.33 mm back from the tip. Over that last 0.33 mm the
    bore is wider than the nose it is being drilled into, so its wall runs out
    tangentially to the surface and each mouth ends up ringed by webs that taper
    to zero thickness -- knife edges, and unprintable besides. A 45 deg chamfer
    makes that worse, not better, because it needs the body to be 8.3 mm wide and
    that only happens 0.63 mm back.

    A **spherical countersink** fixes it at the root. A sphere of radius
    ``mouth_dish_r`` centred out on the bore axis, biting ``mouth_dish_d`` deep at
    the tip, *swallows the whole region where the bore is wider than the nose* --
    so the tangency never appears in the finished solid -- and its own rim meets
    the elliptical flank at a shallow angle everywhere, about 139 deg included.
    What is left is a shallow oval dimple at each pin, blending smoothly into the
    flank. It is the same trick that blunts the finger scoop's rim at the other
    end of the tool.

    This is why there is no truncated nose: ``nose_flat_back`` defaults to 0 and
    **the plan ellipse is left whole**. Cutting the tip off to a flat also works
    (and gives a bearing pad square to the pins), but it costs the tool's shape
    and 3 mm of bore depth for something the dish does without either.

    Held for this job the tool is a 120 mm lever turned about its own major axis;
    the grip is the knurled waist at |x| < 30, which the end fade leaves intact.
    """

    # ---- The pins (BOM items; only their bores are modelled) -------------
    pin_dia: float = 6.0  # [D] Ø6 silver-steel / dowel (in the plug's Ø6.7 holes)
    pin_bore_dia: float = 6.3  # [E] glue clearance: ~0.3 mm epoxy annulus, the
    #                              same allowance v1 gives its Ø8 dowels
    protrusion: float = 6.5  # [E] stick-out beyond the nose. The plug's side
    #                            holes are 8 mm deep, so this bottoms 1.5 mm
    #                            short and the pins take the load in shear.
    bore_depth: float = 14.0  # [E] embedment, from the ellipse's tip. NOT free:
    #                             the +X dowel peg bore's keying grooves reach
    #                             x = 43.45 and the lower pin bore passes right
    #                             over them, so the blind end has to stop short of
    #                             those. 14.0 puts it at x = 46.0, 2.55 mm clear.
    #                             The dish opens the outer 1.1 mm of it, leaving
    #                             ~12.9 mm of full-diameter grip on the pin --
    #                             2.1 x the pin diameter, against 2.5 x for v1's
    #                             pegs -- and the load here is pure transverse
    #                             shear in the LAYER PLANE (rotating about the
    #                             major axis pushes each pin along +/-Y), which is
    #                             the direction printed plastic bears best.

    # Keying + glue management, same scheme as v1's peg bores:
    groove_n: int = 2  # [E] annular grooves; cured epoxy keys into them. Two,
    #                      not v1's three: this bore is 11 mm long against v1's
    #                      25, and the grooves are spread over the middle 3 mm of
    #                      it, so three 1.5 mm rings would run together into one
    #                      continuous counterbore with no shoulders to key on.
    groove_depth: float = 0.8  # [E] radial extra depth of each groove
    groove_h: float = 1.5  # [E] axial height of each groove
    # ---- Mouth treatment: a spherical dish (see the class docstring) -----
    mouth_dish_r: float = 9.0  # [E] countersink sphere radius, centred on the
    #                               bore axis at (nose - d + r). A bigger radius
    #                               is a blunter blend, but it also reaches
    #                               further up and down the nose -- sqrt(2rd - d^2)
    #                               -- and on a 45 mm body there is only 6.0 mm of
    #                               band above each bore to reach into. r=10 at
    #                               d=2 reaches exactly 6.0 -- tangent to the
    #                               band/sculpt junction, the sort of exact touch
    #                               v2's mesh_gap exists to avoid -- so 9.0 backs
    #                               it off to 5.66 and keeps 0.34 mm of daylight.
    #                               0 falls back to the conical mouth_chamfer.
    mouth_dish_d: float = 2.0  # [E] how deep it bites on the axis, at the tip.
    #                              Enough that the sphere swallows the whole
    #                              region where the bore is wider than the nose,
    #                              which build_driver_v3 checks: this clears it by
    #                              0.52 mm and leaves a 132 deg rim.
    mouth_chamfer: float = 2.0  # [E] plain 45 deg lead-in, used ONLY when the
    #                               dish is switched off. It CAN do the job, but
    #                               only at this size or more: the cone has to
    #                               reach the corner of the breakout region, where
    #                               a point sits at the full bore radius in y and
    #                               z at once (r*sqrt(2) = 4.45 mm from the axis),
    #                               and 1.0 mm does not -- measured, it leaves 8
    #                               slivers in a 1331-point sample where 2.0 mm
    #                               leaves none. It is the cheaper option and the
    #                               rim is blunt enough to handle, just less blunt
    #                               than the dish: ~121 deg against ~136 deg.

    # ---- Truncated nose: the rejected alternative, kept switchable -------
    # Cutting the tip off to a flat face solves the same problem and throws in a
    # bearing pad square to the pins, but it costs the elliptical silhouette and
    # 3 mm of bore depth. The dish does the job without either, so this is OFF.
    nose_flat_back: float = 0.0  # [E] mm to cut off the +X tip; 0 = full ellipse
    nose_round: float = 1.5  # [E] fillet round the flat's rim, if one is cut
    vent_dia: float = 1.5  # [E] vent from the blind end so pushing a pin in
    #                          cannot hydraulic-lock on trapped epoxy
    vent_inset: float = 1.0  # [E] vent axis this far inboard of the blind end
    #                            (in the pocket the pin tip leaves empty)
    # Each vent runs to whichever face is nearer: the lower pin's drops to the
    # flat base, the upper pin's rises to the sculpted top, where it surfaces
    # inside the sighting groove alongside the existing peg vents.


# ---- v3's body overrides ------------------------------------------------
# v3 does not reshape v1: it hands build_driver_v1 a different DriverParams.
# v1 and v2 keep the stock DRIVER and print exactly as before.
DRIVER_V3 = replace(
    DRIVER,
    # 45 mm tall, with a 39 mm straight band (z 3..42) to carry the pin bores at
    # z = 9 and 36. That leaves 2.85 mm of wall under the lower mouth and over the
    # upper one -- thin, but thickening fast as each bore runs inboard, and the
    # figure the build-time check is set against.
    body_half_h=22.5,
    band_half_h=19.5,
    top_lip=0.0,  # no straight lip above the band: there is no room for one
    # The sculpted top now has only 3 mm of rise. Over v1's 16 mm of radius change
    # that makes the spline bulge 0.88 mm proud of the plateau -- a raised ridge
    # round the logo. Widening the plateau shortens the run the spline has to
    # cover and kills it (0.05 mm, on a par with v1's own 0.015).
    plateau_r=22.0,
    # ...but plateau_r also sets the logo's size, and a Ø44 plateau would render
    # it 1.6x larger than on v1 and v2. Drop the fill to hold the badge at exactly
    # the size it is on the other two: 22.0 * 0.541 = 11.9 = 14.0 * 0.85.
    logo_fill=0.541,
    # Teeth full depth to |x| = 30, gone by |x| = 45. The furthest-inboard thing
    # that breaks the rim is the finger scoop at |x| = 46.2, so 45 clears every
    # end feature; the 15 mm fade spans about 2.5 teeth, which reads as the knurl
    # dying away rather than stopping.
    knurl_fade_start=0.50,
    knurl_fade_end=0.75,
    knurl_crest_out=0.3,
)

# The key channel is specified as running along the tool's equator, so it has to
# follow body_half_h up. (build_driver_v3 checks that these two still agree.)
KEYSTORE_V3 = replace(
    KEYSTORE,
    z_plane=DRIVER_V3.body_half_h,
    # Soften the -X entrance. The knurl fade above does most of the work -- it is
    # the truncated teeth that made the spikes -- and these take the rest of what
    # can be taken: the finger scoop becomes a wide shallow cap (Ø28 x 6 deep)
    # whose rim meets the surface at about 46 deg rather than square on, and the
    # slot mouth loses its four sharp corner points. See the note in
    # build_driver_v3 for the one edge that is NOT fixed.
    scoop_r=20.0,
    scoop_depth=6.0,
    bar_slot_round=1.5,
)


# Single shared instances; import and override fields as measurements arrive.
SCREWSTASH = ScrewStashParams()
BASETRAY = BaseTrayParams()
SIDEPIN = SidePinParams()
