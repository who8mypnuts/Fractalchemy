"""The theme model: a few *seed* colours in, every colour role the application paints with out. Pure Python, no Qt.

A catalogue entry (`Seed`) names about fourteen colours taken from a theme's published palette:

    bg        the window / panel background        fg       body text
    surface   buttons, tool bars, tabs              dim      secondary text
    base      editors, lists, inputs (the theme's canonical *editor* background)
    accent    selection and active states           comment  comment grey
    red, orange, yellow, green, cyan, blue, purple  the palette's hues

plus optional `overrides` for a theme's iconic mappings (Monokai's pink keywords, Nord's Frost keywords …).
`derive(seed)` turns that into a `Theme`: a complete role → colour table (`ROLES`). Every role has a colour, so
nothing is ever painted with a hard-coded fallback.

**Readability is a rule, not a hope.** `CONTRAST_RULES` lists which role must stand out from which background, and by how
much (WCAG AA: 4.5:1 for text, 3:1 for comments, placeholders and disabled text). `derive` enforces it with
`ensure_contrast`, which nudges a failing colour towards the theme's text colour just far enough. A published palette
stays faithful wherever it is already readable and is corrected wherever it is not (many themes' own comment greys
sit at 2.3–2.8:1). The test-suite checks every rule for every theme.

Canvases (the Transform Editor, previews, the timeline) are dark on every theme, because the classic transform colours
need a dark ground. Dark themes darken their own window colour for them; light themes use a neutral charcoal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

WHITE, BLACK = "#ffffff", "#000000"
LIGHT_CANVAS = "#1b1c20"            # the canvas ground of light themes (canvases are always dark)

# Every colour role a theme provides, grouped as the application uses them.
UI_ROLES = ("window", "window_text", "base", "alt_base", "text", "dim_text", "button", "button_text", "border", "accent",
            "accent_text", "link", "tooltip", "tooltip_text", "placeholder", "disabled_text")
STATUS_ROLES = ("error", "warning", "success", "info", "error_soft", "warning_soft", "success_soft", "info_soft")
EDITOR_ROLES = ("editor_bg", "editor_fg", "gutter", "gutter_fg", "current_line", "selection", "selection_fg", "error_line",
                "match")
SYNTAX_ROLES = ("keyword", "type", "function", "builtin", "string", "comment", "number", "preprocessor", "annotation",
                "preset", "special", "api", "member", "state", "constant", "decorator", "definition", "meta")
ORIGIN_KINDS = ("builtin", "apophysis", "jwildfire", "user")
ORIGIN_ROLES = tuple(f"origin_{kind}{part}" for kind in ORIGIN_KINDS for part in ("", "_text"))
CANVAS_ROLES = ("canvas_bg", "canvas_grid", "canvas_axis", "canvas_text", "canvas_accent")
GLYPH_ROLES = ("glyph_ink", "glyph_accent")
ROLES = UI_ROLES + STATUS_ROLES + EDITOR_ROLES + SYNTAX_ROLES + ORIGIN_ROLES + CANVAS_ROLES + GLYPH_ROLES

TEXT, SOFT, DECORATION = 4.5, 3.0, 3.0     # WCAG AA for text; 3:1 for comments, hints, disabled text and glyphs
# (role, background role, minimum contrast ratio) — enforced by `derive`, verified by the tests for every theme
CONTRAST_RULES: tuple[tuple[str, str, float], ...] = (
    ("window_text", "window", TEXT), ("text", "base", TEXT), ("text", "alt_base", TEXT), ("dim_text", "base", TEXT),
    ("dim_text", "window", TEXT), ("button_text", "button", TEXT), ("accent_text", "accent", TEXT), ("link", "base", TEXT),
    ("tooltip_text", "tooltip", TEXT), ("placeholder", "base", SOFT), ("disabled_text", "window", SOFT),
    ("error", "base", TEXT), ("warning", "base", TEXT), ("success", "base", TEXT), ("info", "base", TEXT),
    ("text", "error_soft", TEXT), ("text", "warning_soft", TEXT), ("text", "success_soft", TEXT), ("text", "info_soft", TEXT),
    ("editor_fg", "editor_bg", TEXT), ("editor_fg", "current_line", TEXT), ("selection_fg", "selection", TEXT),
    ("gutter_fg", "gutter", SOFT), ("editor_fg", "error_line", TEXT),
    *((role, "editor_bg", SOFT if role in ("comment", "preset") else TEXT) for role in SYNTAX_ROLES),
    *((f"origin_{kind}_text", f"origin_{kind}", TEXT) for kind in ORIGIN_KINDS),
    ("canvas_text", "canvas_bg", TEXT), ("canvas_axis", "canvas_bg", DECORATION), ("canvas_accent", "canvas_bg", DECORATION),
    ("glyph_ink", "button", DECORATION), ("glyph_ink", "window", DECORATION), ("glyph_accent", "window", DECORATION),
)

# Which seed hue each syntax role takes unless a theme overrides it.
SYNTAX_HUES = {
    "keyword": "purple", "type": "yellow", "function": "blue", "builtin": "cyan", "string": "green", "comment": "comment",
    "number": "orange", "preprocessor": "red", "annotation": "orange", "preset": "comment", "special": "cyan", "api": "blue",
    "member": "yellow", "state": "orange", "constant": "orange", "decorator": "yellow", "definition": "blue", "meta": "green",
}
ORIGIN_HUES = {"builtin": "blue", "apophysis": "yellow", "jwildfire": "green", "user": "purple"}


# --- colour maths --------------------------------------------------------------------------------------------------
def parse(color: str) -> tuple[int, int, int]:
    """`#rrggbb` (or `rrggbb`) → (r, g, b)."""
    text = color.lstrip("#")
    if len(text) != 6:
        raise ValueError(f"not a #rrggbb colour: {color!r}")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def to_hex(rgb) -> str:
    """(r, g, b) → `#rrggbb` (channels rounded and clamped)."""
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def mix(a: str, b: str, t: float) -> str:
    """`a` blended towards `b` by `t` (0 = a, 1 = b)."""
    ca, cb = parse(a), parse(b)
    return to_hex(x + (y - x) * t for x, y in zip(ca, cb))


def relative_luminance(color: str) -> float:
    """WCAG relative luminance, 0 (black) … 1 (white)."""
    def linear(channel: int) -> float:
        c = channel / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (linear(c) for c in parse(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: str, b: str) -> float:
    """WCAG contrast ratio between two colours, 1 … 21."""
    la, lb = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def is_dark(color: str) -> bool:
    """Whether text on `color` should be light."""
    return relative_luminance(color) < 0.18


def ensure_contrast(color: str, background: str, minimum: float, towards: str | None = None) -> str:
    """`color` moved towards `towards` (default: white on dark backgrounds, black on light ones) just far enough to reach
    `minimum` contrast against `background`; unchanged when it already does."""
    if contrast_ratio(color, background) >= minimum:
        return color
    target = towards or (WHITE if is_dark(background) else BLACK)
    if contrast_ratio(target, background) < minimum:        # the preferred direction cannot get there: go to the extreme
        target = WHITE if contrast_ratio(WHITE, background) > contrast_ratio(BLACK, background) else BLACK
    lo, hi = 0.0, 1.0
    for _ in range(24):                                       # bisection: the smallest step that passes
        mid = (lo + hi) / 2
        if contrast_ratio(mix(color, target, mid), background) >= minimum:
            hi = mid
        else:
            lo = mid
    return mix(color, target, hi)


def best_text_on(background: str, *candidates: str) -> str:
    """The candidate with the highest contrast on `background` (black or white when none reaches 4.5:1)."""
    best = max(candidates, key=lambda c: contrast_ratio(c, background)) if candidates else BLACK
    if contrast_ratio(best, background) >= TEXT:
        return best
    return WHITE if contrast_ratio(WHITE, background) >= contrast_ratio(BLACK, background) else BLACK


# --- seeds and themes ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Seed:
    """A catalogue entry: the handful of colours a theme is defined by (see the module docstring)."""
    name: str
    family: str
    dark: bool
    bg: str
    surface: str
    base: str
    fg: str
    dim: str
    accent: str
    red: str
    orange: str
    yellow: str
    green: str
    cyan: str
    blue: str
    purple: str
    comment: str
    overrides: Mapping[str, str] = field(default_factory=dict)

    def hue(self, name: str) -> str:
        """One of the seed's named colours (`red` … `purple`, `comment`, `accent` …)."""
        return getattr(self, name)


@dataclass(frozen=True)
class Theme:
    """A complete theme: every role in `ROLES` has a `#rrggbb` colour.

    Attributes:
        name: Shown in the menus.
        family: For grouping (`Nord`, `Catppuccin`, `System` …).
        dark: Whether the UI is dark (light text on dark panels).
        colors: role → colour.
    """
    name: str
    family: str
    dark: bool
    colors: Mapping[str, str]

    def __getitem__(self, role: str) -> str:
        return self.colors[role]

    def contrast_failures(self) -> list[str]:
        """The `CONTRAST_RULES` this theme breaks (empty for every catalogue theme)."""
        return [f"{fg} on {bg}: {contrast_ratio(self[fg], self[bg]):.2f} < {minimum}"
                for fg, bg, minimum in CONTRAST_RULES if contrast_ratio(self[fg], self[bg]) < minimum - 1e-9]


def derive(seed: Seed) -> Theme:
    """Every role from the seed (see the module docstring), overrides applied, contrast rules enforced."""
    dark = seed.dark
    ink = WHITE if dark else BLACK
    c: dict[str, str] = {
        "window": seed.bg, "window_text": seed.fg, "base": seed.base, "alt_base": mix(seed.base, seed.fg, 0.045),
        "text": seed.fg, "dim_text": seed.dim, "button": seed.surface, "button_text": seed.fg,
        "border": mix(seed.bg, seed.fg, 0.22), "accent": seed.accent, "link": seed.blue,
        "tooltip": mix(seed.surface, seed.fg, 0.06) if dark else mix(seed.base, seed.fg, 0.04), "tooltip_text": seed.fg,
        "placeholder": mix(seed.fg, seed.base, 0.5), "disabled_text": mix(seed.fg, seed.bg, 0.5),
        "error": seed.red, "warning": seed.orange if not dark else seed.yellow, "success": seed.green, "info": seed.blue,
        "editor_bg": seed.base, "editor_fg": seed.fg, "gutter": mix(seed.base, seed.bg, 0.6),
        "gutter_fg": seed.comment, "current_line": mix(seed.base, seed.fg, 0.06 if dark else 0.045),
        "selection": mix(seed.base, seed.accent, 0.38 if dark else 0.28), "selection_fg": seed.fg,
        "error_line": mix(seed.base, seed.red, 0.22 if dark else 0.14), "match": mix(seed.base, seed.accent, 0.25),
        "glyph_ink": mix(seed.fg, seed.bg, 0.12), "glyph_accent": seed.accent,
    }
    for role in ("error", "warning", "success", "info"):
        c[f"{role}_soft"] = mix(seed.base, c[role], 0.2 if dark else 0.14)
    for role, hue in SYNTAX_HUES.items():
        c[role] = seed.hue(hue)
    for kind, hue in ORIGIN_HUES.items():
        colour = seed.hue(hue)
        c[f"origin_{kind}"] = mix(seed.base, colour, 0.2 if dark else 0.16)
        c[f"origin_{kind}_text"] = mix(colour, seed.fg, 0.3) if dark else mix(colour, BLACK, 0.35)
    canvas = mix(seed.bg, BLACK, 0.45) if dark else LIGHT_CANVAS
    c.update(canvas_bg=canvas, canvas_grid=mix(canvas, WHITE, 0.1), canvas_axis=mix(canvas, WHITE, 0.38),
             canvas_text=mix(canvas, WHITE, 0.7), canvas_accent=seed.accent)
    c.update(seed.overrides)
    if "accent_text" not in seed.overrides:
        c["accent_text"] = best_text_on(c["accent"], seed.bg, seed.fg, WHITE, BLACK)
    for fg, bg, minimum in CONTRAST_RULES:       # in order: a role is settled before anything is measured against it
        c[fg] = ensure_contrast(c[fg], c[bg], minimum, towards=None if fg.startswith(("origin_", "canvas_")) else _towards(c, bg, ink))
    return Theme(seed.name, seed.family, dark, {role: colour.lower() for role, colour in c.items()})


def _towards(colors: dict[str, str], background: str, ink: str) -> str:
    """Which way a failing colour moves: towards whichever of the text colour and pure black / white contrasts more."""
    text = colors["text"]
    return text if contrast_ratio(text, colors[background]) >= contrast_ratio(ink, colors[background]) else ink


__all__ = ["Seed", "Theme", "derive", "ROLES", "UI_ROLES", "STATUS_ROLES", "EDITOR_ROLES", "SYNTAX_ROLES", "ORIGIN_KINDS",
           "ORIGIN_ROLES", "CANVAS_ROLES", "GLYPH_ROLES", "CONTRAST_RULES", "parse", "to_hex", "mix", "relative_luminance",
           "contrast_ratio", "is_dark", "ensure_contrast", "best_text_on"]
