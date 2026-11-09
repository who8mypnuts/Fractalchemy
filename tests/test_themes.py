"""The theme catalogue and its rules (Qt-free): completeness, the Nord family, and readability for every theme."""

import re

import pytest

from fractalchemy.fragments import editor_themes
from fractalchemy.themes import catalog, nord
from fractalchemy.themes.model import CONTRAST_RULES, ROLES, contrast_ratio, ensure_contrast

HEX = re.compile(r"^#[0-9a-f]{6}$")


def test_the_catalogue_has_nord_variations_and_about_thirty_others_mostly_dark():
    names = catalog.theme_names()
    assert names[0] == catalog.SYSTEM == catalog.DEFAULT_THEME
    assert len(names) == len(set(names)) >= 38
    nord_names = [s.name for s in nord.SEEDS]
    assert nord_names[0] == "Nord" and len(nord_names) >= 7                 # Nord and at least six variations
    others = [n for n in catalog.SEEDS if n not in nord_names]
    assert len(others) >= 30
    dark = [n for n in catalog.SEEDS if catalog.is_dark(n)]
    light = [n for n in catalog.SEEDS if not catalog.is_dark(n)]
    assert len(dark) > 2 * len(light) and len(light) >= 8                   # favour dark, a few light
    assert [title for title, _ in catalog.groups()] == ["Nord", "Dark", "Light"]
    assert sum(len(group) for _, group in catalog.groups()) == len(catalog.SEEDS)


def test_nord_uses_the_canonical_palette():
    assert nord.NORD["nord0"] == "#2E3440" and nord.NORD["nord8"] == "#88C0D0" and nord.NORD["nord15"] == "#B48EAD"
    theme = catalog.theme("Nord")
    assert theme["window"] == "#2e3440" and theme["accent"] == "#88c0d0" and theme["keyword"] == "#81a1c1"
    assert catalog.theme("Nord Snow Storm").dark is False and catalog.theme("Nord Snow Storm")["text"] == "#2e3440"


@pytest.mark.parametrize("name", list(catalog.SEEDS))
def test_every_theme_is_complete_and_readable(name):
    theme = catalog.theme(name)
    assert set(theme.colors) >= set(ROLES)
    assert all(HEX.match(colour) for colour in theme.colors.values())
    assert theme.contrast_failures() == []                                  # WCAG AA text, 3:1 comments / hints / glyphs
    assert contrast_ratio(theme["canvas_bg"], "#000000") < 3                 # canvases are dark on every theme


def test_every_contrast_rule_names_real_roles():
    for fg, bg, minimum in CONTRAST_RULES:
        assert fg in ROLES and bg in ROLES and minimum >= 3.0


def test_published_colours_are_kept_when_readable_and_lifted_when_not():
    assert catalog.theme("Dracula")["keyword"] == "#ff79c6"                 # already readable: untouched
    nord_comment = catalog.theme("Nord")["comment"]
    assert nord_comment != "#616e88" and contrast_ratio(nord_comment, catalog.theme("Nord")["editor_bg"]) >= 3.0
    lifted = ensure_contrast("#4c566a", "#2e3440", 4.5)
    assert contrast_ratio(lifted, "#2e3440") >= 4.5 and ensure_contrast("#ffffff", "#000000", 4.5) == "#ffffff"


def test_unknown_names_fall_back_and_system_has_a_light_fallback():
    assert catalog.theme("no such theme") == catalog.theme(catalog.SYSTEM) == catalog.theme("Fractalchemy Light")
    assert catalog.is_dark(catalog.SYSTEM) is None


def test_fractalchemy_light_keeps_the_historical_editor_colours():
    theme = catalog.theme("Fractalchemy Light")
    assert (theme["keyword"], theme["type"], theme["api"], theme["string"]) == ("#7b2fa0", "#1565c0", "#0d47a1", "#2e7d32")


def test_fragment_editor_themes_follow_the_application_by_default_and_map_old_names():
    assert editor_themes.DEFAULT_THEME == editor_themes.FOLLOW == editor_themes.theme_names()[0]
    assert editor_themes.canonical("Default") == editor_themes.FOLLOW and editor_themes.pinned("Default") is None
    assert editor_themes.canonical("Dark") == "Fractalchemy Dark" and editor_themes.canonical("Solarized light") == "Solarized Light"
    assert editor_themes.pinned("Monokai") == "Monokai" and editor_themes.canonical("bogus") == editor_themes.FOLLOW
    assert editor_themes.theme("Monokai")["background"] == "#272822"
