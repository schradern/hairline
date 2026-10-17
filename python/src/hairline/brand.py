"""Read `_brand.yml` (the brand.yml format) and map it onto hairline settings."""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from matplotlib import font_manager

from hairline.color.adapt import adapt_readable
from hairline.color.check import check_palette
from hairline.color.space import HEX_PATTERN, hex_to_oklch
from hairline.tokens import load_tokens

ROOT_MARKERS = (".git", "_quarto.yml", "pyproject.toml", "DESCRIPTION")
NEUTRAL_KEYS = ("muted", "faint", "grid", "axis", "band")


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


class BrandFile:
    """Parsed YAML with error messages that name the file and the key path."""

    def __init__(self, path: Path):
        self.path = path
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
        self.content = content

    def get(self, dotted: str, default: Any = None) -> Any:
        value: Any = self.content
        for key in dotted.split("."):
            if not isinstance(value, dict) or key not in value:
                return default
            value = value[key]
        return value

    def fail(self, key: str, message: str) -> ValueError:
        return ValueError(f"hairline: {self.path.name}: {key}: {message}")


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
                path = (source.path.parent / str(file_path)).resolve()
                if not path.is_file():
                    raise source.fail(f"typography.fonts[{index}].files[{file_index}]", f"font file {path} not found")
                font_manager.fontManager.addfont(str(path))
        elif kind == "google":
            warnings.warn(f"hairline: {source.path.name}: typography.fonts[{index}]: Google font download is not "
                          "supported; install the font or use source: file", UserWarning, stacklevel=3)


def ramp_hues(source: BrandFile, palette: dict[str, str]) -> tuple[float | None, tuple[float, float] | None]:
    sequential = source.get("defaults.hairline.sequential")
    diverging = source.get("defaults.hairline.diverging")
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


def load_brand(path: str | os.PathLike) -> Brand:
    """Parse a `_brand.yml` file; raises ValueError naming the file, key and value on problems."""
    source = BrandFile(Path(path))
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
    return Brand(name=name, path=source.path, names=names, colors_given=given,
                 colors_used=used, adapt=mode, entity_colors=entity_section(source, palette, names, used),
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


def brand_report(brand: Brand) -> str:
    """Plain-text table: slot, name, colour as given, as used, light slot, overall check."""
    report = check_palette(brand.colors_used) if brand.colors_used else None
    rows = [f"Brand '{brand.name}' from {brand.path} (adapt: {brand.adapt})",
            "slot  name        given    used     light"]
    for slot, (name, given, used) in enumerate(zip(brand.names, brand.colors_given, brand.colors_used, strict=True),
                                               start=1):
        light = "yes" if report and slot in report.light_slots else ""
        rows.append(f"{slot:<5} {name:<11} {given}  {used}  {light}")
    if report is None:
        rows.append("checks: no colours")
    else:
        rows.append("checks: passed" if report.passed else f"checks: {'; '.join(report.failures)}")
    return "\n".join(rows)
