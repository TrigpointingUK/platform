"""Generic engineering specs shared across models.

``ThreadSpec`` describes a mating thread joint and is model-agnostic, so it
lives here rather than beside any one model's parameters.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    # "whitworth" (55 deg BSW), "iso" (60 deg metric) or "trapezoid" (a
    # 3D-printable 90 deg form -- see ``crest_flat``).
    form: str = "whitworth"
    provenance: str = "[E]"
    note: str = ""
    # ``trapezoid`` form only: the axial width of the crest flat, in mm. It is
    # the single free parameter of that form -- the depth and the flank angle
    # follow from it and the pitch (see ``common.threads``). Ignored otherwise.
    crest_flat: float = 0.0
