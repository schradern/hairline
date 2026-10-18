"""Active hairline settings and `use()`, the one call that sets the style."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

from hairline import entities
from hairline.brand import Brand, find_brand, load_brand
from hairline.fonts import register_fonts, resolve_family
from hairline.palettes import palette as resolve_palette
from hairline.tokens import load_tokens


@dataclass(frozen=True)
class Settings:
    font: str
    base_size: float
    sizes: dict[str, float] = field(default_factory=dict)
    palette: tuple[str, ...] = ()
    palette_name: str = "daylight"
    palette_label: str = "palette 'daylight'"
    locale: str = "en"
    background: str = "#ffffff"
    neutral: dict[str, str] = field(default_factory=dict)
    brand_name: str | None = None
    base_size_explicit: bool = False


_state: dict[str, object] = {"current": None, "announced": set(), "arguments": {}}
LOGGER = logging.getLogger("hairline")


def default_settings() -> Settings:
    tokens = load_tokens()
    name = tokens["default_palette"]
    return Settings(font=tokens["font"]["family"], base_size=tokens["type"]["base_size"],
                    palette=tuple(tokens["palettes"][name]), palette_name=name, palette_label=f"palette {name!r}",
                    locale=tokens["default_locale"], neutral=dict(tokens["neutral"]))


def current_settings() -> Settings:
    """The settings set by the last `use()`, or hairline's defaults."""
    return _state["current"] or default_settings()


def current_locale() -> str:
    return current_settings().locale


def reset() -> None:
    _state["current"] = None
    entities.configure({})


def role_size(settings: Settings, role: str) -> float:
    """Text size in pt for a role: an explicit override, else factor x base size."""
    return settings.sizes.get(role, load_tokens()["type"]["roles"][role]["factor"] * settings.base_size)


def validated_sizes(sizes: Mapping[str, float] | None) -> dict[str, float]:
    roles = load_tokens()["type"]["roles"]
    for role in sizes or {}:
        if role not in roles:
            raise ValueError(f"hairline: unknown text role {role!r} in sizes; use one of {', '.join(sorted(roles))}")
    return dict(sizes or {})


def palette_fields(palette: str | Sequence[str] | None) -> dict[str, object]:
    if palette is None:
        return {}
    colors = tuple(resolve_palette(palette))
    name = palette if isinstance(palette, str) else "custom"
    label = f"palette {name!r}" if isinstance(palette, str) else "custom palette"
    return {"palette": colors, "palette_name": name, "palette_label": label}


def resolve_brand(brand: object, output: str | None = None) -> Brand | None:
    if brand is False:
        return None
    if isinstance(brand, Brand):
        return brand
    if isinstance(brand, (list, tuple)):
        return load_brand(list(brand), output)
    path = find_brand() if brand is None else Path(os.fspath(brand))
    if path is None:
        return None
    loaded = load_brand(path, output)
    if brand is None and str(path) not in _state["announced"]:
        _state["announced"].add(str(path))
        LOGGER.info("Using brand '%s' from %s", loaded.name, path)
    return loaded


def brand_layer(base: Settings, brand: Brand | None) -> Settings:
    """Settings with the brand's values applied over hairline's defaults."""
    if brand is None:
        return base
    changes: dict[str, object] = {"brand_name": brand.name, "neutral": {**base.neutral, **brand.neutral},
                                  "sizes": validated_sizes(brand.sizes)}
    if brand.colors_used:
        changes |= {"palette": tuple(brand.colors_used), "palette_name": "brand",
                    "palette_label": f"brand '{brand.name}'"}
    if brand.font:
        changes["font"] = resolve_family(brand.font)
    if brand.base_size is not None:
        changes |= {"base_size": float(brand.base_size), "base_size_explicit": True}
    if brand.locale:
        changes["locale"] = brand.locale
    return Settings(**{**base.__dict__, **changes})


def reapply() -> None:
    """Apply the last `use()` call again (its own arguments, the current host context under them) — what a new
    host context calls. A session that never called `use()` has nothing to re-apply."""
    if _state["current"] is not None:
        use(**_state["arguments"])


def check_locale(locale: str | None) -> None:
    locales = load_tokens()["locales"]
    if locale is not None and locale not in locales:
        raise ValueError(f"hairline: unknown locale {locale!r}; available locales: {', '.join(sorted(locales))}")


def validated_entity_colors(colors: Mapping[str, str] | None) -> dict[str, str]:
    from hairline.color.space import parse_hex
    for name, value in (colors or {}).items():
        try:
            parse_hex(value)
        except ValueError as error:
            raise ValueError(f"hairline: colors[{name!r}]: {error}") from error
    return {str(name): value.lower() for name, value in (colors or {}).items()}


def use(font: str | None = None, base_size: float | None = None, sizes: Mapping[str, float] | None = None,
        palette: str | Sequence[str] | None = None, locale: str | None = None, background: str | None = None,
        brand: object = None, colors: Mapping[str, str] | None = None, output: str | None = None) -> Settings:
    """Set hairline's style for this session and return the active settings.

    Precedence: these arguments > the brand (`brand=` path or a list of layers from institution to document, or
    a `_brand.yml` found from the working directory up to the project root; `brand=False` disables the lookup)
    > hairline's defaults. `output` ("screen", "pdf", "html", "docx") applies the brand's overrides for it.
    """
    from hairline.host import host_context
    from hairline.style import rcparams_for
    _state["arguments"] = {"font": font, "base_size": base_size, "sizes": sizes, "palette": palette,
                           "locale": locale, "background": background, "brand": brand, "colors": colors,
                           "output": output}
    context = host_context()
    if context is not None:
        locale, base_size = locale or context.locale, base_size or context.base_size
        brand = context.brand if brand is None and context.brand is not None else brand
        output, font = output or context.output, font or context.design.get("font")
    register_fonts()
    check_locale(locale)
    explicit = validated_entity_colors(colors)
    resolved_brand = resolve_brand(brand, output)
    layered = brand_layer(default_settings(), resolved_brand)
    changes: dict[str, object] = {**palette_fields(palette)}
    if font is not None:
        changes["font"] = resolve_family(font)
    if sizes is not None:
        changes["sizes"] = {**layered.sizes, **validated_sizes(sizes)}
    if base_size is not None:
        changes |= {"base_size": float(base_size), "base_size_explicit": True}
    changes |= {"locale": locale or layered.locale, "background": background or layered.background}
    settings = Settings(**{**layered.__dict__, **changes})
    _state["current"] = settings
    entities.configure({**(resolved_brand.entity_colors if resolved_brand else {}), **explicit})
    matplotlib.rcParams.update(rcparams_for(settings))
    return settings
