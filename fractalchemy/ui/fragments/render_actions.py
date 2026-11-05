"""The Render menu's commands: the render window, the render queue, regions, batch renders, mesh and DE export.

A helper of `FragmentsWindow` (it holds the window as `w`) so the window stays a thin coordinator. The Render
Fragment window and the Render Queue are created on first use and live as long as the window; *shutdown* stops
their jobs. Every command checks what it needs (a built fragment, a distance estimator, a saved file) and says so
in the status bar instead of failing.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from .file_actions import is_bundled
from .render_window import FragRenderWindow

if TYPE_CHECKING:
    from .render_queue import RenderQueueWindow
    from .window import FragmentsWindow


class RenderActions:
    """Rendering to files and exporting (see the module docstring)."""

    def __init__(self, window: "FragmentsWindow"):
        self.w = window
        self._render_window: FragRenderWindow | None = None
        self._queue: "RenderQueueWindow | None" = None
        self._mesh_dialog = None
        self._batch_dialog = None

    # --- the windows ----------------------------------------------------------------------------------------------------
    @property
    def render_window(self) -> FragRenderWindow:
        """The Render Fragment window (created on first use)."""
        if self._render_window is None:
            w = self.w
            self._render_window = FragRenderWindow(lambda: w.tabs.document, lambda: w.anim.settings, self.rate_hint, w, w._settings)
        return self._render_window

    @property
    def queue(self) -> "RenderQueueWindow":
        """The Render Queue window (created on first use)."""
        if self._queue is None:
            from .render_queue import RenderQueueWindow
            self._queue = RenderQueueWindow(self.w)
            self._queue.add_requested.connect(self.queue_current)
            self._queue.entry_finished.connect(lambda entry: self.w.log.add("info" if entry.state == "done" else "warning",
                                                                             f"Render queue: {entry.label} {entry.state}"
                                                                             + (f" — {entry.message}" if entry.message else "")))
        return self._queue

    def show_render_window(self) -> None:
        window = self.render_window
        window.prepare_for(self.w.tabs.document, self.w.driver.render_size())
        window.bring_to_front()
        problems = window.problems()
        if problems:
            self.w.message("Render: cannot start — " + problems[0])

    def show_queue(self) -> None:
        queue = self.queue
        queue.show()
        queue.raise_()

    def rate_hint(self):
        """(subframes per second, width, height) of the viewport's last render, for the time estimate."""
        stats = self.w.driver.stats
        if stats is None or stats.seconds <= 0 or stats.passes_done <= 0:
            return None
        return stats.passes_done / stats.seconds, stats.width, stats.height

    # --- commands -------------------------------------------------------------------------------------------------------------
    def queue_current(self) -> None:
        """*Add to render queue*: the current tab with the Render Fragment window's settings, rendered later in turn."""
        w = self.w
        document = w.tabs.document
        if document is None or document.request() is None:
            w.message("Build the fragment first")
            return
        settings = self.render_window.current_settings()
        if settings.preview:
            w.message("A queued render must write a file — turn off Preview in the render window")
            return
        problems = settings.problems()
        if problems:
            w.message("Cannot queue: " + "; ".join(problems))
            return
        entry = self.queue.add(FragRenderWindow.make_input(document, settings))
        self.show_queue()
        w.message(f"Queued {entry.label} → {Path(settings.output_path).name}")

    def render_region(self, region: tuple) -> None:
        """Ctrl+drag on the viewport: the render window with that region of the frame as its crop."""
        self.show_render_window()
        self.render_window.set_region(region, self.w.driver.render_size())
        self.w.message(f"Render region {region[2] * 100:.0f}% × {region[3] * 100:.0f}% of the frame — Start renders the crop")

    def show_batch_dialog(self) -> None:
        """*Batch render presets…* for the current tab (saved first — the batch renders from the file)."""
        from .batch_dialog import BatchDialog
        w = self.w
        document = w.tabs.document
        if document is None or document.source is None:
            return
        if document.path is None or document.modified or is_bundled(document.path):
            answer = QMessageBox.question(w, "Batch render", "The batch renders from the saved file. Save the fragment now?",
                                          QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Save or not w.files.save():
                return
        dialog = BatchDialog(document.path, self.render_window.current_settings(), len(document.source.presets),
                             len(document.source.keyframe_names()), w)
        dialog.show()
        self._batch_dialog = dialog

    def _de_request(self, what: str):
        """The current tab's request when it has a distance estimator (else a status message and None)."""
        from ...fragments.gl.mesh import has_distance_estimator
        document = self.w.tabs.document
        request = document.request() if document is not None else None
        if request is None:
            self.w.message("Build the fragment first")
            return None
        if not has_distance_estimator(request.modern):
            self.w.message(f"{what} needs a fragment with `float DE(vec3 p)` (a 3D distance estimator)")
            return None
        return request

    def show_mesh_export(self) -> None:
        """*Export mesh…*: the current tab's DE sampled on the GPU and meshed."""
        from .mesh_export_dialog import MeshExportDialog
        request = self._de_request("Export mesh")
        if request is None:
            return
        w = self.w
        document = w.tabs.document
        dialog = MeshExportDialog(w, request, document.name, w._settings, w._three_d, w.document_folder(document))
        dialog.show()
        self._mesh_dialog = dialog

    def show_export_de(self) -> None:
        """*Export DE…*: the distance estimator as GLSL / Shadertoy / Unity / Unreal code with the values baked in."""
        from .export_de_dialog import ExportDEDialog
        request = self._de_request("Export DE")
        if request is None:
            return
        w = self.w
        document = w.tabs.document
        dialog = ExportDEDialog(w, request.modern.fragment, request.values, document.name, w.document_folder(document))
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.show()

    # --- lifecycle ---------------------------------------------------------------------------------------------------------------
    def confirm_quit(self) -> bool:
        """A running render or queue? Ask; False keeps running."""
        if self._render_window is not None and not self._render_window.confirm_quit():
            return False
        if self._queue is not None and self._queue.running:
            answer = QMessageBox.question(self.w, "Render queue", "The render queue is still running. Stop it and quit?",
                                          QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return False
        return True

    def shutdown(self) -> None:
        """Stop the render window's job, the mesh dialog's jobs and the queue (waits for their threads)."""
        if self._render_window is not None and self._render_window.job is not None:
            self._render_window.job.cancel()
            self._render_window.wait_for_job()
        if self._mesh_dialog is not None:
            self._mesh_dialog.close()        # waits for its jobs
        if self._queue is not None:
            self._queue.stop()
            self._queue.wait_for_job()


__all__ = ["RenderActions"]
