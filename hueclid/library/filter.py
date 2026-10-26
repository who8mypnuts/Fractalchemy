"""Case-insensitive search over file names *and* the gradient names inside files."""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt

from .model import SEARCH_ROLE


class LibraryFilter(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterRole(SEARCH_ROLE)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setRecursiveFilteringEnabled(True)  # keep ancestors of matching rows
        self._terms: list[str] = []

    def set_query(self, text: str) -> None:
        if hasattr(self, "beginFilterChange"):  # Qt >= 6.10
            self.beginFilterChange()
            self._terms = text.casefold().split()
            self.endFilterChange()
        else:
            self._terms = text.casefold().split()
            self.invalidateFilter()

    @property
    def active(self) -> bool:
        return bool(self._terms)

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._terms:
            return True
        index = self.sourceModel().index(source_row, 0, source_parent)
        haystack = (index.data(SEARCH_ROLE) or "").casefold()
        return all(term in haystack for term in self._terms)
