"""The theme catalogue: *System* (the platform's own look), the Nord family (`nord.py`) and thirty-one others.

Each entry is a `Seed` built from the theme's published palette (see `model.py` for what the fields mean); `theme(name)`
derives the full `Theme`. Mostly dark themes, with a few light ones. The order of `THEMES` is the menu order within
each group.

*System* is not a fixed palette: it keeps the platform's style and colours, and its editor / origin / canvas colours are
derived at run time from the live palette (light or dark, chosen by the base colour). The Qt side
(`widgets/theming.py`) builds that seed; `SYSTEM_LIGHT` / `SYSTEM_DARK` provide its syntax hues.
"""

from __future__ import annotations

from functools import lru_cache

from . import nord
from .model import Seed, Theme, derive

SYSTEM = "System"
DEFAULT_THEME = SYSTEM
DARK, LIGHT = "Dark", "Light"


def _seed(name: str, family: str, dark: bool, bg: str, surface: str, base: str, fg: str, dim: str, accent: str, red: str,
          orange: str, yellow: str, green: str, cyan: str, blue: str, purple: str, comment: str, **overrides: str) -> Seed:
    """A catalogue entry in one line: the fourteen seed colours in their fixed order, then role overrides."""
    return Seed(name, family, dark, bg=bg, surface=surface, base=base, fg=fg, dim=dim, accent=accent, red=red, orange=orange,
                yellow=yellow, green=green, cyan=cyan, blue=blue, purple=purple, comment=comment, overrides=overrides)


# Fractalchemy's own pair; the light one carries the application's historical syntax colours exactly.
FRACTALCHEMY_DARK = _seed("Fractalchemy Dark", "Fractalchemy", True, "#202225", "#2B2D31", "#18191B", "#E3E5E8", "#A6ABB3",
                          "#1E88E5", "#EF5350", "#FFA552", "#E5C07B", "#81C784", "#4DD0E1", "#64B5F6", "#CE93D8", "#8A8F98",
                          keyword="#C792EA", type="#64B5F6", api="#82AAFF", member="#E5C07B", function="#8FB4F0")
FRACTALCHEMY_LIGHT = _seed("Fractalchemy Light", "Fractalchemy", False, "#F3F4F6", "#E8EAED", "#FFFFFF", "#1F2328", "#57606A",
                           "#1E88E5", "#C62828", "#C45200", "#8D5A00", "#2E7D32", "#00838F", "#1565C0", "#7B2FA0", "#8A8A8A",
                           keyword="#7B2FA0", type="#1565C0", api="#0D47A1", function="#3B5F9E", builtin="#1565C0",
                           member="#8D5A00", state="#8D5A00", string="#2E7D32", number="#C45200", preprocessor="#4A7A48",
                           constant="#7A3A3A", annotation="#B5541C", special="#0D47A1", decorator="#7B2FA0",
                           definition="#1565C0", meta="#4A7A48", preset="#9A9A9A")
SYSTEM_LIGHT, SYSTEM_DARK = FRACTALCHEMY_LIGHT, FRACTALCHEMY_DARK

DARK_SEEDS = (
    FRACTALCHEMY_DARK,
    _seed("Dracula", "Dracula", True, "#21222C", "#343746", "#282A36", "#F8F8F2", "#C5C8D6", "#BD93F9", "#FF5555", "#FFB86C",
          "#F1FA8C", "#50FA7B", "#8BE9FD", "#8BE9FD", "#BD93F9", "#6272A4",
          keyword="#FF79C6", function="#50FA7B", type="#8BE9FD", string="#F1FA8C", number="#BD93F9", preprocessor="#FF79C6"),
    _seed("Monokai", "Monokai", True, "#1E1F1C", "#3E3D32", "#272822", "#F8F8F2", "#CFCFC2", "#66D9EF", "#F92672", "#FD971F",
          "#E6DB74", "#A6E22E", "#66D9EF", "#66D9EF", "#AE81FF", "#75715E",
          keyword="#F92672", function="#A6E22E", type="#66D9EF", string="#E6DB74", number="#AE81FF", preprocessor="#F92672"),
    _seed("One Dark", "One", True, "#21252B", "#2C313A", "#282C34", "#ABB2BF", "#9DA5B4", "#61AFEF", "#E06C75", "#D19A66",
          "#E5C07B", "#98C379", "#56B6C2", "#61AFEF", "#C678DD", "#5C6370"),
    _seed("Tokyo Night", "Tokyo Night", True, "#16161E", "#1F2335", "#1A1B26", "#C0CAF5", "#A9B1D6", "#7AA2F7", "#F7768E",
          "#FF9E64", "#E0AF68", "#9ECE6A", "#7DCFFF", "#7AA2F7", "#BB9AF7", "#565F89", type="#2AC3DE"),
    _seed("Tokyo Night Storm", "Tokyo Night", True, "#1F2335", "#292E42", "#24283B", "#C0CAF5", "#A9B1D6", "#7AA2F7", "#F7768E",
          "#FF9E64", "#E0AF68", "#9ECE6A", "#7DCFFF", "#7AA2F7", "#BB9AF7", "#565F89", type="#2AC3DE"),
    _seed("Catppuccin Mocha", "Catppuccin", True, "#181825", "#313244", "#1E1E2E", "#CDD6F4", "#A6ADC8", "#89B4FA", "#F38BA8",
          "#FAB387", "#F9E2AF", "#A6E3A1", "#94E2D5", "#89B4FA", "#CBA6F7", "#7F849C"),
    _seed("Catppuccin Macchiato", "Catppuccin", True, "#1E2030", "#363A4F", "#24273A", "#CAD3F5", "#A5ADCB", "#8AADF4",
          "#ED8796", "#F5A97F", "#EED49F", "#A6DA95", "#8BD5CA", "#8AADF4", "#C6A0F6", "#8087A2"),
    _seed("Catppuccin Frappé", "Catppuccin", True, "#292C3C", "#414559", "#303446", "#C6D0F5", "#A5ADCE", "#8CAAEE", "#E78284",
          "#EF9F76", "#E5C890", "#A6D189", "#81C8BE", "#8CAAEE", "#CA9EE6", "#838BA7"),
    _seed("Gruvbox Dark", "Gruvbox", True, "#282828", "#3C3836", "#1D2021", "#EBDBB2", "#BDAE93", "#83A598", "#FB4934", "#FE8019",
          "#FABD2F", "#B8BB26", "#8EC07C", "#83A598", "#D3869B", "#928374",
          keyword="#FB4934", function="#8EC07C", number="#D3869B", preprocessor="#8EC07C"),
    _seed("Solarized Dark", "Solarized", True, "#073642", "#0A4150", "#002B36", "#93A1A1", "#839496", "#268BD2", "#DC322F",
          "#CB4B16", "#B58900", "#859900", "#2AA198", "#268BD2", "#6C71C4", "#586E75",
          keyword="#859900", type="#B58900", string="#2AA198", number="#D33682", preprocessor="#CB4B16", special="#6C71C4"),
    _seed("Ayu Mirage", "Ayu", True, "#1C212B", "#242936", "#1F2430", "#CBCCC6", "#A2A49F", "#FFCC66", "#F28779", "#FFA759",
          "#FFD580", "#BAE67E", "#95E6CB", "#73D0FF", "#D4BFFF", "#5C6773",
          keyword="#FFA759", function="#FFD580", type="#73D0FF", number="#D4BFFF"),
    _seed("Everforest Dark", "Everforest", True, "#272E33", "#343F44", "#2D353B", "#D3C6AA", "#9DA9A0", "#A7C080", "#E67E80",
          "#E69875", "#DBBC7F", "#A7C080", "#83C092", "#7FBBB3", "#D699B6", "#859289",
          keyword="#E67E80", function="#A7C080", string="#83C092"),
    _seed("Kanagawa", "Kanagawa", True, "#16161D", "#2A2A37", "#1F1F28", "#DCD7BA", "#C8C093", "#7E9CD8", "#E46876", "#FFA066",
          "#E6C384", "#98BB6C", "#7AA89F", "#7E9CD8", "#957FB8", "#727169", type="#7AA89F", number="#D27E99"),
    _seed("Rosé Pine", "Rosé Pine", True, "#1F1D2E", "#26233A", "#191724", "#E0DEF4", "#908CAA", "#C4A7E7", "#EB6F92", "#F6C177",
          "#F6C177", "#9CCFD8", "#9CCFD8", "#31748F", "#C4A7E7", "#6E6A86",
          keyword="#31748F", function="#EBBCBA", string="#F6C177", type="#9CCFD8", number="#EBBCBA"),
    _seed("Material Palenight", "Material", True, "#202331", "#34324A", "#292D3E", "#A6ACCD", "#8F94B8", "#82AAFF", "#F07178",
          "#F78C6C", "#FFCB6B", "#C3E88D", "#89DDFF", "#82AAFF", "#C792EA", "#676E95"),
    _seed("Night Owl", "Night Owl", True, "#010E1A", "#0B2942", "#011627", "#D6DEEB", "#A1AAB8", "#82AAFF", "#EF5350", "#F78C6C",
          "#ECC48D", "#ADDB67", "#7FDBCA", "#82AAFF", "#C792EA", "#637777", string="#ECC48D", type="#FFCB8B"),
    _seed("Oceanic Next", "Oceanic", True, "#16232A", "#343D46", "#1B2B34", "#D8DEE9", "#A7ADBA", "#6699CC", "#EC5F67",
          "#F99157", "#FAC863", "#99C794", "#5FB3B3", "#6699CC", "#C594C5", "#65737E"),
    _seed("Tomorrow Night", "Tomorrow", True, "#282A2E", "#373B41", "#1D1F21", "#C5C8C6", "#B4B7B4", "#81A2BE", "#CC6666",
          "#DE935F", "#F0C674", "#B5BD68", "#8ABEB7", "#81A2BE", "#B294BB", "#969896"),
    _seed("GitHub Dark", "GitHub", True, "#010409", "#161B22", "#0D1117", "#E6EDF3", "#8B949E", "#2F81F7", "#FF7B72", "#FFA657",
          "#D29922", "#7EE787", "#79C0FF", "#79C0FF", "#D2A8FF", "#8B949E",
          keyword="#FF7B72", function="#D2A8FF", type="#FFA657", string="#A5D6FF", number="#79C0FF", builtin="#79C0FF"),
    _seed("Darcula", "JetBrains", True, "#3C3F41", "#4C5052", "#2B2B2B", "#A9B7C6", "#8C9BAA", "#4A88C7", "#FF6B68", "#CC7832",
          "#FFC66D", "#6A8759", "#299999", "#6897BB", "#9876AA", "#808080",
          keyword="#CC7832", type="#CC7832", function="#FFC66D", string="#6A8759", number="#6897BB", annotation="#BBB529",
          special="#9876AA", member="#9876AA"),
    _seed("Iceberg", "Iceberg", True, "#0F1117", "#1E2132", "#161821", "#C6C8D1", "#A0A3B1", "#84A0C6", "#E27878", "#E2A478",
          "#E2A478", "#B4BE82", "#89B8C2", "#84A0C6", "#A093C7", "#6B7089",
          keyword="#84A0C6", type="#B4BE82", function="#A093C7", string="#89B8C2", number="#A093C7"),
    _seed("High Contrast Dark", "High Contrast", True, "#000000", "#0C0C0C", "#000000", "#FFFFFF", "#E0E0E0", "#1AEBFF",
          "#F48771", "#FFA657", "#FFD700", "#89D185", "#1AEBFF", "#75BEFF", "#D9A2FF", "#7CA668",
          keyword="#569CD6", function="#DCDCAA", type="#4EC9B0", string="#CE9178", number="#B5CEA8", accent_text="#000000"),
)

LIGHT_SEEDS = (
    FRACTALCHEMY_LIGHT,
    _seed("Solarized Light", "Solarized", False, "#EEE8D5", "#E4DDC8", "#FDF6E3", "#586E75", "#657B83", "#268BD2", "#DC322F",
          "#CB4B16", "#B58900", "#859900", "#2AA198", "#268BD2", "#6C71C4", "#93A1A1",
          keyword="#859900", type="#B58900", string="#2AA198", number="#D33682", preprocessor="#CB4B16", special="#6C71C4"),
    _seed("Gruvbox Light", "Gruvbox", False, "#EBDBB2", "#D5C4A1", "#FBF1C7", "#3C3836", "#504945", "#076678", "#9D0006",
          "#AF3A03", "#B57614", "#79740E", "#427B58", "#076678", "#8F3F71", "#928374",
          keyword="#9D0006", function="#427B58", number="#8F3F71", preprocessor="#427B58"),
    _seed("Catppuccin Latte", "Catppuccin", False, "#E6E9EF", "#CCD0DA", "#EFF1F5", "#4C4F69", "#5C5F77", "#1E66F5", "#D20F39",
          "#FE640B", "#DF8E1D", "#40A02B", "#179299", "#1E66F5", "#8839EF", "#8C8FA1"),
    _seed("One Light", "One", False, "#EAEAEB", "#DBDBDC", "#FAFAFA", "#383A42", "#696C77", "#4078F2", "#E45649", "#986801",
          "#C18401", "#50A14F", "#0184BC", "#4078F2", "#A626A4", "#A0A1A7"),
    _seed("Rosé Pine Dawn", "Rosé Pine", False, "#F2E9E1", "#FFFAF3", "#FAF4ED", "#575279", "#797593", "#907AA9", "#B4637A",
          "#EA9D34", "#EA9D34", "#56949F", "#56949F", "#286983", "#907AA9", "#9893A5",
          keyword="#286983", function="#D7827E", string="#EA9D34", type="#56949F", number="#D7827E"),
    _seed("GitHub Light", "GitHub", False, "#F6F8FA", "#EAEEF2", "#FFFFFF", "#1F2328", "#59636E", "#0969DA", "#CF222E", "#953800",
          "#9A6700", "#116329", "#1B7C83", "#0550AE", "#8250DF", "#6E7781",
          keyword="#CF222E", function="#8250DF", type="#953800", string="#0A3069", number="#0550AE"),
    _seed("Paper", "High Contrast", False, "#F2F2F2", "#E6E6E6", "#FFFFFF", "#000000", "#444444", "#0044CC", "#A00000", "#A33000",
          "#7A4100", "#006400", "#00606A", "#005A9C", "#000080", "#707070",
          keyword="#000080", function="#1A1A7A", type="#005A9C", string="#006400", number="#A33000", preprocessor="#2E5E2E",
          builtin="#7A4100", special="#00337A"),
)

NORD_SEEDS = nord.SEEDS
SEEDS: dict[str, Seed] = {s.name: s for s in NORD_SEEDS + DARK_SEEDS + LIGHT_SEEDS}
THEMES: tuple[str, ...] = (SYSTEM, *SEEDS)


@lru_cache(maxsize=None)
def _derived(name: str) -> Theme:
    return derive(SEEDS[name])


def theme(name: str) -> Theme:
    """The catalogue theme called `name` (Fractalchemy Light for System or an unknown name — the Qt side derives the real
    System theme from the live palette)."""
    return _derived(name if name in SEEDS else FRACTALCHEMY_LIGHT.name)


def theme_names() -> list[str]:
    """Every theme name, System first."""
    return list(THEMES)


def groups() -> list[tuple[str, list[str]]]:
    """The menu structure: ("Nord", [...]), ("Dark", [...]), ("Light", [...]) (System stands alone before them)."""
    return [(nord.FAMILY, [s.name for s in NORD_SEEDS]), (DARK, [s.name for s in DARK_SEEDS]),
            (LIGHT, [s.name for s in LIGHT_SEEDS])]


def is_dark(name: str) -> bool | None:
    """Whether a catalogue theme is dark (None for System and unknown names)."""
    seed = SEEDS.get(name)
    return None if seed is None else seed.dark


__all__ = ["SYSTEM", "DEFAULT_THEME", "SEEDS", "THEMES", "theme", "theme_names", "groups", "is_dark", "SYSTEM_LIGHT",
           "SYSTEM_DARK", "FRACTALCHEMY_LIGHT", "FRACTALCHEMY_DARK"]
