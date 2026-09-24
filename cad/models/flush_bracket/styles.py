"""Bracket lettering styles, resolved from the flush-bracket number.

The lettering on a flush bracket is not one design. It varies -- in layout, in
letter size and in weight -- and the variation is **systematic by number
range**, because the ranges correspond to production eras. So the number alone
gets the style right for the great majority of brackets, before any photograph
is consulted.

What was checked, and how
-------------------------
The ranges below come from the TrigpointingUK wiki and bench-marks.org.uk, and
were then checked against the live corpus: all 26,978 trigs from
``/v1/trigs/export`` (8,302 of which carry a number), plus flush-bracket
photographs (``tphoto.type == 'F'``) sampled from each range. What that
confirmed, and corrected:

* **No S29xx exists.** OS skipped the S2900 series and resumed at S3000; the
  corpus contains no S-number between S2900 and S2999 at all.
* **Nothing below S1268.** The low S-series (S01-S1134, which carry the ``S``
  *below* the number) went on wall brackets, not pillars. That style therefore
  does not arise here at all, and is deliberately not modelled.
* **No G or L series** on trigs either -- also wall-bracket series.
* **BsM numbers carry no prefix.** On S3200-S3699 the ``S`` moves up into the
  legend, which reads ``B S M``, and the number below is bare. This is visible
  in the corpus as the same bracket being recorded both ways -- 3475 and S3475
  are one bracket -- so ``resolve_style`` normalises the two forms together.
* **Letters got bigger and bolder over time.** Early brackets (2GL, low S) have
  noticeably lighter, smaller legends than S3700+ and the 5-digit series, where
  ``O S B M`` nearly fills the plate width.

Letterforms
-----------
There is no typeface here, and there was never going to be one. The cast
numerals are geometric -- flat bars, straight diagonals, circular bowls -- and
no digital font has them. They are drawn instead, as skeletons swept with a
circular pen, in ``glyphs.py``. A style may one day select between variant
glyph sets; for now there is a single set and the weight comes from
``let_stroke_w`` and ``num_stroke_w``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BracketStyle:
    """How one era of flush bracket carries its lettering."""

    name: str
    era: str
    #: Where the series letter lives.
    #:   "in-number"  -- part of the number below, e.g. "S1852"
    #:   "in-legend"  -- between the B and the M, legend reads "B S M" (BsM)
    #:   "none"       -- no series letter at all (2GL and the 5-digit series)
    series_letter: str
    #: Multiplier on the measured O/S/B/M letter boxes in ``params``.
    letter_scale: float
    note: str = ""

    @property
    def legend_has_middle_s(self) -> bool:
        return self.series_letter == "in-legend"


STYLES = {
    "2gl": BracketStyle(
        name="2gl",
        era="Second Geodetic Levelling, 1912-21 (applied from 1935/36)",
        series_letter="none",
        letter_scale=0.92,
        note="Unused plates left over from the 2GL, put on the earliest "
             "primary stations. Bare number, no prefix letter.",
    ),
    "s-early": BracketStyle(
        name="s-early",
        era="Secondary levelling, 1930s",
        series_letter="in-number",
        letter_scale=0.92,
        note="Lighter, smaller legend than the later series.",
    ),
    "bsm": BracketStyle(
        name="bsm",
        era="c.1940",
        series_letter="in-legend",
        letter_scale=1.0,
        note="The 'BsM' brackets. The number font was enlarged until there "
             "was no room for a prefix, so the S moved into the legend "
             "between the B and the M, and the number below is bare.",
    ),
    "s-late": BracketStyle(
        name="s-late",
        era="post-war Secondary",
        series_letter="in-number",
        letter_scale=1.0,
        note="Bold, large legend filling most of the plate width.",
    ),
    "five-digit": BracketStyle(
        name="five-digit",
        era="late Secondary, 5-digit numbering",
        series_letter="none",
        letter_scale=1.0,
        note="Five digits left no room for the S, so it was dropped.",
    ),
    "unknown": BracketStyle(
        name="unknown",
        era="unknown",
        series_letter="in-number",
        letter_scale=1.0,
        note="Fallback: the number is unreadable, absent or not a recognised "
             "series. The legend is rendered; no number is.",
    ),
}

DEFAULT_STYLE = STYLES["s-late"]

#: Numbers recorded as free text rather than a bracket number.
_NOT_A_NUMBER = re.compile(
    r"^(no\s*fb|none|unknown|missing|n/?a|fbm|-+)?$", re.IGNORECASE
)


def parse_number(fb_number: str | None) -> tuple[str | None, int | None]:
    """Split a recorded number into (series letter, value).

    Returns ``(None, None)`` when the field does not hold a bracket number --
    the corpus records absences as free text ("No FB", "NONE", "Unknown"), and
    carries a block of internal ``u###`` placeholders.
    """
    if not fb_number:
        return None, None
    s = fb_number.strip().upper()
    if not s or _NOT_A_NUMBER.match(s):
        return None, None
    # Only S, G and L were ever real series letters. Anything else prefixed to
    # digits is not a bracket number -- notably the corpus's block of internal
    # ``u###`` placeholders, which would otherwise parse as a "U series".
    m = re.fullmatch(r"([SGL]?)0*(\d{1,5})", s)
    if not m:
        return None, None
    return (m.group(1) or None), int(m.group(2))


def resolve_style(fb_number: str | None) -> BracketStyle:
    """Pick the lettering style for a bracket number.

    Ranges are inclusive. The BsM range is matched on the **value alone**, with
    or without an S, because a BsM plate's number is bare and the corpus holds
    both spellings for the same bracket.
    """
    letter, value = parse_number(fb_number)
    if value is None:
        return STYLES["unknown"]
    if 3200 <= value <= 3699:
        return STYLES["bsm"]
    if letter is None:
        if value <= 3000:
            return STYLES["2gl"]
        if value >= 10000:
            return STYLES["five-digit"]
        # A bare 3001-9999: almost certainly an S-series bracket recorded
        # without its prefix. Treat it as such rather than as a 2GL plate.
        return STYLES["s-late"] if value >= 3700 else STYLES["s-early"]
    if value >= 10000:
        return STYLES["five-digit"]
    return STYLES["s-late"] if value >= 3700 else STYLES["s-early"]


def legend_number(fb_number: str | None) -> str | None:
    """The number exactly as it is cast on the plate, or None.

    Not the same as the recorded value: a BsM plate carries a bare number even
    when the database spells it with an S, and the 2GL and 5-digit series never
    had a prefix.
    """
    letter, value = parse_number(fb_number)
    if value is None:
        return None
    style = resolve_style(fb_number)
    if style.series_letter == "in-number":
        return f"{letter or 'S'}{value}"
    return str(value)
