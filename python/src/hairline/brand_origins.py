"""Which brand layer set a value: its 1-based number, with the export type when an `outputs` override set it (that
override applies last, so it is looked for first). Mirrored in R's brand_origin()."""

from __future__ import annotations

from collections.abc import Sequence

CATEGORICAL_FALLBACK = ("primary", "secondary", "tertiary")


def has_path(layer: dict, keys: Sequence[str]) -> bool:
    node: object = layer
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return False
        node = node[key]
    return True


def layer_origin(layers: Sequence[dict], output: str | None, *keys: str) -> str:
    """'2' for the last layer that sets `keys`, '2, docx' when that layer's docx override does; '' when none does."""
    if output and keys[:2] == ("defaults", "hairline"):
        override = ("defaults", "hairline", "outputs", output, *keys[2:])
        for index in range(len(layers), 0, -1):
            if has_path(layers[index - 1], override):
                return f"{index}, {output}"
    for index in range(len(layers), 0, -1):
        if has_path(layers[index - 1], keys):
            return str(index)
    return ""


def slot_origins(layers: Sequence[dict], output: str | None, names: Sequence[str], palette: dict) -> list[str]:
    """A palette name comes from `color.palette`; a hex entry from `categorical`, else primary/secondary/tertiary."""
    origins = []
    for name in names:
        if name in palette:
            origins.append(layer_origin(layers, output, "color", "palette", name))
            continue
        candidates = [layer_origin(layers, output, "defaults", "hairline", "categorical"),
                      *(layer_origin(layers, output, "color", role) for role in CATEGORICAL_FALLBACK)]
        origins.append(next((origin for origin in candidates if origin), ""))
    return origins


def entity_origins(layers: Sequence[dict], output: str | None, entities: Sequence[str], groups: dict | None) -> dict:
    """A pinned colour comes from `colors`; a group member's tint from the group in `groups` that lists it."""
    origins = {}
    for name in entities:
        origin = layer_origin(layers, output, "defaults", "hairline", "colors", name)
        group = next((group for group, members in (groups or {}).items() if name in (members or [])), None)
        if not origin and group is not None:
            origin = layer_origin(layers, output, "defaults", "hairline", "groups", group)
        origins[name] = origin
    return origins
