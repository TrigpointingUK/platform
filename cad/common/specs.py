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
    form: str = "whitworth"  # "whitworth" (55 deg BSW) or "iso" (60 deg metric)
    provenance: str = "[E]"
    note: str = ""
