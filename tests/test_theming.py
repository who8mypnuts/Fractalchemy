"""Applying themes to the running application: palette and style, persistence, the menu, live recolouring of the
editors, tables, style sheets and icons, and the readability fix of the Transform Editor's tinted rows."""

import pytest
from PySide6.QtCore import QSettings, QSize
from PySide6.QtGui import QColor, QIcon, QPalette
from PySide6.QtWidgets import QApplication, QLabel

from fractalchemy.themes import catalog
from fractalchemy.themes.model import contrast_ratio
from fractalchemy.widgets.theming import (THEME_KEY, colored_html, current_theme, on_theme_changed, palette_for, set_themed_style,
                                          system_theme, theme_color, theme_manager)


@pytest.fixture
def themes(qapp):
    """The theme manager; the application goes back to System afterwards, so other tests see the usual look."""
    manager = theme_manager()
    yield manager
    manager.apply(catalog.SYSTEM, persist=False)


def base_color(widget=None) -> str:
    palette = widget.palette() if widget is not None else QApplication.palette()
    return palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Base).name()


def test_applying_a_theme_sets_fusion_and_the_palette_and_system_restores(themes):
    original_style, original_base = QApplication.style().name(), base_color()
    seen, owner = [], QLabel()
    owner.show()
    on_theme_changed(owner, seen.append)
    theme = themes.apply("Nord", persist=False)
    assert QApplication.style().name().lower() == "fusion" and base_color() == theme["base"]
    assert QApplication.palette().color(QPalette.ColorRole.Highlight).name() == theme["accent"]
    assert themes.name == "Nord" and current_theme() is theme and seen and seen[-1] is theme
    themes.apply(catalog.SYSTEM, persist=False)
    assert QApplication.style().name() == original_style and base_color() == original_base
    assert themes.name == catalog.SYSTEM and current_theme().name == catalog.SYSTEM
    import shiboken6
    shiboken6.delete(owner)                                               # the listener goes with its owner
    themes.apply("Nord", persist=False)
    assert len(seen) == 2


def test_the_choice_persists_and_unknown_names_mean_system(themes, tmp_path):
    settings = QSettings(str(tmp_path / "t.ini"), QSettings.Format.IniFormat)
    themes._settings = settings
    themes.apply("Dracula")
    assert settings.value(THEME_KEY) == "Dracula"
    settings.setValue(THEME_KEY, "Gruvbox Dark")
    themes.install(QApplication.instance(), settings)
    assert themes.name == "Gruvbox Dark" and base_color() == catalog.theme("Gruvbox Dark")["base"]
    assert themes.apply("no such theme", persist=False).name == catalog.SYSTEM
    themes._settings = None


def test_palette_for_fills_every_group_and_dims_disabled_text():
    theme = catalog.theme("Tokyo Night")
    palette = palette_for(theme)
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        assert palette.color(group, QPalette.ColorRole.Text).name() == theme["text"]
    assert palette.color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text).name() == theme["disabled_text"]
    assert palette.color(QPalette.ColorRole.PlaceholderText).name() == theme["placeholder"]


def test_system_theme_picks_dark_editor_colours_on_a_dark_palette():
    dark = palette_for(catalog.theme("Fractalchemy Dark"))
    theme = system_theme(dark)
    assert theme.dark and theme["keyword"] != catalog.theme("Fractalchemy Light")["keyword"]
    assert theme.contrast_failures() == []
    assert not system_theme(palette_for(catalog.theme("Paper"))).dark


def test_the_theme_menu_lists_every_theme_and_applies_it(themes):
    from fractalchemy.widgets.theme_menu import ThemeMenu
    menu = ThemeMenu()
    assert set(menu.actions_by_name) == set(catalog.theme_names()) and menu.actions_by_name[catalog.SYSTEM].isChecked()
    menu.actions_by_name["Catppuccin Mocha"].trigger()
    assert themes.name == "Catppuccin Mocha" and menu.group.checkedAction().text() == "Catppuccin Mocha"
    themes.apply("Nord", persist=False)                                    # chosen elsewhere: the menu follows
    assert menu.actions_by_name["Nord"].isChecked()


def test_code_editors_recolour_with_the_theme_unless_pinned(themes):
    from fractalchemy.ui.fragments.code_editor import GlslCodeEditor
    from fractalchemy.widgets.code_editor import CodeEditor
    from fractalchemy.widgets.formula_code_editor import FormulaCodeEditor
    editors = [CodeEditor(), FormulaCodeEditor(), GlslCodeEditor()]
    pinned = GlslCodeEditor()
    pinned.set_theme("Monokai")
    for editor in editors + [pinned]:
        editor.show()                                                       # hidden editors recolour when shown
    for name in ("Nord", "Nord Snow Storm"):
        theme = themes.apply(name, persist=False)
        for editor in editors:
            assert editor.highlighter.format_color("keyword").name() == theme["keyword"]
            assert base_color(editor) == theme["editor_bg"]
        assert pinned.theme_name == "Monokai" and base_color(pinned) == "#272822"
    pinned.set_theme("Default")                                            # the old preference value: follow again
    assert pinned.theme_name == "Follow application theme" and base_color(pinned) == current_theme()["editor_bg"]


def test_value_table_rows_use_their_text_colour_in_every_column(qapp):
    """The Transform Editor bug: tinted rows coloured only the name, leaving light weight text on a pale tint."""
    from fractalchemy.widgets.value_table import ValueRow, ValueTable
    table = ValueTable(None, ("Variation", "Weight", "Kind"))
    text, tint = QColor("#123f73"), QColor("#e3effb")
    table.set_rows([ValueRow("linear", 0.5, "3D", color=text, background=tint)])
    for column in range(3):
        assert table.item(0, column).foreground().color() == text and table.item(0, column).background().color() == tint


def test_transform_editor_variation_rows_are_readable_in_dark_and_light_themes(themes, main_window_factory, samples):
    win = main_window_factory()
    from fractalchemy.fractal.formats import load_flame
    win.show_flame(load_flame(samples / "sample flames" / "candy.flame", 0))
    win.show_editor()
    table = win.editor.variations_tab.table
    for name in ("Dracula", "Nord", "Solarized Light"):
        themes.apply(name, persist=False)
        for row in range(0, table.rowCount(), 97):
            for column in range(table.columnCount()):
                item = table.item(row, column)
                assert contrast_ratio(item.foreground().color().name(), item.background().color().name()) >= 4.5, (name, row, column)


def test_hidden_widgets_recolour_when_shown(themes):
    label = QLabel()
    calls = []
    on_theme_changed(label, calls.append)
    themes.apply("Nord", persist=False)
    themes.apply("Dracula", persist=False)
    assert calls == []                                                       # hidden: nothing done yet
    label.show()
    assert [t.name for t in calls] == ["Dracula"]                            # once, with the latest theme
    themes.apply("Nord", persist=False)
    assert [t.name for t in calls] == ["Dracula", "Nord"]                    # visible: at once


def test_themed_style_sheets_and_rich_text_follow_the_theme(themes):
    label = QLabel()
    label.show()
    set_themed_style(label, "QLabel {{ color: {error}; }}")
    themes.apply("Nord", persist=False)
    assert catalog.theme("Nord")["error"] in label.styleSheet()
    themes.apply("GitHub Light", persist=False)
    assert catalog.theme("GitHub Light")["error"] in label.styleSheet()
    set_themed_style(label, "")
    assert label.styleSheet() == ""
    assert catalog.theme("GitHub Light")["error"] in colored_html("oops", "error")


def test_painted_icons_take_the_theme_ink(themes):
    from fractalchemy.widgets.icons import editor_icon

    def ink(icon: QIcon) -> str:
        image = icon.pixmap(QSize(24, 24)).toImage()
        opaque = [image.pixelColor(x, y) for x in range(24) for y in range(24) if image.pixelColor(x, y).alpha() == 255]
        return max(opaque, key=lambda c: sum(1 for o in opaque if o == c)).name()
    icon = editor_icon("move")
    themes.apply("Nord", persist=False)
    on_dark = ink(icon)
    themes.apply("Nord Snow Storm", persist=False)
    on_light = ink(icon)
    assert on_dark == catalog.theme("Nord")["glyph_ink"] and on_light == catalog.theme("Nord Snow Storm")["glyph_ink"]
    assert QColor(on_dark).lightness() > QColor(on_light).lightness()


def test_canvas_colours_come_from_the_theme(themes):
    themes.apply("Nord Deep", persist=False)
    assert theme_color("canvas_bg").name() == catalog.theme("Nord Deep")["canvas_bg"]
