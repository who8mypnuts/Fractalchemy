"""Batch Open: turn every image in a folder into a gradient and save them all into one file.

Run from the Gradient Library's *Batch Open* button. A Save-As dialog picks one
target file (and so the folder to read); every image under that folder, its
subfolders included, is extracted with the same palette code the Open flow uses
(`formats.registry.load_gradients`) and every gradient is written into the
target. The file is created if new and appended to if it already exists, then
loaded into the editor so the batch can be browsed like an Open result.

The whole disk phase (scan, extraction, writing) runs on the thread pool.

Known limitation: images with the same stem in different subfolders produce
gradient entries that share a name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

from ..formats import DEFAULT_SAVE_FORMAT, FORMATS, format_for, load_gradients
from ..imaging import supported_image_extensions
from ..model import Gradient
from .background import run_in_background
from .file_actions import FileActions


class BatchError(Exception):
    """Nothing could be imported (no images beside the target, or all reads failed)."""


@dataclass
class BatchResult:
    """What one batch import achieved; `failures` pairs image names with their error text."""
    images: int = 0
    gradients: int = 0
    failures: list[tuple[str, str]] = field(default_factory=list)
    note: str = ""


def batch_dialog_filter() -> str:
    """QFileDialog filter of the formats that can hold several gradients (the default save format first)."""
    formats = [fmt for fmt in FORMATS if fmt.can_create and fmt.can_append and fmt.multi_entry]
    formats.sort(key=lambda fmt: fmt is not DEFAULT_SAVE_FORMAT)  # stable: puts UGR first
    return ";;".join(fmt.dialog_filter() for fmt in formats)


def image_files_in(folder: Path) -> list[Path]:
    """Every decodable image under `folder` (subfolders included), sorted by path."""
    extensions = supported_image_extensions()
    return sorted(path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in extensions)


def extract_images(images: list[Path]) -> tuple[list[Gradient], list[tuple[str, str]]]:
    """A gradient per image; anything that cannot be read is skipped into the failures list."""
    gradients: list[Gradient] = []
    failures: list[tuple[str, str]] = []
    for path in images:
        try:
            gradients.extend(gradient for gradient in load_gradients(path) if gradient.stops)
        except Exception as exc:  # noqa: BLE001 - one bad image must not stop the batch
            failures.append((path.name, str(exc)))
    return gradients, failures


def write_gradients(gradients: list[Gradient], target: Path) -> str:
    """Write every gradient into `target`, creating or appending as needed.

    Returns:
        A note for the status bar (why an existing file was kept), or ''.

    Raises:
        ValueError: If the target's format cannot hold several gradients.
    """
    fmt = format_for(target)
    if not (fmt.can_create and fmt.can_append and fmt.multi_entry):
        raise ValueError(f"Gradients cannot be batched into {fmt.name} files — choose a .ugr, .flame or .fa file")
    existed = target.exists()
    for gradient in gradients:
        fmt.append(gradient, target)
    return f"{target.name} already existed — the batch was added to it" if existed else ""


def batch_import(target: Path) -> BatchResult:
    """One complete batch: scan the folder next to `target`, extract, write into `target`.

    Raises:
        BatchError: If there are no images, or no image could be read.
        ValueError: If the target format cannot take several gradients.
    """
    images = image_files_in(target.parent)
    if not images:
        raise BatchError(f"No supported images found in {target.parent}")
    gradients, failures = extract_images(images)
    if not gradients:
        raise BatchError("None of the images could be read\n" + "\n".join(f"{name}: {reason}" for name, reason in failures))
    return BatchResult(len(images), len(gradients), failures, write_gradients(gradients, target))


class BatchImages(QObject):
    """The Gradient Library's Batch Open flow: pick a target file, import the images beside it.

    Signals:
        status(str): Outcome text for the status bar.
    """
    status = Signal(str)

    def __init__(self, files: FileActions, parent: QWidget):
        """Args:
            files: The window's FileActions — for the unsaved-edits check and
                for loading the finished batch like an Open result.
            parent: Widget that owns dialogs and message boxes.
        """
        super().__init__(parent)
        self._files = files
        self._parent = parent
        self._last_dir = str(Path.cwd())

    def run(self) -> None:
        """Ask where to save, then import the gradients from the images beside that file."""
        if not self._files.confirm_discard():
            return
        path, _ = QFileDialog.getSaveFileName(
            self._parent, "Batch-open folder images as gradients", self._suggest_target(), batch_dialog_filter())
        if not path:
            return
        target = Path(path)
        self._last_dir = str(target.parent)
        self.status.emit(f"Batch importing gradients from images in {target.parent.name}…")
        run_in_background(batch_import, target, on_done=lambda result: self._done(target, result),
                          on_error=self._fail)

    # --- helpers ------------------------------------------------------------
    def _suggest_target(self) -> str:
        stem = Path(self._last_dir).name or "gradients"
        return str(Path(self._last_dir) / f"{stem}{DEFAULT_SAVE_FORMAT.extensions[0]}")

    def _done(self, target: Path, result: BatchResult) -> None:
        summary = self._summary(target, result)
        report = self._failure_report(result)
        self._files.open_path(target, 0, summary)
        show = QMessageBox.warning if result.failures else QMessageBox.information
        show(self._parent, "Batch Open", summary + ("\n\n" + report if report else ""))

    def _summary(self, target: Path, result: BatchResult) -> str:
        summary = f"Imported {result.gradients} gradients from {result.images} images into '{target.name}'"
        if result.failures:
            summary += f" ({len(result.failures)} images skipped)"
        if result.note:
            summary += f"\n{result.note}"
        return summary

    def _failure_report(self, result: BatchResult) -> str:
        lines = [f"{name} — {reason}" for name, reason in result.failures[:12]]
        if len(result.failures) > 12:
            lines.append(f"… and {len(result.failures) - 12} more")
        return "Skipped images:\n" + "\n".join(lines)

    def _fail(self, exc: Exception) -> None:
        self.status.emit(f"Batch Open: {exc}")
        QMessageBox.warning(self._parent, "Batch Open", str(exc))
