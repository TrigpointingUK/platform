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


@dataclass(frozen=True)
class ThreadSpec:
    """A mating thread joint.

    ``major_diameter`` is the crest-to-crest diameter of the *external* member
    (the classic nominal size). The internal member is generated from the same
    nominal so the two mate by construction; printing clearance is applied
    separately at build time, never baked in here.
    """

    name: str
    major_diameter: float  # mm, nominal (external crest dia)
    pitch: float  # mm
    form: str = "whitworth"  # "whitworth" (55 deg BSW) or "iso" (60 deg metric)
    provenance: str = "[E]"
    note: str = ""


@dataclass(frozen=True)
class PlugParams:
    # ---- Outer plug: three stacked annular rings + through-bore -----------
    # [D] tags below match the render model's own annotations.
    upper_r: float = 46.0  # [D] 92 mm upper ring dia / 2
    upper_h: float = 6.0  # [D] 6 mm thick
    upper_chamfer: float = 3.0  # [D] 3 mm 45 deg chamfer, top outer edge
    middle_r: float = 31.9  # [D] ~63.8 mm dia / 2 (fraction under 64 mm)
    middle_h: float = 9.0  # [D] 9 mm thick
    lower_r: float = 23.0  # [D] 46 mm dia / 2
    lower_h: float = 9.0  # [D] 9 mm thick
    bore_r: float = 19.0  # [D] 38 mm inner dia / 2
    bore_chamfer: float = 1.0  # [D] 1 mm chamfer, top of bore

    # Clearance holes in the upper ring (for the spider shelf screws)
    clr_hole_r: float = 4.5  # [D] 9 mm clearance holes / 2
    clr_hole_spacing: float = 77.0  # [D] 77 mm apart (matches spider screwholes)

    # Cotter-pin cross hole through the lower annulus
    cotter_r: float = 1.5  # [D] 3 mm peg dia / 2
    cotter_z_from_shelf: float = 13.0  # [D] 13 mm below the upper-ring base

    # Bottom of bore left plain (unthreaded run-out)
    bore_thread_plain_bottom: float = 3.0  # [D] bottom 3 mm of bore plain
    # Of that plain run-out, the fraction nearest the thread that is bored out
    # to the thread's major (root) diameter; the remainder stays at the minor
    # (drill) diameter. The real plug has the upper half relieved.
    bore_relief_frac: float = 0.5  # [D] top half of the plain bottom at major dia

    # ---- Inner plug: threaded cylinder with blind holes ------------------
    ip_r: float = 18.9  # [D] ~37.8 mm dia / 2 (fraction under 38 mm)
    ip_h: float = 22.0  # [D] 22 mm thick
    ip_chamfer: float = 1.0  # [D] 1 mm chamfer, top edge
    ip_hole_r: float = 3.0  # [D] 6 mm blind holes / 2
    ip_centre_depth: float = 16.0  # [D] centre hole 16 mm deep
    ip_side_depth: float = 8.0  # [D] side holes 8 mm deep
    ip_side_spacing: float = 27.0  # [D] side holes 27 mm apart

    # Radial pivot hole near the base (for the cotter pin to bear on)
    ip_pivot_r: float = 1.5  # [E] 3 mm dia / 2
    ip_pivot_z: float = 3.5  # [E] 3.5 mm above the bottom face
    ip_pivot_bearing: float = 0.0  # [E] degrees, along +X

    # Threaded grub-screw hole (locks the inner plug against the bore).
    # A single radial hole from the outer face through to the central hole,
    # ~160 deg clockwise from the cotter hole (viewed from above) -> bearing
    # 200 deg (the cotter hole is at 0 deg). Thread spec is `grub_joint` below.
    ip_grub_z: float = 10.0  # [E] 10 mm above bottom
    ip_grub_bearing: float = 200.0  # [E] deg; ~160 CW from cotter (at 0 deg)

    # ---- Thread joints ---------------------------------------------------
    # All three measured as Whitworth (55 deg) form; pitch from a thread gauge
    # in TPI (threads per inch), pitch_mm = 25.4 / TPI. Major diameters remain
    # the dimensioned values (the gauge gives form + TPI, not diameter).
    #
    # Joint A: plug external <-> spider central ring (screws the plug in).
    spider_joint: ThreadSpec = field(
        default_factory=lambda: ThreadSpec(
            name="plug-to-spider",
            major_diameter=63.8,  # [D] ~63.8 mm middle-ring dia
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
    # Joint C: grub screw <-> inner-plug radial locking hole.
    grub_joint: ThreadSpec = field(
        default_factory=lambda: ThreadSpec(
            name="grubscrew",
            major_diameter=4.0,  # [D] ~4 mm (close to 5/32in BSW = 3.97 mm)
            pitch=25.4 / 32,  # [D] 32 TPI Whitworth = 0.794 mm
            form="whitworth",
            provenance="[D]",
            note="Measured Whitworth 55deg, 32 TPI (5/32in BSW is 32 TPI).",
        )
    )


# Single shared instance; import and override fields as measurements arrive.
PLUG = PlugParams()
