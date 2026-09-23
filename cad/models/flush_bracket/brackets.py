"""The measurement database: per-style defaults and per-bracket overrides.

``params.py`` holds one set of dimensions. Real brackets vary, in two different
ways, and this keeps them apart:

* **By style.** Everything in one production era shares a legend layout and
  letter size. Those go in ``[styles.<name>]``.
* **By bracket.** Individual castings have their own quirks -- a kerning
  error, a deeper keyhole trough -- and those go in ``[brackets.<number>]``.

Both live in ``brackets.toml``, read with the standard library's ``tomllib``,
so the file can carry comments recording where a number came from. Keys are
field names of ``FlushBracketParams``; an unknown key raises rather than being
quietly ignored, because this file is hand-edited and a silently-dropped typo
would be indistinguishable from a measurement that did not take.

Adding a parameter later needs no change here: give it a field and a default in
``params.py`` and it is immediately settable at either layer.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields, replace
from functools import lru_cache
from pathlib import Path

from models.flush_bracket.params import FB, FlushBracketParams
from models.flush_bracket.styles import (
    DEFAULT_STYLE,
    BracketStyle,
    legend_number,
    resolve_style,
)

DB_PATH = Path(__file__).with_name("brackets.toml")

#: Keys that document an entry rather than dimension it.
META = frozenset({"trig_id", "name", "note", "measured_by", "measured_on"})


@dataclass(frozen=True)
class ResolvedBracket:
    """One bracket, with every layer of measurement already applied."""

    number: str | None          # as recorded in the database
    legend: str | None          # as cast on the plate; None if not a number
    style: BracketStyle
    params: FlushBracketParams
    applied: tuple[str, ...]    # which layers contributed, for reporting
    name: str = ""
    note: str = ""


@lru_cache(maxsize=1)
def _load() -> dict:
    if not DB_PATH.exists():
        return {}
    return tomllib.loads(DB_PATH.read_text())


def _field_names() -> frozenset[str]:
    return frozenset(f.name for f in fields(FlushBracketParams))


def _apply(params: FlushBracketParams, table: dict, where: str):
    """Fold one table's dimension keys onto ``params``; return (params, meta)."""
    valid = _field_names()
    updates, meta = {}, {}
    for key, value in table.items():
        if key in META:
            meta[key] = value
            continue
        if key not in valid:
            near = sorted(n for n in valid if n.split("_")[0] == key.split("_")[0])
            raise ValueError(
                f"{DB_PATH.name} [{where}]: unknown key {key!r}. "
                + (f"Did you mean one of {near}? " if near else "")
                + "Keys must be fields of FlushBracketParams."
            )
        # TOML has no tuples; the dataclass wants them for hashability.
        updates[key] = tuple(value) if isinstance(value, list) else value
    return (replace(params, **updates) if updates else params), meta


def resolve(fb_number: str | None,
            base: FlushBracketParams = FB) -> ResolvedBracket:
    """Resolve one bracket number to its style and its measured dimensions.

    Layers apply in order, each overriding the last: ``params.py`` defaults,
    then the style's table, then the bracket's own. A bracket is looked up by
    its number *as cast*, so ``3353`` and ``S3353`` find the same entry.
    """
    db = _load()
    style = resolve_style(fb_number) if fb_number else DEFAULT_STYLE
    legend = legend_number(fb_number) if fb_number else None

    params, applied, name, note = base, ["params.py"], "", ""

    style_table = db.get("styles", {}).get(style.name)
    if style_table:
        params, meta = _apply(params, style_table, f"styles.{style.name}")
        applied.append(f"styles.{style.name}")
        note = meta.get("note", "")

    if legend:
        entry = db.get("brackets", {}).get(legend)
        if entry:
            params, meta = _apply(params, entry, f"brackets.{legend}")
            applied.append(f"brackets.{legend}")
            name = meta.get("name", "")
            if meta.get("note"):
                note = meta["note"]

    return ResolvedBracket(
        number=fb_number, legend=legend, style=style, params=params,
        applied=tuple(applied), name=name, note=note,
    )


def known_brackets() -> list[str]:
    """Numbers with their own entry, as cast."""
    return sorted(_load().get("brackets", {}))
