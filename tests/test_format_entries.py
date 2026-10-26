"""Multi-entry editing: append / remove / rename / save(index) / copy_entry."""

import shutil

import pytest

from fractalchemy.formats import entry_names, format_for, load_gradients, save_gradient
from fractalchemy.model import Gradient

RED_BLUE = Gradient.from_colors("red-blue", [(255, 0, 0), (0, 0, 255)])


@pytest.fixture
def ugr(samples, tmp_path):
    return shutil.copy(samples / "sample gradients" / "ag6.ugr", tmp_path / "ag6.ugr")


@pytest.fixture
def flames(samples, tmp_path):
    return shutil.copy(samples / "sample flames" / "candy.flame", tmp_path / "candy.flame")


@pytest.fixture
def bare_flame(samples, tmp_path):
    return shutil.copy(samples / "sample flames" / "69e8n5w1.flame", tmp_path / "bare.flame")


# --- names ------------------------------------------------------------------
def test_entry_names_are_cheap_and_in_order(samples):
    assert entry_names(samples / "sample gradients" / "ag6.ugr")[:3] == ["001", "002", "003"]
    assert entry_names(samples / "sample flames" / "candy.flame")[:2] == ["original", "outlined"]
    assert entry_names(samples / "sample images" / "idaho-001.png") == ["idaho-001"]


# --- UGR --------------------------------------------------------------------
def test_ugr_append_remove_rename_preserve_other_blocks(ugr):
    fmt = format_for(ugr)
    original = ugr.read_bytes()
    count = len(entry_names(ugr))
    fmt.append(RED_BLUE, ugr)
    assert entry_names(ugr)[-1] == "red-blue" and len(entry_names(ugr)) == count + 1
    assert ugr.read_bytes().startswith(original)  # nothing before the new block changed

    fmt.remove(ugr, count)
    assert ugr.read_bytes() == original  # append + remove is a no-op

    fmt.remove(ugr, 0)
    assert entry_names(ugr)[0] == "002" and len(entry_names(ugr)) == count - 1
    assert ugr.read_bytes() == original[original.index(b"002 {"):]

    fmt.rename(ugr, 0, "renamed")
    assert entry_names(ugr)[0] == "renamed"
    assert ugr.read_bytes().startswith(b'renamed {\r\ngradient:\r\n title="renamed"')


def test_ugr_save_by_index_replaces_only_that_entry(ugr):
    before = load_gradients(ugr, 0)
    save_gradient(RED_BLUE, ugr, index=2)
    after = load_gradients(ugr, 0)
    assert after[2].name == "red-blue" and after[2].stops[0].color == (255, 0, 0)
    assert [g.name for g in after[:2]] == [g.name for g in before[:2]]
    assert [g.name for g in after[3:]] == [g.name for g in before[3:]]


def test_ugr_copy_entry_is_verbatim(ugr, tmp_path):
    fmt = format_for(ugr)
    target = tmp_path / "new.ugr"
    fmt.copy_entry(ugr, 1, target)
    fmt.copy_entry(ugr, 1, target)
    assert entry_names(target) == ["002", "002"]
    block = ugr.read_bytes().split(b"002 {")[1].split(b"}")[0]
    assert target.read_bytes().count(block) == 2
    assert load_gradients(target, 0)[0].stops == load_gradients(ugr, 0)[1].stops


# --- Flame ------------------------------------------------------------------
def test_flame_append_remove_rename_preserve_other_flames(flames):
    fmt = format_for(flames)
    original = flames.read_bytes()
    fmt.append(RED_BLUE, flames)
    names = entry_names(flames)
    assert names[-1] == "red-blue" and len(names) == 6
    assert flames.read_bytes().endswith(b"</flame>\r\n</Flames>\r\n")

    fmt.remove(flames, 5)
    assert flames.read_bytes() == original

    fmt.rename(flames, 1, "out & about")
    assert entry_names(flames)[1] == "out & about"
    fmt.remove(flames, 0)
    assert entry_names(flames)[0] == "out & about"
    assert b"<xform" in flames.read_bytes()


def test_flame_save_by_index(flames):
    save_gradient(RED_BLUE, flames, index=3)
    after = load_gradients(flames, 0)
    assert after[3].stops[0].color == (255, 0, 0) and after[2].stops[0].color != (255, 0, 0)
    assert entry_names(flames)[3] != "red-blue"  # save keeps the flame's own name


def test_bare_flame_is_wrapped_when_a_second_entry_is_added(bare_flame):
    fmt = format_for(bare_flame)
    fmt.append(RED_BLUE, bare_flame)
    assert entry_names(bare_flame) == ["Apo3D-181008-2", "red-blue"]
    text = bare_flame.read_text()
    assert text.startswith('<Flames name="bare">') and text.rstrip().endswith("</Flames>")
    fmt.remove(bare_flame, 0)
    assert entry_names(bare_flame) == ["red-blue"]


def test_flame_copy_entry_keeps_xforms(flames, tmp_path):
    fmt = format_for(flames)
    target = tmp_path / "copy.flame"
    fmt.copy_entry(flames, 1, target)
    text = target.read_text()
    assert 'name="outlined"' in text and text.count("<xform") == 6
    assert entry_names(target) == ["outlined"]


def test_cross_format_transfer_goes_through_gradient(flames, tmp_path):
    target = tmp_path / "t.ugr"
    g = load_gradients(flames)[0]
    format_for(target).append(g, target)
    assert entry_names(target) == ["original"]
