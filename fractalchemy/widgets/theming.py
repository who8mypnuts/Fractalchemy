"""Applying themes (`fractalchemy.themes`) to the running application.

    manager = theme_manager()
    manager.install(app, settings)     # main.py, before any window: the saved theme (System by default)
    manager.apply("Nord")              # View ▸ Theme: live, persisted
    colour = theme_color("keyword")    # a QColor of the current theme
    on_theme_changed(widget, widget.recolour)

**Catalogue themes** switch the application to Qt's *Fusion* style, the one style that honours a palette completely on
every platform, and install a `QPalette` built from the theme's roles (`palette_for`). **System** restores the style
and palette the application started with. It still has a full `Theme`, derived from the live palette (`system_theme`),
so editors, origin tints, canvases and glyphs are readable on a dark desktop too, and it follows the platform when it
switches between light and dark while the application runs.

A palette change repaints every palette-driven widget by itself. Whatever *caches* colours (syntax highlighters,
table items with explicit brushes, style sheets, HTML) subscribes with `on_theme_changed` and recolours itself, at once
when it is visible, else when it is next shown (so trying themes never makes hidden windows repopulate their lists).
Painted icons follow through `icons.set_glyph_inks`.
"""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QEvent, QObject, QSettings, Signal, Slot
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory, QWidget

from ..themes import catalog
from ..themes.model import Seed, Theme, derive, is_dark, mix
from . import icons

THEME_KEY = "appearance/theme"
FUSION = "Fusion"
Role = QPalette.ColorRole
Group = QPalette.ColorGroup


class ThemeManager(QObject):
    """The application's current theme (one per application; see `theme_manager()`).

    Signals:
        theme_changed(Theme): A theme was applied (also when the platform switched light / dark under System).
    """
    theme_changed = Signal(object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._name = catalog.SYSTEM
        self._theme: Theme | None = None
        self._system_style: str | None = None      # what the application started with (restored by System)
        self._system_palette: QPalette | None = None
        self._settings: QSettings | None = None

    # --- state ----------------------------------------------------------------------------------------------------
    @property
    def name(self) -> str:
        """The name of the applied theme (`System` until another is applied)."""
        return self._name

    def current(self) -> Theme:
        """The applied theme (for System: derived from the application's palette)."""
        if self._theme is None:
            self._settle(system_theme(QApplication.palette()))
        return self._theme

    # --- applying -------------------------------------------------------------------------------------------------
    def install(self, app: QApplication, settings: QSettings | None = None) -> None:
        """Remember the platform look, then apply the saved theme (main.py calls this before building windows)."""
        self._settings = settings
        self._capture_system(app)
        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda _scheme: self._platform_changed())
        name = str(settings.value(THEME_KEY, catalog.DEFAULT_THEME)) if settings is not None else catalog.DEFAULT_THEME
        self.apply(name, persist=False)

    def apply(self, name: str, persist: bool = True) -> Theme:
        """Switch the whole application to theme `name` (unknown names mean System); returns the theme."""
        app = QApplication.instance()
        if name not in catalog.THEMES:
            name = catalog.DEFAULT_THEME
        self._capture_system(app)
        if name == catalog.SYSTEM:
            if app is not None and self._system_style is not None and app.style().name().lower() != self._system_style.lower():
                app.setStyle(QStyleFactory.create(self._system_style))
            if app is not None and self._system_palette is not None:
                app.setPalette(self._system_palette)
            theme = system_theme(app.palette() if app is not None else QPalette())
        else:
            theme = catalog.theme(name)
            if app is not None:
                if app.style().name().lower() != FUSION.lower():
                    app.setStyle(QStyleFactory.create(FUSION))
                app.setPalette(palette_for(theme))
        self._name = name
        self._settle(theme)
        if persist and self._settings is not None:
            self._settings.setValue(THEME_KEY, name)
        self.theme_changed.emit(theme)
        return theme

    def _capture_system(self, app: QApplication | None) -> None:
        if app is not None and self._system_style is None:
            self._system_style = app.style().name()
            self._system_palette = QPalette(app.palette())

    def _platform_changed(self) -> None:
        """The platform switched light / dark: under System, take its new palette and re-derive."""
        if self._name != catalog.SYSTEM:
            return
        app = QApplication.instance()
        self._system_palette = QPalette(app.palette()) if app is not None else None
        theme = system_theme(app.palette() if app is not None else QPalette())
        self._settle(theme)
        self.theme_changed.emit(theme)

    def _settle(self, theme: Theme) -> None:
        self._theme = theme
        icons.set_glyph_inks(theme["glyph_ink"], theme["glyph_accent"])


_manager: ThemeManager | None = None


def theme_manager() -> ThemeManager:
    """The application's theme manager (created on first use)."""
    global _manager
    if _manager is None:
        _manager = ThemeManager()
    return _manager


def current_theme() -> Theme:
    """The applied theme."""
    return theme_manager().current()


def theme_color(role: str) -> QColor:
    """The current theme's colour for `role` (see `themes.model.ROLES`)."""
    return QColor(current_theme()[role])


class _ThemeListener(QObject):
    """Relays `theme_changed` to a callback; a child of the widget it serves, so Qt drops the connection with it.

    With `lazy`, a theme change that finds the owner hidden is remembered and delivered once, when the owner is next
    shown: a hidden window does not repopulate its tables for every theme the user tries.
    """

    def __init__(self, owner: QObject, callback: Callable[[Theme], None], lazy: bool):
        super().__init__(owner)
        self._owner = owner
        self._callback = callback
        self._lazy = lazy and isinstance(owner, QWidget)
        self._pending: Theme | None = None
        if self._lazy:
            owner.installEventFilter(self)

    @Slot(object)
    def notify(self, theme: Theme) -> None:
        if self._lazy and not self._owner.isVisible():
            self._pending = theme
        else:
            self._pending = None
            self._callback(theme)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Show and self._pending is not None:
            theme, self._pending = self._pending, None
            self._callback(theme)
        return False


def on_theme_changed(owner: QObject, callback: Callable[[Theme], None], lazy: bool = True) -> None:
    """Call `callback(theme)` after every theme change, for as long as `owner` lives. With `lazy` (the default) a hidden
    owner is recoloured when it is next shown instead of at once."""
    theme_manager().theme_changed.connect(_ThemeListener(owner, callback, lazy).notify)


def set_themed_style(widget: QWidget, template: str) -> None:
    """Give `widget` a style sheet whose `{role}` fields are the current theme's colours (CSS braces doubled: `{{ }}`),
    and re-apply it after every theme change. Calling it again replaces the template (an empty one clears the sheet)."""
    first = not hasattr(widget, "_themed_style")
    widget._themed_style = template
    if first:
        on_theme_changed(widget, lambda theme: widget.setStyleSheet(widget._themed_style.format_map(theme.colors)))
    widget.setStyleSheet(template.format_map(current_theme().colors))


def colored_html(text: str, role: str) -> str:
    """`text` (HTML) in the current theme's `role` colour, for rich-text labels (`colored_html(message, "error")`)."""
    return f'<span style="color:{current_theme()[role]}">{text}</span>'


# --- Qt ↔ theme ------------------------------------------------------------------------------------------------------
def palette_for(theme: Theme) -> QPalette:
    """A `QPalette` carrying the theme's UI roles (all colour groups, Fusion's bevel shades included)."""
    palette = QPalette()
    button = theme["button"]
    shades = {Role.Light: mix(button, "#ffffff", 0.25), Role.Midlight: mix(button, "#ffffff", 0.12),
              Role.Mid: mix(button, theme["border"], 0.6), Role.Dark: mix(button, "#000000", 0.35),
              Role.Shadow: mix(button, "#000000", 0.6)}
    normal = {Role.Window: theme["window"], Role.WindowText: theme["window_text"], Role.Base: theme["base"],
              Role.AlternateBase: theme["alt_base"], Role.Text: theme["text"], Role.Button: button,
              Role.ButtonText: theme["button_text"], Role.BrightText: theme["error"], Role.Highlight: theme["accent"],
              Role.HighlightedText: theme["accent_text"], Role.ToolTipBase: theme["tooltip"],
              Role.ToolTipText: theme["tooltip_text"], Role.PlaceholderText: theme["placeholder"], Role.Link: theme["link"],
              Role.LinkVisited: theme["link"], Role.Accent: theme["accent"], **shades}
    disabled = dict(normal)
    disabled.update({Role.WindowText: theme["disabled_text"], Role.Text: theme["disabled_text"],
                     Role.ButtonText: theme["disabled_text"], Role.Highlight: mix(theme["accent"], theme["window"], 0.55),
                     Role.HighlightedText: theme["disabled_text"]})
    for group, roles in ((Group.Active, normal), (Group.Inactive, normal), (Group.Disabled, disabled)):
        for role, colour in roles.items():
            palette.setColor(group, role, QColor(colour))
    return palette


def system_theme(palette: QPalette) -> Theme:
    """The System theme: the palette's own colours, with Fractalchemy's light or dark syntax hues on top."""
    def c(role: Role) -> str:
        return palette.color(Group.Active, role).name()
    base, text = c(Role.Base), c(Role.Text)
    dark = is_dark(base)
    hues = catalog.SYSTEM_DARK if dark else catalog.SYSTEM_LIGHT
    seed = Seed(catalog.SYSTEM, catalog.SYSTEM, dark, bg=c(Role.Window), surface=c(Role.Button), base=base, fg=text,
                dim=mix(text, base, 0.3), accent=c(Role.Highlight), red=hues.red, orange=hues.orange, yellow=hues.yellow,
                green=hues.green, cyan=hues.cyan, blue=hues.blue, purple=hues.purple, comment=hues.comment,
                overrides={**hues.overrides, "accent_text": c(Role.HighlightedText)})
    return derive(seed)


__all__ = ["ThemeManager", "theme_manager", "current_theme", "theme_color", "on_theme_changed", "set_themed_style", "colored_html", "palette_for",
           "system_theme",
           "THEME_KEY"]
