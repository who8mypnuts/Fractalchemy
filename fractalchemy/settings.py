"""Application settings helpers: the QSettings identity and the one-time HueClid migration."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication, QSettings

from . import config
from .library.roots import KEY as LIBRARY_ROOTS_KEY

MIGRATED_KEYS = (LIBRARY_ROOTS_KEY,)


def configure_application(app: QCoreApplication) -> None:
    """Give `app` the organisation / application names that default QSettings use."""
    app.setOrganizationName(config.APP_NAME)
    app.setApplicationName(config.APP_NAME)


def migrate_legacy_settings(old: QSettings | None = None, new: QSettings | None = None) -> list[str]:
    """Copy settings saved by HueClid into the Fractalchemy store, once.

    Only keys that are missing from `new` are copied, so nothing the user has
    set since the rename is overwritten. The legacy store is left untouched.

    Args:
        old: The HueClid settings; defaults to the real ones.
        new: The Fractalchemy settings; defaults to the application's.

    Returns:
        The keys that were copied.
    """
    old = old if old is not None else QSettings(config.LEGACY_APP_NAME, config.LEGACY_APP_NAME)
    new = new if new is not None else QSettings()
    copied = [key for key in MIGRATED_KEYS if old.contains(key) and not new.contains(key)]
    for key in copied:
        new.setValue(key, old.value(key))
    if copied:
        new.sync()
    return copied
