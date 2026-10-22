"""Text styles for frame elements, derived from settings and the type scale."""

from __future__ import annotations

from hairline.fonts import face_weight
from hairline.settings import Settings, role_size
from hairline.tokens import load_tokens


def role_style(settings: Settings, role: str, weight: int | None = None, color: str | None = None) -> dict:
    """Family, size, weight and colour of a text role; the weight is that of a face the family has."""
    definition = load_tokens()["type"]["roles"][role]
    return {"family": settings.font, "size": role_size(settings, role),
            "weight": face_weight(settings.font, weight or definition["weight"]),
            "color": color or settings.neutral[definition["color"]]}


def header_styles(settings: Settings) -> dict[str, dict]:
    weights = load_tokens()["type"]
    ink, faint, muted = settings.neutral["ink"], settings.neutral["faint"], settings.neutral["muted"]
    return {"name": role_style(settings, "panel"), "letter": role_style(settings, "panel", 600, ink),
            "qualifier": role_style(settings, "label", 400, faint),
            "stat_label": role_style(settings, "label", 400, faint),
            "stat_value": role_style(settings, "label", weights["value_weight"], muted),
            "key_value": role_style(settings, "label", weights["key_weight"], ink)}


def header_gaps(settings: Settings) -> dict[str, float]:
    spacing, base = load_tokens()["spacing"], settings.base_size
    return {"qualifier": spacing["qualifier_gap"] * base, "pair": spacing["stats_pair"] * base,
            "stats_min": spacing["stats_pair"] * base, "letter": spacing["panel_letter_gap"] * base}
