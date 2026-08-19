"""Parametric dimensions for the OS trig-pillar plug assembly.

All dimensions in **millimetres** (build123d's native unit).

Every value carries a provenance tag so the confidence level is explicit:

    [D]  Dimensioned  - taken from a drawing or a measured original.
    [E]  Estimated    - a plausible guess, NOT yet confirmed against a real part.
    [S]  Spec         - a nominal engineering-standard value (e.g. an ISO pitch).

Values were ported from the Blender render model
(``Blender/Hotine/trig_pillar.py``), where they were expressed in metres and
several were only ever intended to *look* right for rendering. Threads in
particular were bump-maps with no helix angle, so their pitch/form here are
best-effort estimates flagged [E]. When a real plug is measured (calipers +
thread gauge) or an Ordnance Survey drawing is obtained, update the [E]/[S]
values below and re-run ``build.py`` -- no geometry code needs to change.

Coordinate frame for both parts: z = 0 at the part's lowest face, +z upward,
revolved about the Z axis. This is independent of the pillar-assembly frame
used in the render model.
"""

from dataclasses import dataclass, field

from common.specs import ThreadSpec


@dataclass(frozen=True)
class PlugParams:
    # ---- Outer plug: three stacked annular rings + through-bore -----------
    # [D] tags below match the render model's own annotations.
    upper_r: float = 46.0  # [D] 92 mm upper ring dia / 2
    upper_h: float = 6.8  # [D] 6.8 mm thick, measured on the brass original
    upper_chamfer: float = 6.8 / 3  # [E] 45 deg chamfer, top outer edge. On the
    #                                   original the bevel is about a third of the
    #                                   ring's thickness, the rest cylindrical
    #                                   (judged by eye side-on, hence [E]).
    middle_r: float = 32.35  # [D] 64.7 mm dia / 2 = the spider thread's crest;
    #                            only used for the threads-off preview, so it must
    #                            track spider_joint.major_diameter below
    middle_h: float = 9.8  # [D] 9.8 mm thick, measured on the brass original
    lower_r: float = 23.0  # [D] 46 mm dia / 2
    lower_h: float = 10.0  # [D] 10 mm thick, measured on the brass original
    bore_r: float = 19.0  # [D] 38 mm inner dia / 2
    bore_chamfer: float = 1.0  # [D] 1 mm chamfer, top of bore

    # Clearance holes in the upper ring (for the spider shelf screws)
    clr_hole_r: float = 4.5  # [D] 9 mm clearance holes / 2
    clr_hole_spacing: float = 77.0  # [D] 77 mm apart (matches spider screwholes)

    # Cotter-pin cross hole through the lower annulus
    cotter_r: float = 1.5  # [D] 3 mm peg dia / 2
    cotter_z_from_shelf: float = 13.0  # [D] 13 mm below the upper-ring base

    # Bottom of bore left plain (unthreaded run-out)
    bore_thread_plain_bottom: float = 4.5  # [D] bottom 4.5 mm of bore plain
    # Of that plain run-out, the fraction nearest the thread that is bored out
    # to the thread's major (root) diameter; the remainder stays at the minor
    # (drill) diameter. The real plug has the upper half relieved.
    bore_relief_frac: float = 2.5 / 4.5  # [D] of the 4.5 mm plain run, the upper
    #                                        2.5 mm is at major dia and the bottom
    #                                        2.0 mm stays at the drill (minor) dia

    # ---- Inner plug: threaded cylinder with blind holes ------------------
    ip_r: float = 18.9  # [D] ~37.8 mm dia / 2 (fraction under 38 mm)
    ip_h: float = 24.2  # [D] 24.2 mm thick, measured on the brass original
    ip_chamfer: float = 1.0  # [D] 1 mm chamfer, top edge
    ip_hole_r: float = 3.0  # [D] 6 mm blind holes / 2
    ip_centre_depth: float = 16.0  # [D] centre hole 16 mm deep
    ip_side_depth: float = 8.0  # [D] side holes 8 mm deep
    ip_side_spacing: float = 27.0  # [D] side holes 27 mm apart

    # Radial pivot hole near the base (for the cotter pin to bear on)
    ip_pivot_r: float = 1.5  # [E] 3 mm dia / 2
    ip_pivot_z: float = 4.4  # [E] above the inner plug's bottom face. Derived, not
    #                            measured: the inner plug seats flush with the plug
    #                            top, so its base sits at total_h - ip_h = 2.4 mm,
    #                            and the cotter hole is at 19.8 - 13 = 6.8 mm; 6.8 -
    #                            2.4 = 4.4 puts the two holes on one axis. Re-derive
    #                            if ip_h, any ring height or cotter_z_from_shelf move.
    ip_pivot_bearing: float = 0.0  # [E] degrees, along +X

    # Recessed locking-screw hole (locks the inner plug against the bore).
    # A single radial hole from the outer face through to the central hole,
    # ~160 deg clockwise from the cotter hole (viewed from above) -> bearing
    # 200 deg (the cotter hole is at 0 deg). The first 8.3 mm is a smooth
    # Ø6.3 mm counterbore, followed by a 45° taper into the thread below.
    ip_lock_z: float = 10.0  # [E] 10 mm above bottom
    ip_lock_bearing: float = 200.0  # [E] deg; ~160 CW from cotter (at 0 deg)
    ip_lock_counterbore_d: float = 6.3  # [D] smooth entry diameter
    ip_lock_counterbore_depth: float = 8.3  # [D] depth from outer surface

    # ---- Thread joints ---------------------------------------------------
    # All three measured as Whitworth (55 deg) form; pitch from a thread gauge
    # in TPI (threads per inch), pitch_mm = 25.4 / TPI. Major diameters remain
    # the dimensioned values (the gauge gives form + TPI, not diameter).
    #
    # Joint A: plug external <-> spider central ring (screws the plug in).
    spider_joint: ThreadSpec = field(
        default_factory=lambda: ThreadSpec(
            name="plug-to-spider",
            major_diameter=64.7,  # [D] re-measured 2026-08-19; supersedes the
            #                          earlier ~63.8 carried over from the render model
            pitch=25.4 / 8,  # [D] 8 TPI Whitworth = 3.175 mm
            form="whitworth",
            provenance="[D]",
            note="Measured Whitworth 55deg, 8 TPI.",
        )
    )
    # Joint B: inner-plug external <-> plug bore internal.
    bore_joint: ThreadSpec = field(
        default_factory=lambda: ThreadSpec(
            name="innerplug-to-bore",
            major_diameter=38.0,  # [D] = bore dia
            pitch=25.4 / 14,  # [D] 14 TPI Whitworth = 1.814 mm
            form="whitworth",
            provenance="[D]",
            note="Measured Whitworth 55deg, 14 TPI.",
        )
    )
    # Joint C: locking screw <-> inner-plug radial locking hole.
    locking_screw_joint: ThreadSpec = field(
        default_factory=lambda: ThreadSpec(
            name="locking-screw",
            major_diameter=4.0,  # [D] ~4 mm (close to 5/32in BSW = 3.97 mm)
            pitch=25.4 / 32,  # [D] 32 TPI Whitworth = 0.794 mm
            form="whitworth",
            provenance="[D]",
            note="Measured Whitworth 55deg, 32 TPI (5/32in BSW is 32 TPI).",
        )
    )


# Single shared instance; import and override fields as measurements arrive.
PLUG = PlugParams()
