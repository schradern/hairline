"""The wording of a palette that has fewer slots than a chart has categories."""

from __future__ import annotations

BRAND_ADVICE = ("list the brand's chart colours under defaults.hairline.categorical (colours named under "
                "color.palette are not slots until listed there), or give this chart colors=")
PALETTE_ADVICE = "fold small categories into 'Other' or split the figure into panels"


def slot_count(label: str, slots: int) -> str:
    """"brand 'X' has 1 slot" / "palette 'daylight' has 8 slots"."""
    return f"{label} has {slots} slot{'' if slots == 1 else 's'}"


def more_slots_advice(label: str) -> str:
    """A brand is short of slots because its file names too few chart colours, which merging categories doesn't
    fix; a hairline palette has eight, so a chart that needs more has too many categories."""
    return BRAND_ADVICE if label.startswith("brand ") else PALETTE_ADVICE
