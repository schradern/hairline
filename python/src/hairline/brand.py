"""Read `_brand.yml` (the brand.yml format) and map it onto hairline settings."""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from matplotlib import font_manager

from hairline.brand_entities import checked_entities, grouped_entities
from hairline.brand_origins import entity_origins, slot_origins
from hairline.color.adapt import adapt_readable
from hairline.color.check import check_palette
from hairline.color.space import HEX_PATTERN, hex_to_oklch
from hairline.tokens import load_tokens

ROOT_MARKERS = (".git", "_quarto.yml", "pyproject.toml", "DESCRIPTION")
NEUTRAL_KEYS = ("muted", "faint", "grid", "axis", "band")
OUTPUTS = ("screen", "pdf", "html", "docx")


@dataclass(frozen=True)
class Brand:
    name: str | None
    path: Path
    names: list[str]
    colors_given: list[str]
    colors_used: list[str]
    adapt: str = "readable"
    font: str | None = None
    heading_font: str | None = None
    heading_weight: int | None = None
    neutral: dict[str, str] = field(default_factory=dict)
    base_size: float | None = None
    sizes: dict[str, float] = field(default_factory=dict)
    locale: str | None = None
    sequential_hue: float | None = None
    diverging_hues: tuple[float, float] | None = None
    entity_colors: dict[str, str] = field(default_factory=dict)
    entity_failures: list[str] = field(default_factory=list)
    output: str | None = None
    layers: list[str] = field(default_factory=list)
    slot_origins: list[str] = field(default_factory=list)
    entity_origins: dict[str, str] = field(default_factory=dict)


def merged(base: dict, layer: dict) -> dict:
    """`layer` over `base`: mappings merge key by key, everything else (lists included) is replaced."""
    result = dict(base)
    for key, value in layer.items():
        result[key] = merged(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) \
            else value
    return result


def read_layer(path: Path) -> dict:
    try:
        content = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as error:
        raise ValueError(f"hairline: brand file {path} does not exist") from error
    except yaml.YAMLError as error:
        mark = getattr(error, "problem_mark", None)
        where = f"line {mark.line + 1}" if mark else "unknown position"
        raise ValueError(f"hairline: {path.name}: {where}: {getattr(error, 'problem', error)}") from error
    if not isinstance(content, dict):
        raise ValueError(f"hairline: {path.name}: the top level must be a mapping of sections")
    return content


class BrandFile:
    """One brand file, or layers from institution to document merged in order; error messages name the file
    (the layers, joined by '+') and the key path."""

    def __init__(self, paths: Path | list[Path], output: str | None = None):
        self.paths = [paths] if isinstance(paths, Path) else list(paths)
        self.path = self.paths[-1]
        self.label = " + ".join(path.name for path in self.paths)
        layers = [read_layer(path) for path in self.paths]
        self.font_dir = next((path.parent for path, layer in zip(reversed(self.paths), reversed(layers),
                                                                strict=True)
                              if isinstance(layer.get("typography"), dict) and "fonts" in layer["typography"]),
                             self.path.parent)
        content: dict = {}
        for layer in layers:
            content = merged(content, layer)
        self.layers, self.output = layers, output
        self.content = self.for_output(content, output)

    def for_output(self, content: dict, output: str | None) -> dict:
        """Apply `defaults.hairline.outputs.<output>` after all layers."""
        hairline = (content.get("defaults") or {}).get("hairline") or {}
        outputs = hairline.get("outputs") or {}
        for name in outputs:
            if name not in OUTPUTS:
                raise self.fail(f"defaults.hairline.outputs.{name}", f"must be one of {', '.join(OUTPUTS)}")
        if output is None or output not in outputs:
            return content
        return merged(content, {"defaults": {"hairline": outputs[output]}})

    def get(self, dotted: str, default: Any = None) -> Any:
        value: Any = self.content
        for key in dotted.split("."):
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value

    def fail(self, key: str, message: str) -> ValueError:
        return ValueError(f"hairline: {self.label}: {key}: {message}")


def palette_section(source: BrandFile) -> dict[str, str]:
    palette = source.get("color.palette", {}) or {}
    if not isinstance(palette, dict):
        raise source.fail("color.palette", "must map colour names to hex values")
    for name, value in palette.items():
        if not isinstance(value, str) or not HEX_PATTERN.match(value):
            raise source.fail(f"color.palette.{name}", f"{value!r} is not a 6-digit hex colour")
    return {str(name): value.lower() for name, value in palette.items()}


def resolve_color(source: BrandFile, key: str, value: Any, palette: dict[str, str]) -> str:
    if isinstance(value, str) and value in palette:
        return palette[value]
    if isinstance(value, str) and HEX_PATTERN.match(value):
        return value.lower()
    raise source.fail(key, f"{value!r} is not in color.palette and not a 6-digit hex colour")


def categorical_section(source: BrandFile, palette: dict[str, str]) -> tuple[list[str], list[str]]:
    entries = source.get("defaults.hairline.categorical")
    if entries is None:
        entries = [source.get(f"color.{role}") for role in ("primary", "secondary", "tertiary")]
        entries = [entry for entry in entries if entry is not None]
        if not entries:
            return [], []
    names, colors = [], []
    for index, entry in enumerate(entries):
        if isinstance(entry, str) and not entry.startswith("#") and entry not in palette:
            raise source.fail(f"defaults.hairline.categorical[{index}]", f"{entry!r} is not in color.palette")
        colors.append(resolve_color(source, f"defaults.hairline.categorical[{index}]", entry, palette))
        names.append(entry if entry in palette else colors[-1])
    return names, colors


def adapt_mode(source: BrandFile) -> str:
    mode = source.get("defaults.hairline.adapt", "readable")
    if mode not in ("exact", "readable"):
        raise source.fail("defaults.hairline.adapt", f"{mode!r} must be 'exact' or 'readable'")
    return mode


def warn_exact(name: str | None, names: list[str], colors: list[str]) -> None:
    report = check_palette(colors)
    problems = list(report.failures)
    problems += [f"{names[slot - 1]} ({colors[slot - 1]}) is below 3:1 on white; it gets heavier lines and darker "
                 "point fills" for slot in report.light_slots]
    if problems:
        warnings.warn(f"hairline: brand '{name}' (adapt: exact): {'; '.join(problems)}", UserWarning, stacklevel=3)


def neutral_section(source: BrandFile, palette: dict[str, str]) -> dict[str, str]:
    neutral = {}
    for role, token in (("foreground", "ink"), ("background", "surface")):
        if source.get(f"color.{role}") is not None:
            neutral[token] = resolve_color(source, f"color.{role}", source.get(f"color.{role}"), palette)
    for key in NEUTRAL_KEYS:
        if source.get(f"defaults.hairline.{key}") is not None:
            neutral[key] = resolve_color(source, f"defaults.hairline.{key}", source.get(f"defaults.hairline.{key}"),
                                         palette)
    return neutral


def register_brand_fonts(source: BrandFile) -> None:
    for index, entry in enumerate(source.get("typography.fonts", []) or []):
        kind = entry.get("source", "system") if isinstance(entry, dict) else "system"
        if kind == "file":
            for file_index, file_entry in enumerate(entry.get("files", []) or []):
                file_path = file_entry.get("path") if isinstance(file_entry, dict) else file_entry
                path = (source.font_dir / str(file_path)).resolve()
                if not path.is_file():
                    raise source.fail(f"typography.fonts[{index}].files[{file_index}]", f"font file {path} not found")
                font_manager.fontManager.addfont(str(path))
        elif kind == "google":
            family = str(entry.get("family", ""))
            warnings.warn(f"hairline: {source.label}: typography.fonts[{index}]: {family!r} comes from Google Fonts, "
                          f"which hairline does not download; install it (https://fonts.google.com/specimen/"
                          f"{family.replace(' ', '+')}) or put its files next to the brand file with source: file",
                          UserWarning, stacklevel=3)


def ramp_hues(source: BrandFile, palette: dict[str, str]) -> tuple[float | None, tuple[float, float] | None]:
    sequential = source.get("defaults.hairline.sequential")
    diverging = source.get("defaults.hairline.diverging")
    if diverging is not None and (not isinstance(diverging, list) or len(diverging) != 2):
        raise source.fail("defaults.hairline.diverging", "must list two colours, the low and the high pole")
    hue = hex_to_oklch(resolve_color(source, "defaults.hairline.sequential", sequential, palette))[2] \
        if sequential is not None else None
    pair = tuple(hex_to_oklch(resolve_color(source, "defaults.hairline.diverging", value, palette))[2]
                 for value in diverging) if diverging else None
    return hue, pair


def entity_section(source: BrandFile, palette: dict[str, str], names: list[str], used: list[str]) -> dict[str, str]:
    """`defaults.hairline.colors`: entity -> palette name or hex; palette names resolve to the colour in use."""
    mapping = source.get("defaults.hairline.colors", {}) or {}
    if not isinstance(mapping, dict):
        raise source.fail("defaults.hairline.colors", "must map entity names to palette names or hex values")
    resolved = {}
    for entity, value in mapping.items():
        key = f"defaults.hairline.colors.{entity}"
        if isinstance(value, str) and value in names:
            resolved[str(entity)] = used[names.index(value)]
        elif isinstance(value, str) and (value in palette or HEX_PATTERN.match(value)):
            resolved[str(entity)] = resolve_color(source, key, value, palette)
        else:
            raise source.fail(key, f"{value!r} is not in color.palette and not a 6-digit hex colour")
    return resolved


def brand_paths(path: str | os.PathLike | list) -> list[Path]:
    paths = [Path(os.fspath(item)) for item in path] if isinstance(path, (list, tuple)) else [Path(os.fspath(path))]
    if not paths:
        raise ValueError("hairline: brand needs at least one file")
    return paths


def load_brand(path: str | os.PathLike | list, output: str | None = None) -> Brand:
    """Parse a `_brand.yml` file, or layers from institution to document (later layers override earlier ones);
    `output` applies that export type's overrides. Raises ValueError naming the file, key and value."""
    if output is not None and output not in OUTPUTS:
        raise ValueError(f"hairline: output {output!r} must be one of {', '.join(OUTPUTS)}")
    source = BrandFile(brand_paths(path), output)
    palette = palette_section(source)
    names, given = categorical_section(source, palette)
    mode, name = adapt_mode(source), source.get("meta.name")
    if mode == "exact" and given:
        warn_exact(name, names, given)
    register_brand_fonts(source)
    locale = source.get("defaults.hairline.locale")
    if locale is not None and locale not in load_tokens()["locales"]:
        known = ", ".join(load_tokens()["locales"])
        raise source.fail("defaults.hairline.locale", f"{locale!r} must be one of {known}")
    hue, pair = ramp_hues(source, palette)
    used = adapt_readable(given) if mode == "readable" and given else list(given)
    entities, failures = checked_entities(entity_section(source, palette, names, used), mode, source.label)
    groups = source.get("defaults.hairline.groups", {})
    entities = grouped_entities(entities, groups, source.fail)
    return Brand(name=name, path=source.path, names=names, colors_given=given, output=output,
                 layers=[str(path.resolve()) for path in source.paths],
                 slot_origins=slot_origins(source.layers, output, names, palette),
                 entity_origins=entity_origins(source.layers, output, list(entities), groups),
                 colors_used=used, adapt=mode, entity_colors=entities, entity_failures=failures,
                 font=source.get("typography.base.family"), heading_font=source.get("typography.headings.family"),
                 heading_weight=source.get("typography.headings.weight"), neutral=neutral_section(source, palette),
                 base_size=source.get("defaults.hairline.base_size"),
                 sizes=dict(source.get("defaults.hairline.sizes", {}) or {}), locale=locale, sequential_hue=hue,
                 diverging_hues=pair)


def find_brand(start: str | os.PathLike | None = None) -> Path | None:
    """Look for `_brand.yml` from `start` upwards, stopping at the project root."""
    folder = Path(start or Path.cwd()).resolve()
    for candidate in (folder, *folder.parents):
        if (candidate / "_brand.yml").is_file():
            return candidate / "_brand.yml"
        if any((candidate / marker).exists() for marker in ROOT_MARKERS):
            return None
    return None


def brand_report(brand: Brand | None = None) -> str:
    """Plain-text report: the layers by number with their paths, then per slot the name, colour as given and as
    used, light slot and the layer that set it, the checks, and the pinned or grouped colours with their layers.
    `None` reports the brand the last `use()` applied."""
    if brand is None:
        from hairline.settings import active_brand
        brand = active_brand()
    if brand is None:
        return "No brand is active."
    report = check_palette(brand.colors_used) if brand.colors_used else None
    layers = brand.layers or [str(Path(brand.path).resolve())]
    rows = [f"Brand '{brand.name}' (adapt: {brand.adapt})",
            *(f"layer {index}: {path}" for index, path in enumerate(layers, start=1)),
            "slot  name        given    used     light  layer"]
    for slot, (name, given, used) in enumerate(zip(brand.names, brand.colors_given, brand.colors_used, strict=True),
                                               start=1):
        light = "yes" if report and slot in report.light_slots else ""
        origin = brand.slot_origins[slot - 1] if slot <= len(brand.slot_origins) else ""
        rows.append(f"{slot:<5} {name:<11} {given}  {used}  {light:<5}  {origin}".rstrip())
    if report is None:
        rows.append("checks: no colours")
    else:
        rows.append("checks: passed" if report.passed else f"checks: {'; '.join(report.failures)}")
    rows += [f"entity {name}: {color}" + (f" (layer {brand.entity_origins[name]})" if brand.entity_origins.get(name)
                                          else "") for name, color in brand.entity_colors.items()]
    rows += [f"entity check: {failure}" for failure in brand.entity_failures]
    return "\n".join(rows)
