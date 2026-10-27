"""The Info tab of the settings panel: facts about the loaded fractal."""

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from fractalchemy.fractal import Flame, XForm
from fractalchemy.fractal.formats import load_flames
from fractalchemy.render.settings import RenderStats
from fractalchemy.ui.info_panel import InfoPanel, formula_facts, formula_uses
from fractalchemy.ui.settings_panel import TAB_KEY, SettingsPanel
from tests.conftest import spin, wait_until


def rows(item) -> dict[str, str]:
    return {item.child(i).text(0): item.child(i).text(1) for i in range(item.childCount())}


def child(item, key):
    return next(item.child(i) for i in range(item.childCount()) if item.child(i).text(0) == key)


@pytest.fixture
def panel(qapp):
    p = InfoPanel()
    p.resize(320, 600)
    p.show()
    yield p
    p.close()


def test_empty_panel_says_so(panel):
    assert panel.tree.topLevelItemCount() == 1 and panel.tree.topLevelItem(0).text(0) == "No fractal loaded"
    panel.show_camera()   # no-ops without a flame
    panel.show_palette()
    assert panel.current_formulas() == []


def test_panel_describes_file_camera_transforms_formulas_and_colouring(panel, samples):
    path = samples / "sample flames" / "candy.flame"
    flame = load_flames(path)[2]
    panel.show_flame(flame, path, 2)
    groups = panel._groups
    assert list(groups) == ["Fractal", "Transforms", "Formulas", "Colouring", "Render"]
    fractal = rows(groups["Fractal"])
    assert fractal["Name"] == "rotated" and fractal["File"] == "candy.flame" and fractal["Entry"] == "#3"
    assert fractal["Format"].startswith("Apophysis / flam3") and "Apophysis 2.09" in fractal["Format"]
    assert fractal["Size"] == "3840 × 2160" and fractal["3D camera"] == "flat (2D)" and fractal["Transforms"] == "6 + final"
    assert child(groups["Fractal"], "File").toolTip(1) == str(path)
    # transforms: weight share, variation summary, and the details underneath
    transforms = groups["Transforms"]
    assert transforms.text(1) == "7 (xaos)" and transforms.childCount() == 7
    third = transforms.child(2)
    assert third.text(1) == "13%  ·  sinusoidal -0.128 · hyperbolic 0.088 · pre_blur 3"
    details = rows(third)
    assert details["Opacity"] == "0.2" and details["Variations"] == "3" and "Post affine" in details
    assert rows(child(third, "Variations")) == {"sinusoidal": "-0.128", "hyperbolic": "0.088", "pre_blur": "3"}
    final = transforms.child(6)
    assert final.text(0) == "Final" and "Weight" not in rows(final)
    assert "lazysusan_spin" in rows(child(child(final, "Variations"), "lazysusan"))
    # distinct formulas with use counts and facts
    assert panel.current_formulas() == ["bubble", "disc", "hyperbolic", "lazysusan", "linear", "pre_blur", "radial_blur",
                                        "sinusoidal", "spherical"]
    formulas = rows(groups["Formulas"])
    assert formulas["pre_blur"].startswith("×3  ·  pre  ·  random") and formulas["linear"].startswith("×2  ·  normal")
    assert "5 parameters" in formulas["lazysusan"] and child(groups["Formulas"], "lazysusan").toolTip(1).startswith("lazysusan")
    colouring = rows(groups["Colouring"])
    assert colouring["Gamma threshold"] == "0.04" and colouring["Background"] == "#000000"
    assert panel.palette_label is not None and not panel.palette_label.pixmap().isNull()
    assert rows(groups["Render"]) == {"Status": "not rendered yet"}


def test_camera_palette_and_render_rows_update_in_place(panel):
    flame = Flame("f", [XForm(variations={"julian": 1.0}, params={"julian_power": 3})])
    panel.show_flame(flame)
    fractal = rows(panel._groups["Fractal"])
    assert fractal["File"] == "not saved" and fractal["Centre"] == "0, 0"
    flame.camera.center = (0.25, -1.5)
    flame.camera.pitch = 0.5
    panel.show_camera()
    fractal = rows(panel._groups["Fractal"])
    assert fractal["Centre"] == "0.25, -1.5" and fractal["3D camera"].startswith("pitch 28.65°")
    before = panel.palette_label.pixmap().toImage()
    flame.palette = [(255, 0, 0)] * 256
    panel.show_palette()
    assert panel.palette_label.pixmap().toImage() != before
    panel.show_render(RenderStats("CPU (numpy, 2 threads)", 2, 6, 1_500_000, 0, 3.0, 400, 300, ["note one"]))
    render = rows(panel._groups["Render"])
    assert render["Engine"] == "CPU (numpy, 2 threads)" and render["Image"] == "400 × 300" and render["Passes"] == "2 of 6"
    assert render["Samples"] == "1.5 M  ·  500 k/s" and render["Time"] == "3.0 s" and render["Note"] == "note one"
    assert panel._groups["Render"].text(1) == "CPU"
    assert rows(child(child(panel._groups["Transforms"].child(0), "Variations"), "julian")) == {"julian_power": "3"}


def test_unavailable_formulas_are_flagged_and_double_click_emits_the_name(panel):
    flame = Flame("f", [XForm(variations={"linear": 1.0, "no_such_formula": 0.5})], unsupported=["no_such_formula"])
    panel.show_flame(flame)
    assert rows(panel._groups["Fractal"])["Ignored"] == "no_such_formula"
    assert panel._groups["Formulas"].text(1) == "2  ·  1 not available"
    assert "not available" in rows(panel._groups["Formulas"])["no_such_formula"]
    assert formula_uses(flame) == {"linear": 1, "no_such_formula": 1}
    assert formula_facts("no_such_formula", 1)[0].startswith("×1  ·  not available")
    seen = []
    panel.formula_activated.connect(seen.append)
    panel._activated(child(panel._groups["Formulas"], "linear"), 0)
    panel._activated(panel._groups["Colouring"], 0)   # not a formula row: nothing
    assert seen == ["linear"]


def test_settings_panel_has_info_first_and_remembers_the_tab(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    panel = SettingsPanel(settings=settings)
    assert [panel.tabs.tabText(i) for i in range(panel.tabs.count())] == ["Info", "Image"]
    assert panel.tabs.currentIndex() == 0 and panel.tabs.widget(0) is panel.info
    panel.tabs.setCurrentIndex(1)
    assert int(settings.value(TAB_KEY)) == 1
    again = SettingsPanel(settings=settings)
    assert again.tabs.currentIndex() == 1


def test_main_window_feeds_the_info_tab_and_links_to_the_formula_browser(qapp, tmp_path, samples):
    from fractalchemy.library.catalog import FRACTAL_CATALOG
    from fractalchemy.library.roots import LibraryRoots
    from fractalchemy.ui.main_window import MainWindow

    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    win = MainWindow(LibraryRoots(settings), LibraryRoots(settings, key=FRACTAL_CATALOG.roots_key), prefer_gpu=False, settings=settings)
    win.show()
    try:
        info = win.settingsPanel.info
        assert info.tree.topLevelItem(0).text(0) == "No fractal loaded"
        path = Path(samples) / "sample flames" / "candy.flame"
        win.open_path(path, 3)
        wait_until(lambda: win.document.flame is not None and win.document.flame.name == "pearl")
        assert rows(info._groups["Fractal"])["Name"] == "pearl" and rows(info._groups["Fractal"])["Entry"] == "#4"
        wait_until(lambda: win.viewport.stats is not None and win.viewport.stats.finished, timeout_ms=60000)
        spin(50)
        assert rows(info._groups["Render"])["Engine"].startswith("CPU")
        win.document.set_view(center=(1.0, 2.0))
        assert rows(info._groups["Fractal"])["Centre"] == "1, 2"
        info.formula_activated.emit("spherical")
        browser = win._formula_browser
        assert browser is not None and browser.isVisible()
        assert browser.tree.currentItem() is not None and browser.tree.currentItem().text(0) == "spherical"
        assert browser.details.toPlainText().startswith("spherical")
        browser.select("no_such_formula")
        assert browser.tree.currentItem() is None and "not available" in browser.details.toPlainText()
        browser.close()
    finally:
        win.gradient_library.document.modified = False
        win.close()
