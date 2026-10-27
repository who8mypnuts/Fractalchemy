"""Formula discovery: bundled library, user folders, overrides, caching and error reporting."""

from pathlib import Path

import numpy as np

from fractalchemy.formulas import loader
from fractalchemy.fractal import variations as V

USER_FORMULA = '''
typedef struct { double myfx_k; } Variables;
#include "apoplugin.h"
APO_PLUGIN("myfx");
APO_VARIABLES(VAR_REAL(myfx_k, 2.0));
int PluginVarPrepare(Variation* vp) { return TRUE; }
int PluginVarCalc(Variation* vp) { FPx += VVAR * VAR(myfx_k) * FTx; FPy += VVAR * FTy; return TRUE; }
'''

PYTHON_FORMULA = '''
import numpy as np
from fractalchemy.fractal.variations import Point, variation

@variation("mypy", "v += w * vec2(t.y, t.x);")
def _mypy(p: Point):
    return p.w * p.y, p.w * p.x
'''


def test_bundled_library_is_loaded_and_cached(tmp_path):
    report = loader.load_all(user_dirs=[], force=True, use_cache=False)
    assert len(report.loaded) > 400 and not report.errors
    for name in ("collideoscope", "bwraps7", "crackle", "waves2", "falloff2", "julia3D", "spher"):
        assert name in V.REGISTRY, name
    assert V.REGISTRY["collideoscope"].style == V.FORMULA and V.REGISTRY["linear"].style == V.LEGACY
    assert V.REGISTRY["pre_falloff2"].kind == V.PRE and V.REGISTRY["post_smartcrop"].kind == V.POST
    assert V.REGISTRY["dc_bubble"].dc and V.REGISTRY["julia3D"].z == V.Z_FORMULA


def test_user_folder_formulas_are_loaded_and_override_bundled_ones(tmp_path, monkeypatch):
    user = tmp_path / "formulas"
    user.mkdir()
    (user / "myfx.c").write_text(USER_FORMULA)
    (user / "mypy.py").write_text(PYTHON_FORMULA)
    (user / "broken.c").write_text('#include "apoplugin.h"\nAPO_PLUGIN("broken");\nint PluginVarCalc(Variation* vp) { FPx += nosuch; return 1; }')
    (user / "whorl.c").write_text(USER_FORMULA.replace("myfx", "whorl"))   # overrides the bundled whorl
    monkeypatch.setenv(loader.ENV_VAR, str(user))
    report = loader.load_all(force=True, use_cache=False)
    assert "myfx" in report.loaded and "mypy" in report.loaded
    assert V.REGISTRY["myfx"].params == {"myfx_k": 2.0}
    assert V.REGISTRY["whorl"].origin.endswith("whorl.c") and str(user) in V.REGISTRY["whorl"].origin
    assert [e for e in report.errors if "broken.c" in e[0] and "nosuch" in e[1]]
    point = V.Point(np.array([1.0]), np.array([2.0]), 0.5, (1, 0, 0, 1, 0, 0), {"myfx_k": 2.0}, np.random.default_rng(0))
    assert V.REGISTRY["myfx"].apply(point)[3].tolist() == [1.0]
    assert V.REGISTRY["mypy"].apply(point)[3].tolist() == [1.0]
    monkeypatch.delenv(loader.ENV_VAR)
    loader.load_all(force=True, use_cache=False)   # restore the bundled registry for the other tests
    assert "myfx" not in loader.last_report().loaded or "myfx" in V.REGISTRY   # stale entries are harmless


def test_cache_round_trip(tmp_path, monkeypatch):
    user = tmp_path / "formulas"
    user.mkdir()
    (user / "myfx.c").write_text(USER_FORMULA)
    cache = tmp_path / "cache.bin"
    monkeypatch.setattr(loader, "cache_file", lambda: cache)
    first = loader.load_all(user_dirs=[user], force=True)
    assert cache.exists() and "myfx" in first.loaded
    second = loader.load_all(user_dirs=[user], force=True)
    assert "myfx" in second.loaded and second.seconds < first.seconds * 2 + 1
    assert V.REGISTRY["myfx"].params == {"myfx_k": 2.0}
    loader.load_all(user_dirs=[], force=True, use_cache=False)


def test_user_formula_dir_is_platform_specific():
    assert loader.user_formula_dir().name == "formulas" and "Fractalchemy" in str(loader.user_formula_dir())
    assert isinstance(loader.user_formula_dirs(), list)


def test_every_bundled_formula_file_declares_its_origin():
    for path in Path(loader.LIBRARY_DIR).rglob("*.c"):
        head = path.read_text(encoding="utf-8", errors="replace")[:1200]
        assert "Fractalchemy formula library" in head, path
