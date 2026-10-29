"""The Formula Editor's drawer: the dialect reference, the compiler's output, and the point probe / engine check.

* **Reference** — the dialect guide (`docs/formulas.md`), the catalogue of names the compiler knows (click one to
  insert it), and a summary of the formula being edited.
* **Compiler** — what the last good compile generated (the numpy module, the GLSL) and the compiler's warnings.
* **Probe** — one point through the formula on numpy (and GLSL, on a context of its own), and *Check numpy vs GLSL*
  over the verifier's sample points; both run on the thread pool so the window never waits for a GL context.
"""

from __future__ import annotations

from dataclasses import replace
from html import escape
from pathlib import Path

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QTabWidget,
                               QVBoxLayout, QWidget)

from ..formulas import completion as FC, verify
from .background import run_in_background
from .formula_browser import formula_description
from .formula_session import FormulaSession
from .script_drawer import STYLE, _Browser, guide_html

GUIDE_PATH = Path(__file__).resolve().parents[2] / "docs" / "formulas.md"
TAB_REFERENCE, TAB_COMPILER, TAB_PROBE = "reference", "compiler", "probe"


def _page(body: str) -> str:
    return STYLE + "<body>" + body + "</body>"


# --- reference -------------------------------------------------------------------------------------------------
class ReferencePanel(QWidget):
    """Guide / catalogue / this formula, with a search box.

    Signals:
        insert_requested(str): A catalogue name was clicked — insert it at the cursor.
    """
    insert_requested = Signal(str)

    def __init__(self, session: FormulaSession, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self.guide_button = QPushButton("Guide", self)
        self.catalogue_button = QPushButton("Names", self)
        self.formula_button = QPushButton("This formula", self)
        for b in (self.guide_button, self.catalogue_button, self.formula_button):
            b.setCheckable(True)
            b.setAutoExclusive(True)
        self.catalogue_button.setChecked(True)
        self.search = QLineEdit(self, placeholderText="Search the guide and the names (e.g. atan2, VAR_REAL, depth)…")
        self.search.setClearButtonEnabled(True)
        self.browser = _Browser(self)
        self.browser.link_clicked.connect(self._link)
        buttons = QHBoxLayout()
        for b in (self.guide_button, self.catalogue_button, self.formula_button):
            buttons.addWidget(b)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(buttons)
        layout.addWidget(self.search)
        layout.addWidget(self.browser, 1)
        self._timer = QTimer(self, singleShot=True, interval=200)
        self._timer.timeout.connect(self.render)
        self.search.textChanged.connect(lambda _t: self._timer.start())
        for b in (self.guide_button, self.catalogue_button, self.formula_button):
            b.clicked.connect(self.render)
        self._guide_html: str | None = None
        self.render()

    @property
    def mode(self) -> str:
        """`guide`, `names` or `formula`."""
        return "guide" if self.guide_button.isChecked() else "names" if self.catalogue_button.isChecked() else "formula"

    def show_mode(self, mode: str) -> None:
        """Switch to one of the three views."""
        {"guide": self.guide_button, "names": self.catalogue_button, "formula": self.formula_button}.get(mode, self.catalogue_button).setChecked(True)
        self.render()

    def render(self) -> None:
        """Rebuild the page for the mode and the search text."""
        query = self.search.text().strip().lower()
        if self.mode == "guide":
            self.browser.setHtml(_page(self._guide(query)))
        elif self.mode == "names":
            self.browser.setHtml(_page(self._catalogue(query)))
        else:
            self.browser.setHtml(_page(self._formula()))

    def _guide(self, query: str) -> str:
        if self._guide_html is None:
            try:
                self._guide_html = guide_html(GUIDE_PATH.read_text(encoding="utf-8"))
            except OSError:
                self._guide_html = "<p class='hint'>docs/formulas.md is not available.</p>"
        if not query:
            return self._guide_html
        kept = [block for block in self._guide_html.split("\n") if query in block.lower()]
        return "\n".join(kept) if kept else f"<p class='hint'>Nothing in the guide mentions '{escape(query)}'.</p>"

    @staticmethod
    def _catalogue(query: str) -> str:
        groups: dict[str, list[FC.Reference]] = {}
        for ref in FC.CATALOGUE:
            if query and query not in ref.name.lower() and query not in ref.desc.lower():
                continue
            groups.setdefault(ref.group, []).append(ref)
        if not groups:
            return f"<p class='hint'>No name matches '{escape(query)}'.</p>"
        parts = ["<p class='hint'>Click a name to insert it at the cursor.</p>"]
        for group, refs in groups.items():
            rows = "".join(f"<tr><td class='n'><a href='insert:{escape(r.name)}'>{escape(r.sig)}</a></td><td>{escape(r.desc)}</td></tr>" for r in refs)
            parts.append(f"<h3>{escape(group)}</h3><table width='100%'>{rows}</table>")
        return "".join(parts)

    def _formula(self) -> str:
        var = self.session.variation
        if var is None:
            return "<p class='hint'>No formula is loaded.</p>"
        shown = replace(var, name=self.session.name or var.name)
        text = escape(formula_description(shown)).replace("\n", "<br>")
        warnings = self.session.warnings
        if warnings:
            text += "<h3>Compiler remarks</h3><ul>" + "".join(f"<li>{escape(w)}</li>" for w in warnings) + "</ul>"
        return f"<p style='font-family: monospace'>{text}</p>"

    def _link(self, url: str) -> None:
        if url.startswith("insert:"):
            self.insert_requested.emit(url[len("insert:"):])


# --- compiler output --------------------------------------------------------------------------------------------
class CompilerOutputPanel(QWidget):
    """The generated numpy / GLSL of the last good compile and the compiler's warnings."""

    def __init__(self, session: FormulaSession, parent: QWidget | None = None):
        super().__init__(parent)
        self.session = session
        self.which = QComboBox(self)
        self.which.addItems(["GLSL (GPU engine)", "numpy (CPU engine)", "Warnings"])
        self.which.setToolTip("What the compiler made of the code, for the two engines")
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        font = self.output.font()
        font.setFamily("monospace")
        self.output.setFont(font)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.which)
        layout.addWidget(self.output, 1)
        self.which.currentIndexChanged.connect(lambda _i: self.refresh())
        self.refresh()

    def refresh(self) -> None:
        """Show the chosen output of the session's last good compile."""
        session = self.session
        index = self.which.currentIndex()
        if session.variation is None:
            text = "No formula compiled yet."
        elif index == 0:
            text = session.generated_glsl or "(a native built-in: no generated GLSL — its snippet is shown on the Reference tab)"
        elif index == 1:
            text = session.generated_numpy or "(a native built-in: no generated numpy — see its source in the Reference tab's skeleton)"
        else:
            text = "\n".join(session.warnings) or "No warnings."
        if session.error:
            text = f"// the current text does not compile ({session.error}); this is the last good compile\n\n" + text
        self.output.setPlainText(text)


# --- probe / verify ---------------------------------------------------------------------------------------------
class ProbePanel(QWidget):
    """One point through the formula on both engines, and *Check numpy vs GLSL* over the sample points.

    Signals:
        status(str): A line for the status bar (the check's outcome).
    """
    status = Signal(str)

    def __init__(self, session: FormulaSession, params_provider, parent: QWidget | None = None):
        """Args:
            session: Whose formula to probe.
            params_provider: Returns the selected transform's parameter values (dict) — what the previews use.
            parent: Qt owner.
        """
        super().__init__(parent)
        self.session = session
        self._params = params_provider
        self._busy = False
        self.boxes: dict[str, QDoubleSpinBox] = {}
        row = QHBoxLayout()
        for name, value in (("x", 0.5), ("y", 0.25), ("z", 0.0)):
            box = QDoubleSpinBox(self)
            box.setRange(-1000.0, 1000.0)
            box.setDecimals(4)
            box.setSingleStep(0.1)
            box.setValue(value)
            box.setKeyboardTracking(False)
            row.addWidget(QLabel(f"FT{name}", self))
            row.addWidget(box, 1)
            self.boxes[name] = box
        self.probe_button = QPushButton("Probe point", self)
        self.probe_button.setToolTip("Send this input point through the formula (weight 1, identity affine) on numpy and on GLSL")
        self.check_button = QPushButton("Check numpy vs GLSL", self)
        self.check_button.setToolTip("Run the verifier's sample points through both engines and compare them (the test-suite's check)")
        self.result = QPlainTextEdit(self)
        self.result.setReadOnly(True)
        font = self.result.font()
        font.setFamily("monospace")
        self.result.setFont(font)
        self.result.setPlaceholderText("Results appear here.")
        buttons = QHBoxLayout()
        buttons.addWidget(self.probe_button)
        buttons.addWidget(self.check_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addLayout(buttons)
        layout.addWidget(self.result, 1)
        self.probe_button.clicked.connect(self.probe)
        self.check_button.clicked.connect(self.check)
        for box in self.boxes.values():
            box.valueChanged.connect(lambda _v: self.probe() if self.result.toPlainText() else None)

    @property
    def busy(self) -> bool:
        """True while a probe or check runs on the thread pool."""
        return self._busy

    def point(self) -> tuple[float, float, float]:
        """The input point typed in."""
        return (self.boxes["x"].value(), self.boxes["y"].value(), self.boxes["z"].value())

    def _start(self, work, on_done) -> None:
        var = self.session.variation
        if var is None:
            self.result.setPlainText("No formula to run.")
            return
        if self._busy:
            return
        self._busy = True
        self.result.setPlainText("Working…")
        run_in_background(work, var, dict(self._params() or {}), on_done=on_done, on_error=self._failed)

    def probe(self) -> None:
        """Run the point through both engines (GLSL on a standalone context created for the purpose)."""
        point = self.point()

        def work(var, params):
            ctx = None
            try:
                ctx = verify.create_context()
            except Exception:  # noqa: BLE001 - no GL here: numpy only
                ctx = None
            try:
                return verify.probe(var, point, params, ctx)
            finally:
                if ctx is not None:
                    ctx.release()

        self._start(work, self._probed)

    def _probed(self, result: verify.ProbeResult) -> None:
        self._busy = False
        lines = [f"input FTx {result.point[0]:g}  FTy {result.point[1]:g}  FTz {result.point[2]:g}", ""] + result.lines()
        if result.glsl is None:
            lines.append("")
            lines.append("(no OpenGL context could be created here: numpy only)")
        self.result.setPlainText("\n".join(lines))

    def check(self) -> None:
        """Compare the engines on the verifier's sample points."""
        def work(var, params):
            ctx = verify.create_context()
            try:
                return verify.compare(var, ctx, params=params or None)
            finally:
                ctx.release()

        self._start(work, self._checked)

    def _checked(self, report: verify.VerifyReport) -> None:
        self._busy = False
        header = ("✓ " if report.ok else "✗ ") + report.message
        lines = [header, "", f"{'point':<12}{'numpy FPx':>12}{'glsl FPx':>12}{'numpy FPy':>12}{'glsl FPy':>12}{'numpy TC':>10}{'glsl TC':>10}"]
        for i, (n, g) in enumerate(zip(report.numpy_out, report.glsl_out)):
            lines.append(f"{i + 1:<12}{n[3]:>12.5g}{g[3]:>12.5g}{n[4]:>12.5g}{g[4]:>12.5g}{n[6]:>10.4g}{g[6]:>10.4g}")
        self.result.setPlainText("\n".join(lines))
        self.status.emit(header)

    def _failed(self, exc: Exception) -> None:
        self._busy = False
        self.result.setPlainText(f"Could not run: {exc}")
        self.status.emit(f"Check failed: {exc}")


class FormulaDrawer(QTabWidget):
    """Reference / Compiler / Probe tabs, collapsible at the window's right edge."""

    def __init__(self, session: FormulaSession, params_provider, parent: QWidget | None = None):
        super().__init__(parent)
        self.reference = ReferencePanel(session, self)
        self.compiler = CompilerOutputPanel(session, self)
        self.probe = ProbePanel(session, params_provider, self)
        self.addTab(self.reference, "Reference")
        self.addTab(self.compiler, "Compiler")
        self.addTab(self.probe, "Probe")
        self.setDocumentMode(True)
        self.setMinimumWidth(300)

    def show_tab(self, name: str) -> None:
        """Open one of the tabs by name (`reference`, `compiler`, `probe`)."""
        index = {TAB_REFERENCE: 0, TAB_COMPILER: 1, TAB_PROBE: 2}.get(name, 0)
        self.setCurrentIndex(index)

    def refresh(self) -> None:
        """The session compiled or loaded: refresh what shows compile results."""
        self.compiler.refresh()
        if self.reference.mode == "formula":
            self.reference.render()


__all__ = ["FormulaDrawer", "ReferencePanel", "CompilerOutputPanel", "ProbePanel", "TAB_REFERENCE", "TAB_COMPILER", "TAB_PROBE"]
