"""Fragment files: the .fafrag metadata block, parameter files, screenshots, templates and the library pane."""

from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QImage

from fractalchemy.fragments.document_format import (FragmentFormatError, FragmentMetadata, join_metadata, read_fragment,
                                                    read_parameters, split_metadata, write_fragment, write_parameters)
from fractalchemy.fragments.examples import EXAMPLES_DIR
from fractalchemy.fragments.files import FileManager
from fractalchemy.fragments.library_format import FragmentFormat, is_bundled_path
from fractalchemy.fragments.preprocessor import Preprocessor
from fractalchemy.fragments.templates import BUILTIN_TEMPLATES, save_user_template, user_templates
from fractalchemy.library.catalog import FRAGMENT_CATALOG
from fractalchemy.render.output import read_embedded_parameters
from fractalchemy.ui.fragments import FragmentsWindow
from fractalchemy.ui.fragments.file_actions import is_bundled, qimage_to_rgba16

from .conftest import wait_until

SOURCE = "#include \"MathUtils.frag\"\nfloat DE(vec3 p) { return length(p) - 1.0; }\n#preset Default\nFOV = 0.4\n#endpreset\n"


def test_metadata_block_round_trips_and_fragm_sees_a_comment(tmp_path):
    metadata = FragmentMetadata(render={"tiles": 2, "subframes": 200}, library={"tags": ["mandelbulb"]})
    metadata.set_thumbnail_png(b"\x89PNG fake */ bytes")
    text = join_metadata(SOURCE, metadata)
    assert text.startswith(SOURCE.rstrip("\n")) and "/*[fractalchemy]" in text and "[/fractalchemy]*/" in text
    body, parsed = split_metadata(text)
    assert body.strip() == SOURCE.strip() and parsed.render == {"tiles": 2, "subframes": 200} and parsed.library["tags"] == ["mandelbulb"]
    assert parsed.thumbnail_png == b"\x89PNG fake */ bytes"
    # the preprocessor (FragM's rules) sees the same presets and parameters with or without the block
    with_block = Preprocessor(FileManager()).parse(text, None)
    without = Preprocessor(FileManager()).parse(SOURCE, None)
    assert with_block.presets == without.presets and [p.name for p in with_block.params] == [p.name for p in without.params]
    assert join_metadata(text, None).strip() == SOURCE.strip()                # dropping the block
    assert join_metadata(SOURCE, FragmentMetadata()) == SOURCE                 # empty metadata writes nothing
    with pytest.raises(FragmentFormatError):
        split_metadata(SOURCE + "/*[fractalchemy]\n{not json\n[/fractalchemy]*/\n")


def test_write_fragment_keeps_the_block_for_fafrag_only(tmp_path):
    metadata = FragmentMetadata(animation={"fps": 30})
    write_fragment(tmp_path / "a.fafrag", SOURCE, metadata)
    write_fragment(tmp_path / "a.frag", SOURCE, metadata)
    assert read_fragment(tmp_path / "a.fafrag")[1].animation == {"fps": 30}
    assert read_fragment(tmp_path / "a.frag") == (SOURCE, None)
    write_parameters(tmp_path / "p.fragparams", "FOV = 0.5\n")
    assert read_parameters(tmp_path / "p.fragparams") == "FOV = 0.5\n"


def test_library_format_and_bundled_rule(tmp_path):
    fmt = FragmentFormat()
    source = EXAMPLES_DIR / "Historical 3D Fractals" / "Mandelbulb.frag"
    assert fmt.names(source) == ["Mandelbulb"] and not fmt.multi_entry and FRAGMENT_CATALOG.matches(source)
    fmt.copy_entry(source, 0, tmp_path / "copy.fafrag")
    assert (tmp_path / "copy.fafrag").read_text() == source.read_text()
    assert is_bundled_path(source) and is_bundled(source) and not is_bundled(tmp_path / "copy.fafrag")
    with pytest.raises(ValueError):
        fmt.copy_entry(tmp_path / "copy.fafrag", 0, source.parent / "x.frag")
    with pytest.raises(ValueError):
        fmt.remove(source, 0)


def test_user_templates_round_trip(tmp_path):
    path = save_user_template("My / Menger", BUILTIN_TEMPLATES[2].text, tmp_path)
    assert path.name == "My _ Menger.fafrag"
    mine = user_templates(tmp_path)
    assert [t.name for t in mine] == ["My _ Menger"] and mine[0].kind == "3D"


def test_qimage_conversion_and_embedded_parameters(tmp_path):
    image = QImage(4, 3, QImage.Format.Format_RGBA8888)
    image.fill(0xFF336699)
    array = qimage_to_rgba16(image)
    assert array.shape == (3, 4, 4) and array.dtype == np.uint16 and array[0, 0, 3] == 65535
    from fractalchemy.render.output import SaveOptions, output_format, save_image
    save_image(array, tmp_path / "shot.png", output_format("png"), SaveOptions(parameters="FOV = 0.4", parameters_key="frAg"))
    assert read_embedded_parameters(tmp_path / "shot.png", "frAg") == "FOV = 0.4"
    assert read_parameters(tmp_path / "shot.png") == "FOV = 0.4"
    with pytest.raises(FragmentFormatError):
        image.save(str(tmp_path / "plain.png"))
        read_parameters(tmp_path / "plain.png")


@pytest.fixture
def window(qapp, tmp_path):
    settings = QSettings(str(tmp_path / "fragments.ini"), QSettings.Format.IniFormat)
    win = FragmentsWindow(None, settings)
    win.resize(1000, 640)
    win.show()
    wait_until(lambda: win._capabilities is not None, 30000)
    yield win
    for tab in win.tabs.tabs:
        tab.document._modified = False
    win.shutdown()
    win.close()


def test_save_load_fafrag_with_metadata_and_session(window, tmp_path):
    document = window.open_text(SOURCE)
    document.metadata.render["tiles"] = 3
    path = tmp_path / "shell.fafrag"
    assert window.files._write(document, path)
    assert "/*[fractalchemy]" in path.read_text() and not document.modified
    window.tabs.close_tab(0, ask=False)
    reopened = window.files.open_path(path)
    assert reopened.metadata.render == {"tiles": 3} and reopened.text.strip() == SOURCE.strip()
    window.save_state()
    assert window._settings.value("fragments/open_files") == [str(path)]
    # a second window restores the tab
    other = FragmentsWindow(None, window._settings)
    try:
        assert [t.document.path for t in other.tabs.tabs] == [path]
    finally:
        other.shutdown()
        other.close()


def test_parameter_files_and_screenshot(window, tmp_path):
    window.open_path(EXAMPLES_DIR / "Historical 3D Fractals" / "Mandelbulb.frag")
    document = window.tabs.document
    wait_until(lambda: window.viewport.image is not None, 60000)
    params = tmp_path / "p.fragparams"
    write_parameters(params, "Power = 3\n")
    assert window.files.load_parameters(params) and document.state.get("Power") == 3.0
    from fractalchemy.render.output import SaveOptions, output_format, save_image
    shot = tmp_path / "shot.png"
    save_image(qimage_to_rgba16(window.viewport.image), shot, output_format("png"),
               SaveOptions(parameters=document.state.to_text(), parameters_key="frAg"))
    document.set_value("Power", 5.0)
    assert window.files.load_parameters(shot) and document.state.get("Power") == 3.0
    # drops: a .fragparams applies, a .frag opens
    from PySide6.QtCore import QMimeData, QPointF, QUrl, Qt
    from PySide6.QtGui import QDropEvent
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(tmp_path / "other.frag"))])
    (tmp_path / "other.frag").write_text(SOURCE)
    window.dropEvent(QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert window.tabs.document.path == tmp_path / "other.frag"


def test_library_pane_lists_the_examples_and_refuses_to_change_them(window, tmp_path):
    wait_until(lambda: window.library_panel.model.rowCount() >= 1 and not window.library._pending, 30000)
    assert window.library_panel.model.root_paths()[0] == EXAMPLES_DIR
    entries = window.library_panel.model.entries()
    mandelbulb = next(i for i in entries if i.path.name == "Mandelbulb.frag")
    failures = []
    window.library.status.connect(failures.append)
    window.library.delete([mandelbulb])
    window.library.rename(mandelbulb, "x.frag")
    window.library.remove_root(EXAMPLES_DIR)
    assert len(failures) == 3 and mandelbulb.path.is_file()
    window.open_item(mandelbulb)
    assert window.tabs.document.path == mandelbulb.path
    window.library_panel.set_thumbnail_view(True)
    assert window.thumbnails._enabled
    icon = window.thumbnails.icon_for(mandelbulb)
    assert icon is not None
    wait_until(lambda: window.thumbnails.cached(mandelbulb) is not None, 90000)
    assert not window.thumbnails.cached(mandelbulb).isNull()
    assert (Path(window.thumbnails._disk).exists())
