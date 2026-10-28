"""Application settings helpers: the QSettings identity."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication

from . import config


def configure_application(app: QCoreApplication) -> None:
    """Give `app` the organisation / application names that default QSettings use."""
    app.setOrganizationName(config.APP_NAME)
    app.setApplicationName(config.APP_NAME)
