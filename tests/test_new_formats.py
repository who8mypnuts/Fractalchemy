"""Ultra Fractal .ufr / .map and Chaotica .chaos support."""

import shutil
import struct
import zlib

import pytest

from fractalchemy.library.catalog import GRADIENT_CATALOG
from fractalchemy.formats import entry_names, format_for, load_gradient, load_gradients, save_gradient
from fractalchemy.formats.ufparams import tokens, unquote, wrap_tokens
from fractalchemy.model import Gradient

RED_BLUE = Gradient.from_colors("red-blue", [(255, 0, 0), (0, 0, 255)])


@pytest.fixture
def flames_dir(samples):
    return samples / "sample flames"


# --- UF parameter text ------------------------------------------------------
def test_tokens_handle_quoted_values_with_spaces():
    body = '  title="111798014" width=600 credits="Stan Ragets;11/22/2016"\r\n  gamma=0.1\r\n'
    pairs = tokens(body)
    assert pairs[0] == ("title", '"111798014"') and unquote(pairs[0][1]) == "111798014"
    assert pairs[2] == ("credits", '"Stan Ragets;11/22/2016"') and pairs[3] == ("gamma", "0.1")


def test_wrap_reproduces_uf_layout():
    body = ("  smooth=yes index=48 color=24831 index=100 color=74 index=198\r\n"
            "  color=12320848 index=249 color=16711680 index=291 color=16736634\r\n"
            "  index=349 color=16777072\r\n")
    assert wrap_tokens(tokens(body), "\r\n") == body


# --- .ufr ---------------------------------------------------------------------
@pytest.mark.parametrize("name", ["111798014.ufr", "brainfibres.ufr"])
def test_ufr_noop_save_is_byte_identical(flames_dir, tmp_path, name):
    path = shutil.copy(flames_dir / name, tmp_path / name)
    original = path.read_bytes()
    for index, gradient in enumerate(load_gradients(path, 0)):
        save_gradient(gradient, path, index)
    assert path.read_bytes() == original


def test_ufr_layers_are_named_entries(flames_dir):
    assert entry_names(flames_dir / "brainfibres.ufr") == ["Layer 2", "Base", "Tenticles"]
    g = load_gradient(flames_dir / "brainfibres.ufr", 1, simplify_tolerance=0)
    assert g.name == "Base" and len(g) == 5


def test_ufr_save_shifts_header_and_keeps_pixel_cache(flames_dir, tmp_path):
    path = shutil.copy(flames_dir / "brainfibres.ufr", tmp_path / "b.ufr")
    before = path.read_bytes()
    info_off, info_len, cache_off = struct.unpack_from("<III", before, 24)
    save_gradient(RED_BLUE, path, index=2)
    after = path.read_bytes()
    delta = len(after) - len(before)
    assert struct.unpack_from("<I", after, 20)[0] == struct.unpack_from("<I", before, 20)[0] + delta
    new_info_off, new_info_len, new_cache_off = struct.unpack_from("<III", after, 24)
    assert (new_info_off, new_info_len, new_cache_off) == (info_off + delta, info_len, cache_off + delta)
    assert after[new_info_off:] == before[info_off:]                   # binary tail untouched
    zlib.decompressobj().decompress(after[new_cache_off:new_cache_off + 4096])  # still a valid stream
    reloaded = load_gradients(path, 0)
    assert reloaded[2].stops[0].color == (255, 0, 0) and reloaded[2].name == "Tenticles"
    assert reloaded[1].stops == load_gradients(flames_dir / "brainfibres.ufr", 0)[1].stops
    assert b"rotation=1" in after  # non-stop attributes of the layer gradient survive


def test_ufr_rename_changes_layer_caption(flames_dir, tmp_path):
    path = shutil.copy(flames_dir / "brainfibres.ufr", tmp_path / "b.ufr")
    format_for(path).rename(path, 1, "Sea floor")
    assert entry_names(path) == ["Layer 2", "Sea floor", "Tenticles"]


def test_ufr_rejects_append_and_remove(flames_dir, tmp_path):
    from fractalchemy.library import operations as ops

    fmt = format_for(flames_dir / "brainfibres.ufr")
    assert fmt.can_save and not fmt.can_append and not fmt.can_remove and not fmt.can_create
    path = shutil.copy(flames_dir / "brainfibres.ufr", tmp_path / "b.ufr")
    with pytest.raises(ValueError):
        ops.delete_entry(GRADIENT_CATALOG, path, 0)
    with pytest.raises(ValueError):
        ops.transfer_entry(GRADIENT_CATALOG, flames_dir / "candy.flame", 0, path, move=False)


# --- .map ---------------------------------------------------------------------
def test_map_round_trip(flames_dir, tmp_path):
    src = flames_dir / "kasane_haru_hazakura.map"
    original = load_gradient(src, simplify_tolerance=0)
    assert len(original) == 256 and original.stops[0].color == (169, 207, 83)
    out = tmp_path / "out.map"
    save_gradient(original, out)
    assert load_gradient(out, simplify_tolerance=0).stops == original.stops
    assert out.read_text().splitlines()[1] == "169 206  83"


# --- .chaos -------------------------------------------------------------------
def test_chaos_loads_palette_named_after_ifs(flames_dir):
    assert entry_names(flames_dir / "tatasz_tram_rails.chaos") == ["Rram rails by tatasz"]
    g = load_gradient(flames_dir / "satania_spikobius.chaos", simplify_tolerance=0)
    assert len(g) == 256 and g.stops[0].color == (28, 28, 28)


def test_chaos_save_replaces_palette_only(flames_dir, tmp_path):
    path = shutil.copy(flames_dir / "tatasz_tram_rails.chaos", tmp_path / "t.chaos")
    before = path.read_bytes()
    save_gradient(RED_BLUE, path)
    after = path.read_bytes()
    g = load_gradient(path, simplify_tolerance=0)
    assert g.stops[0].color == (255, 0, 0) and g.stops[-1].color == (0, 0, 255) and len(g) == 256
    assert after.count(b"<iterator") == before.count(b"<iterator")
    assert b"\r\n" in after and after[:200] == before[:200]
    format_for(path).rename(path, 0, "Tram & rails")
    assert entry_names(path) == ["Tram & rails"]
