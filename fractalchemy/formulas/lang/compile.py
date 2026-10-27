"""Source text → `Variation`: the formula compiler's front door.

Compilation produces *artefacts* — the generated numpy source, the GLSL, and the metadata —
which are plain data, so the loader can cache them on disk and rebuild a `Variation`
without parsing the source again (`variation_from_artefacts`).
"""

from __future__ import annotations

import marshal
from dataclasses import asdict, dataclass

import numpy as np

from ...fractal.variations import FORMULA, Z_FORMULA, Z_NONE, ParamInfo, Point, Variation
from . import glsl_backend, numpy_backend
from . import runtime as _rt
from .lexer import LexError
from .parser import ParseError, parse
from .preprocess import PreprocessError, preprocess
from .semantic import PluginSpec, SemanticError, analyze

CACHE_VERSION = 11   # bump when generated code changes shape, so stale caches are ignored


class FormulaError(ValueError):
    """The source could not be compiled; `str(exc)` says why."""


@dataclass
class Artefacts:
    """Everything needed to rebuild a Variation, as picklable data."""
    name: str
    numpy_source: str
    glsl_decls: str
    glsl_body: str
    params: dict[str, float]
    param_info: list[dict]
    derived: list[str]
    kind: str
    writes_z: bool
    writes_color: bool
    uses_affine: bool
    uses_random: bool
    warnings: list[str]
    const_globals: list[tuple[str, str, list[int], object]]
    version: int = CACHE_VERSION
    numpy_code: bytes = b""      # marshalled code object of `numpy_source` (skips Python's slow compile step)


@dataclass
class CompiledFormula:
    """The outcome of compiling one source: the Variation plus the generated code (for inspection)."""
    spec: PluginSpec
    variation: Variation
    artefacts: Artefacts

    @property
    def numpy_source(self) -> str:
        return self.artefacts.numpy_source


def compile_artefacts(text: str, origin: str = "", include_dir=None) -> tuple[PluginSpec, Artefacts]:
    """Parse, analyse and generate code; raises FormulaError.

    `include_dir` resolves `#include "file"` lines (shared helper sources next to the formula).
    """
    try:
        spec = analyze(parse(preprocess(text, include_dir=include_dir)))
        numpy_source = numpy_backend.emit_module(spec)
        decls, body = glsl_backend.emit(spec)
    except (PreprocessError, LexError, ParseError, SemanticError) as exc:
        raise FormulaError(f"{origin or 'formula'}: {exc}") from exc
    info = [asdict(ParamInfo(v.name, v.type, v.default, v.min, v.max, v.cyclic, v.nonzero)) for v in spec.variables]
    art = Artefacts(
        name=spec.name, numpy_source=numpy_source, glsl_decls=decls, glsl_body=body,
        params={v.name: v.default for v in spec.variables}, param_info=info, derived=list(spec.derived),
        kind=spec.kind, writes_z=spec.writes_z, writes_color=spec.writes_color, uses_affine=spec.uses_affine,
        uses_random=spec.uses_random, warnings=list(spec.warnings), const_globals=list(spec.const_globals),
    )
    return spec, art


def compile_source(text: str, origin: str = "", include_dir=None) -> CompiledFormula:
    """Compile formula source (Apophysis plugin C dialect) for both engines.

    Args:
        text: The source.
        origin: Where it came from, for messages and the registry.
        include_dir: Folder that `#include "file"` lines are resolved against.

    Raises:
        FormulaError: On any preprocessing, parse, analysis or code-generation problem.
    """
    spec, art = compile_artefacts(text, origin, include_dir)
    return CompiledFormula(spec, variation_from_artefacts(art, origin), art)


def variation_from_artefacts(art: Artefacts, origin: str = "") -> Variation:
    """Build the runtime Variation (executes the generated numpy module)."""
    namespace = {
        "np": np, "_rt": _rt, "_F": _rt.FUNCS,
        "_G": {n: (np.asarray(v) if d else v) for n, t, d, v in art.const_globals},
    }
    try:
        code = marshal.loads(art.numpy_code) if art.numpy_code else None
    except Exception:  # noqa: BLE001 - stale marshal data: recompile from source
        code = None
    if code is None:
        try:
            code = compile(art.numpy_source, f"<formula {art.name}>", "exec")
        except SyntaxError as exc:
            raise FormulaError(f"{origin or art.name}: generated code failed to compile: {exc}") from exc
        art.numpy_code = marshal.dumps(code)
    exec(code, namespace)   # noqa: S102 - our own generated code
    calc, prepare = namespace["calc"], namespace.get("prepare")

    def numpy_fn(p: Point):
        with np.errstate(all="ignore"):
            out = calc(p.x, p.y, p.z, p.px, p.py, p.pz, p.c, p.w, *p.coefs, p.params, p.rng)
        n = p.x.shape[0]
        return tuple(_as_array(o, n) for o in out)

    prepare_fn = _prepare_wrapper(prepare) if prepare is not None and art.derived else None
    info = {d["name"]: ParamInfo(**d) for d in art.param_info}
    tables = {n: [float(x) for x in np.asarray(v, dtype=np.float64).reshape(-1)] for n, t, d, v in art.const_globals if d}
    return Variation(
        name=art.name, numpy=numpy_fn, glsl=art.glsl_body, params=dict(art.params), random=art.uses_random,
        uses_affine=art.uses_affine, note="; ".join(w for w in art.warnings if w.startswith("stateful")), kind=art.kind,
        z=Z_FORMULA if art.writes_z else Z_NONE, dc=art.writes_color, style=FORMULA, glsl_decls=art.glsl_decls,
        prepare=prepare_fn, param_info=info, origin=origin, tables=tables,
    )


def _prepare_wrapper(prepare):
    def prepare_fn(params: dict[str, float], weight: float, coefs, rng: np.random.Generator) -> dict[str, float]:
        with np.errstate(all="ignore"):
            derived = prepare(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, weight, *coefs, dict(params), rng)
        return {k: _scalar(v) for k, v in derived.items()}
    return prepare_fn


def _as_array(value, n: int) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (n,):
        arr = np.broadcast_to(arr, (n,)).copy()
    return arr


def _scalar(value):
    arr = np.asarray(value)
    if arr.ndim:   # a lookup table: flattened list, as the parameter texture will hold it
        return [float(v) for v in arr.reshape(-1)]
    if arr.dtype.kind in "iub":
        return int(arr)
    return float(arr)



