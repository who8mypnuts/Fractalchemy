"""The report's document model: sections of labelled items and tables, with machine and human values.

Every `Item` (and every table cell) keeps a machine `value` next to a human `display`, so the text
writer can emit `key<TAB>value` records and the Markdown / HTML writers readable prose from the
same facts — the formats can differ in presentation, never in numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime


def machine_text(value: object) -> str:
    """Pipeline-friendly rendering of a value: numbers unadorned, booleans lower-case, lists comma-joined."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        return f"{value + 0.0:.10g}"          # + 0.0 turns −0.0 into 0.0
    if isinstance(value, (list, tuple)):
        return ", ".join(machine_text(v) for v in value)
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if value is None:
        return ""
    return str(value)


@dataclass(frozen=True)
class Cell:
    """One table cell: machine value plus its human rendering."""
    value: object
    display: str

    @classmethod
    def of(cls, raw: object) -> "Cell":
        """Normalise a plain value, a (value, display) pair or a Cell into a Cell."""
        if isinstance(raw, Cell):
            return raw
        if isinstance(raw, tuple) and len(raw) == 2 and isinstance(raw[1], str):
            return cls(raw[0], raw[1])
        return cls(raw, machine_text(raw))


@dataclass
class Item:
    """One labelled fact.

    Attributes:
        key: Machine name (no spaces).
        label: Human label.
        value: Machine value (number, bool, str, list).
        display: Human rendering; defaults to the machine value (booleans as yes / no).
    """
    key: str
    label: str
    value: object
    display: str | None = None

    @property
    def text(self) -> str:
        """Human text."""
        if self.display is not None:
            return self.display
        if isinstance(self.value, bool):
            return "yes" if self.value else "no"
        return machine_text(self.value)


@dataclass
class Table:
    """Rows of facts sharing columns.

    Attributes:
        key: Machine name ("" when the table is the section's only content, so rows sit directly under the section).
        title: Human title.
        columns: (key, label) per column.
        rows: Dicts of column key → Cell (use `add_row`, which normalises plain values and pairs).
        id_key: Column whose value names the row in text output (else the 1-based row number).
    """
    key: str
    title: str
    columns: list[tuple[str, str]]
    rows: list[dict[str, Cell]] = field(default_factory=list)
    id_key: str | None = None

    def add_row(self, row: dict) -> None:
        """Append a row given as column key → value, (value, display) or Cell."""
        self.rows.append({key: Cell.of(raw) for key, raw in row.items()})

    def cell(self, row: dict[str, Cell], key: str) -> Cell:
        """The cell for `key` (an empty cell when the row lacks it)."""
        return row.get(key, Cell("", ""))


@dataclass
class Section:
    """A titled group of items and tables."""
    key: str
    title: str
    items: list[Item] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, key: str, label: str, value: object, display: str | None = None) -> None:
        """Append an item."""
        self.items.append(Item(key, label, value, display))


@dataclass
class Report:
    """The whole document."""
    title: str
    generated: datetime
    sections: list[Section] = field(default_factory=list)


__all__ = ["machine_text", "Cell", "Item", "Table", "Section", "Report"]
