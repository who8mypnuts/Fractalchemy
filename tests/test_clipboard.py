"""Copy / paste of gradients as UGR text (Ultra Fractal & Apophysis interchange)."""

from PySide6.QtGui import QGuiApplication

from hueclid.formats.clipboard import gradient_to_text, text_to_gradient
from hueclid.model import Gradient
from hueclid.ui.main_window import MainWindow

RGB3 = [(0, 0, 0), (255, 0, 0), (255, 255, 255)]

APOPHYSIS_STYLE = """Apophysis gradient {
gradient:
 title="Apophysis gradient" smooth=no
 index=0 color=255
 index=199 color=65280
 index=399 color=16711680
}
"""
UF_WRAPPED = "  smooth=yes rotation=-6 index=46 color=16709120 index=98 color=74\r\n  index=196 color=12320848\r\n"
FLAME_SNIPPET = '<flame name="x"><palette count="2" format="RGB">\n  FF000000FF00\n</palette></flame>'


def test_round_trip_text():
    g = Gradient.from_colors("demo", RGB3)
    text = gradient_to_text(g)
    assert text.startswith("demo {\ngradient:\n title=\"demo\" smooth=no\n index=0 color=0\n")
    back = text_to_gradient(text)
    assert back.name == "demo" and [s.color for s in back.stops] == RGB3


def test_paste_accepts_other_programs_text():
    apo = text_to_gradient(APOPHYSIS_STYLE)
    assert apo.name == "Apophysis gradient" and [s.color for s in apo.stops] == [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    uf = text_to_gradient(UF_WRAPPED)
    assert len(uf.stops) == 3 and uf.stops[0].color == (0, 246, 254)
    flame = text_to_gradient(FLAME_SNIPPET)
    assert [s.color for s in flame.stops] == [(255, 0, 0), (0, 255, 0)]
    assert text_to_gradient("just some prose") is None and text_to_gradient("") is None


def test_buttons_copy_and_paste_through_the_clipboard(qapp):
    window = MainWindow()
    window.show()
    panel = window.wholeGradientPanel
    clipboard = QGuiApplication.clipboard()
    clipboard.setText("nothing useful")
    window.document.replace(Gradient.from_colors("src", RGB3))
    assert panel.copy_button.isEnabled() and not panel.paste_button.isEnabled()

    panel.copy_button.click()
    assert clipboard.text().startswith("src {")
    assert panel.paste_button.isEnabled()

    window.document.replace(Gradient.from_colors("target", [(9, 9, 9), (1, 1, 1)]), source_index=3)
    panel.paste_button.click()
    assert [s.color for s in window.document.gradient.stops] == RGB3
    assert window.document.gradient.name == "target" and window.document.source_index == 3  # stays in its slot
    assert window.document.modified and "Pasted" in window.statusBar().currentMessage()

    window.document.replace(Gradient())
    assert panel.isEnabled() and panel.paste_button.isEnabled() and not panel.copy_button.isEnabled()
    window.close()
