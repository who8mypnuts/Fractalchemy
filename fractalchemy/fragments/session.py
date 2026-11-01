"""Sessions: the open tabs with their unsaved text and current settings, as one JSON file — and the autosave that
brings a crashed session back.

A `.fasession` lists every tab: the file it came from (if any), the full text when the tab had unsaved edits, the
current settings text (so the look is restored, not only the source), the preset in effect and which tab was current.
*File ▸ Save session* writes one by hand; the autosave writes the same into the cache folder every few minutes and
removes it on a clean shutdown, so a file left behind means the last run ended badly — the next start offers to
recover it. Qt-free; the window's `session_actions.py` captures and restores.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

SESSION_SUFFIX = ".fasession"
AUTOSAVE_NAME = "autosave" + SESSION_SUFFIX
VERSION = 1


@dataclass
class SessionTab:
    """One tab.

    Attributes:
        path: The file the tab was opened from (None: a new fragment).
        text: The full source when the tab had unsaved edits (None: the file's text is current).
        settings: The settings text (the parameter values) at the time.
        preset: The preset in effect.
        modified: Whether the tab had unsaved edits.
    """
    path: str | None = None
    text: str | None = None
    settings: str = ""
    preset: str = ""
    modified: bool = False


@dataclass
class Session:
    """What a session file holds."""
    tabs: list[SessionTab] = field(default_factory=list)
    current: int = 0
    saved_at: float = 0.0
    version: int = VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=1)

    @classmethod
    def from_json(cls, text: str) -> "Session":
        """`ValueError` for text that is not a session."""
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"not a session file: {exc}") from exc
        if not isinstance(data, dict) or not isinstance(data.get("tabs"), list):
            raise ValueError("not a session file: no tabs")
        tabs = [SessionTab(**{k: v for k, v in entry.items() if k in SessionTab.__dataclass_fields__}) for entry in data["tabs"] if isinstance(entry, dict)]
        return cls(tabs, int(data.get("current", 0)), float(data.get("saved_at", 0.0)), int(data.get("version", VERSION)))

    def write(self, path: Path) -> Path:
        path = Path(path)
        if path.suffix.lower() != SESSION_SUFFIX:
            path = path.with_suffix(SESSION_SUFFIX)
        self.saved_at = time.time()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")
        return path

    @classmethod
    def read(cls, path: Path) -> "Session":
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    @property
    def empty(self) -> bool:
        return not self.tabs

    def describe(self) -> str:
        names = [Path(t.path).name if t.path else "Unnamed" for t in self.tabs]
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(self.saved_at)) if self.saved_at else "unknown time"
        unsaved = sum(1 for t in self.tabs if t.modified)
        return f"{len(self.tabs)} tab{'s' if len(self.tabs) != 1 else ''} ({', '.join(names[:6])}{'…' if len(names) > 6 else ''}), " \
               f"{unsaved} with unsaved edits, saved {when}"


class AutosaveStore:
    """The autosave file in `folder` (see the module docstring)."""

    def __init__(self, folder: Path):
        self.path = Path(folder) / AUTOSAVE_NAME

    @property
    def exists(self) -> bool:
        return self.path.is_file()

    def write(self, session: Session) -> None:
        try:
            session.write(self.path)
        except OSError:
            pass

    def read(self) -> Session | None:
        if not self.exists:
            return None
        try:
            return Session.read(self.path)
        except (OSError, ValueError):
            return None

    def clear(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass


__all__ = ["Session", "SessionTab", "AutosaveStore", "SESSION_SUFFIX", "AUTOSAVE_NAME"]
