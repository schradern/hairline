"""Active hairline settings and `use()`, the one call that sets the style."""

from __future__ import annotations

import logging
import math
import numbers
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import matplotlib

from hairline import entities
from hairline.brand import Brand, find_brand, load_brand
from hairline.color.ramps import diverging_ramp, sequential_ramp
from hairline.color.space import hex_to_oklch
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
    accent: str | None = None
    scheme: str = "light"
    ramps: dict[str, tuple[str, ...]] = field(default_factory=dict)


_state: dict[str, object] = {"current": None, "announced": set(), "arguments": {}}
LOGGER = logging.getLogger("hairline")


def default_settings() -> Settings:
    tokens = load_tokens()
    name = tokens["default_palette"]
    return Settings(font=tokens["font"]["family"], base_size=tokens["type"]["base_size"],
                    palette=tuple(tokens["palettes"][name]), palette_name=name, palette_label=f"palette {name!r}",
                    locale=tokens["default_locale"], neutral=dict(tokens["neutral"]))


def active_brand() -> Brand | None:
    """The brand the last `use()` applied, if any."""
    return _state.get("brand")


def current_settings() -> Settings:
    """The settings set by the last `use()`, or hairline's defaults; a host context that changed since is applied
    first, so the next figure already has its style."""
    from hairline.host import host_context
    host_context()
    return _state["current"] or default_settings()


def current_locale() -> str:
    return current_settings().locale


def reset() -> None:
    _state["current"], _state["brand"] = None, None
    entities.configure({})


def role_size(settings: Settings, role: str) -> float:
    """Text size in pt for a role: an explicit override, else factor x base size."""
    return settings.sizes.get(role, load_tokens()["type"]["roles"][role]["factor"] * settings.base_size)


def validated_sizes(sizes: Mapping[str, float] | None) -> dict[str, float]:
    roles = load_tokens()["type"]["roles"]
    for role, size in (sizes or {}).items():
        if role not in roles:
            raise ValueError(f"hairline: unknown text role {role!r} in sizes; use one of {', '.join(sorted(roles))}")
        check_positive(size, f"sizes[{role!r}]")
    return dict(sizes or {})


def check_background(background: object) -> None:
    from matplotlib.colors import is_color_like
    if background is not None and not (isinstance(background, str) and
                                       (background == "transparent" or is_color_like(background))):
        raise ValueError(f"hairline: background {background!r} is not a colour; use a hex value such as '#ffffff'")


def check_positive(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"hairline: {name} must be a number above zero; got {value!r}")


def palette_fields(palette: str | Sequence[str] | None) -> dict[str, object]:
    if palette is None:
        return {}
    colors = tuple(resolve_palette(palette))
    if not colors:
        raise ValueError("hairline: palette has no colours; give a palette name (see palettes()) or a list of hex "
                         "colours")
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
        check_positive(brand.base_size, "the brand's defaults.hairline.base_size")
        changes |= {"base_size": float(brand.base_size), "base_size_explicit": True}
    if brand.locale:
        changes["locale"] = brand.locale
    changes["ramps"] = brand_ramps(brand)
    return Settings(**{**base.__dict__, **changes})


def brand_ramps(brand: Brand) -> dict[str, tuple[str, ...]]:
    """The brand's ramps: `sequential` and `diverging` hues, else the hues of its first one and two colours."""
    used = brand.colors_used
    hue = brand.sequential_hue if brand.sequential_hue is not None else (hex_to_oklch(used[0])[2] if used else None)
    pair = brand.diverging_hues or ((hex_to_oklch(used[0])[2], hex_to_oklch(used[1])[2]) if len(used) > 1 else None)
    ramps = {} if hue is None else {"brand-sequential": tuple(sequential_ramp(hue))}
    return ramps | ({} if pair is None else {"brand-diverging": tuple(diverging_ramp(*pair))})


def reapply() -> None:
    """Apply the last `use()` call again (its own arguments, the current host context under them) — what a new
    host context calls. A session that never called `use()` has nothing to re-apply."""
    if _state["current"] is not None:
        use(**_state["arguments"])


def scheme_fields(scheme: str | None, background: str | None, accent: str | None) -> dict[str, object]:
    """The dark scheme swaps every neutral token (a brand's light neutrals do not carry over); the accent is
    checked as a hex colour."""
    if scheme not in (None, "light", "dark"):
        raise ValueError(f"hairline: scheme {scheme!r} must be 'light' or 'dark'")
    fields: dict[str, object] = {"scheme": scheme or "light"}
    if accent is not None:
        fields["accent"] = validated_entity_colors({"accent": accent})["accent"]
    if scheme == "dark":
        neutral = dict(load_tokens()["neutral_dark"])
        fields |= {"neutral": neutral, "background": background or neutral["surface"]}
    return fields


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
        brand: object = None, colors: Mapping[str, str] | None = None, output: str | None = None,
        accent: str | None = None, scheme: str | None = None) -> Settings:
    """Set hairline's style for this session and return the active settings.

    Precedence: these arguments > the brand (`brand=` path or a list of layers from institution to document, or
    a `_brand.yml` found from the working directory up to the project root; `brand=False` disables the lookup)
    > hairline's defaults. `output` ("screen", "pdf", "html", "docx") applies the brand's overrides for it.
    `palette` is a palette or purpose-set name ("calm", "pair"; see `palettes()`) or a list of hex colours;
    `colors` pins colours to names ({"Unit B": "#e79d01"}) across every chart. `accent` colours a lone series
    (charts without groups); `scheme="dark"` uses the dark neutral tokens.
    """
    from hairline.host import host_context
    from hairline.style import rcparams_for
    # Kept for reapply() once they have been applied: a call that fails must not come back with every new context.
    arguments = {"font": font, "base_size": base_size, "sizes": sizes, "palette": palette, "locale": locale,
                 "background": background, "brand": brand, "colors": colors, "output": output, "accent": accent,
                 "scheme": scheme}
    context = host_context()
    if context is not None:
        locale, base_size = locale or context.locale, base_size or context.base_size
        brand = context.brand if brand is None and context.brand is not None else brand
        output, font = output or context.output, font or context.design.get("font")
        accent, scheme = accent or context.design.get("accent"), scheme or context.design.get("scheme")
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
        check_positive(base_size, "base_size")
        changes |= {"base_size": float(base_size), "base_size_explicit": True}
    check_background(background)
    changes |= {"locale": locale or layered.locale, "background": background or layered.background}
    changes |= scheme_fields(scheme, background, accent)
    settings = Settings(**{**layered.__dict__, **changes})
    _state["current"], _state["brand"], _state["arguments"] = settings, resolved_brand, arguments
    entities.configure({**(resolved_brand.entity_colors if resolved_brand else {}), **explicit})
    matplotlib.rcParams.update(rcparams_for(settings))
    return settings
