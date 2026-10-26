"""Case-insensitive search over file names *and* the gradient names inside files."""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt

from .model import SEARCH_ROLE


class LibraryFilter(QSortFilterProxyModel):
    """Proxy that hides rows not matching every search term (ancestors of matches stay)."""
    def __init__(self, parent=None):
        """Configure recursive, case-insensitive filtering on SEARCH_ROLE."""
        super().__init__(parent)
        self.setFilterRole(SEARCH_ROLE)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setRecursiveFilteringEnabled(True)  # keep ancestors of matching rows
        self._terms: list[str] = []

    def set_query(self, text: str) -> None:
        """Set the search text; words are matched independently as substrings."""
        if hasattr(self, "beginFilterChange"):  # Qt >= 6.10
            self.beginFilterChange()
            self._terms = text.casefold().split()
            self.endFilterChange()
        else:
            self._terms = text.casefold().split()
            self.invalidateFilter()

    @property
    def active(self) -> bool:
        """True while a non-empty query is applied."""
        return bool(self._terms)

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._terms:
            return True
        index = self.sourceModel().index(source_row, 0, source_parent)
        haystack = (index.data(SEARCH_ROLE) or "").casefold()
        return all(term in haystack for term in self._terms)
