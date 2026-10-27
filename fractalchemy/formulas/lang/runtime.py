"""Runtime helpers used by the generated numpy code (C semantics on arrays and scalars).

Integer arrays are int32 so hash-style arithmetic wraps exactly as it does in C and GLSL.
"""

from __future__ import annotations

import builtins
import math

import numpy as np

LOOP_LIMIT = 100000   # iterations before a data-dependent loop is abandoned (guards against hangs)


def where(mask, a, b):
    return np.where(mask, a, b)


def any_(mask) -> bool:
    return bool(np.any(mask))


def mask(cond):
    """A condition as a numpy boolean (array or 0-d), so `~` and `&` behave."""
    return np.asarray(cond, dtype=bool)


def wrap32(v: int) -> int:
    """A Python int reduced to a 32-bit two's-complement value (C `int` overflow)."""
    return ((int(v) + 0x80000000) & 0xFFFFFFFF) - 0x80000000


def i32(v):
    """Result of a C int operation: Python ints wrap to 32 bits; int32 arrays already did."""
    if isinstance(v, int):
        return wrap32(v)
    if isinstance(v, np.integer):
        return wrap32(int(v))
    arr = np.asarray(v)
    return arr.astype(np.int32) if arr.dtype != np.int32 and arr.dtype.kind in "iu" else v


def to_int(x):
    """C `(int)` conversion: truncation toward zero."""
    if isinstance(x, (int, np.integer)):
        return wrap32(x)
    if isinstance(x, (float, np.floating, bool, np.bool_)):
        if isinstance(x, (bool, np.bool_)):
            return int(x)
        return int(x) if math.isfinite(x) else 0
    arr = np.asarray(x)
    if arr.dtype.kind in "iub":
        return arr.astype(np.int32)
    with np.errstate(invalid="ignore"):
        clipped = np.clip(np.nan_to_num(np.trunc(arr), nan=0.0, posinf=0.0, neginf=0.0), -2147483648.0, 2147483647.0)
        return clipped.astype(np.int32)


def to_float(x):
    if isinstance(x, (int, float, np.integer, np.floating, bool, np.bool_)):
        return float(x)
    return np.asarray(x, dtype=np.float64)


def to_bool(x):
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, float, np.integer, np.floating)):
        return x != 0
    return np.asarray(x) != 0


def complex(re, im):   # noqa: A001 - the formula language's Complex(a, b)
    if np.ndim(re) or np.ndim(im):
        return np.asarray(re, dtype=np.float64) + 1j * np.asarray(im, dtype=np.float64)
    return np.complex128(builtins.complex(float(re), float(im)))


def to_complex(x):
    if isinstance(x, (int, float, np.integer, np.floating, bool, np.bool_)):
        return np.complex128(float(x))
    return np.asarray(x, dtype=np.complex128)


def cnorm(z):
    return np.real(z) ** 2 + np.imag(z) ** 2


def idiv(a, b):
    """C integer division (truncates toward zero)."""
    if isinstance(a, int):
        a = wrap32(a)
    if isinstance(b, int):
        b = wrap32(b)
    with np.errstate(divide="ignore", invalid="ignore"):
        q = np.trunc(np.asarray(a, dtype=np.float64) / np.asarray(b, dtype=np.float64))
    q = np.nan_to_num(q, nan=0.0, posinf=0.0, neginf=0.0)
    return int(q) if np.ndim(q) == 0 else q.astype(np.int32)


def imod(a, b):
    """C integer remainder (sign follows the dividend)."""
    if isinstance(a, int):
        a = wrap32(a)
    if isinstance(b, int):
        b = wrap32(b)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.fmod(np.asarray(a, dtype=np.int32), np.where(np.asarray(b) == 0, 1, b))
    return int(r) if np.ndim(r) == 0 else r.astype(np.int32)


def fmod(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.fmod(a, b)


def cround(x):
    """C `round`: halves away from zero."""
    return np.sign(x) * np.floor(np.abs(x) + 0.5)


def sign(x):
    return np.sign(x)


def sqr(x):
    return x * x


def cbrt(x):
    return np.cbrt(x)


def erf(x):
    """Abramowitz & Stegun 7.1.26 (|error| < 1.5e-7) — the GLSL side uses the same formula."""
    x = np.asarray(x, dtype=np.float64)
    s = np.sign(x)
    a = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    y = 1.0 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * np.exp(-a * a)
    out = s * y
    return float(out) if out.ndim == 0 else out


def erfc(x):
    return 1.0 - erf(x)


def nested(flat: list, dims: tuple) -> list:
    """A flat list as nested Python lists of the given shape (mutable per-call scratch arrays)."""
    if len(dims) == 1:
        return list(flat[:dims[0]])
    step = 1
    for d in dims[1:]:
        step *= d
    return [nested(flat[i * step:(i + 1) * step], dims[1:]) for i in range(dims[0])]


def gather(table, index):
    """`table[index]` where `index` varies per point; `table` is a list of scalars/arrays."""
    idx = np.clip(np.asarray(index, dtype=np.int64), 0, len(table) - 1)
    if all(np.ndim(t) == 0 for t in table):
        return np.asarray(table, dtype=np.float64 if any(isinstance(t, float) for t in table) else None)[idx]
    stacked = np.stack([np.broadcast_to(np.asarray(t), idx.shape) for t in table])
    return np.take_along_axis(stacked, idx[None, :], axis=0)[0]


def scatter(table, index, value, mask):
    """Masked `table[index] = value` for a per-point index (in place on the list)."""
    idx = np.asarray(index, dtype=np.int64)
    for k in range(len(table)):
        m = idx == k
        if mask is not None:
            m = m & mask
        table[k] = np.where(m, value, table[k])


def lgamma(x):
    return np.vectorize(math.lgamma)(x)


def tgamma(x):
    return np.vectorize(math.gamma)(x)


FUNCS = {
    "sin": np.sin, "cos": np.cos, "tan": np.tan, "asin": np.arcsin, "acos": np.arccos, "atan": np.arctan, "atan2": np.arctan2,
    "sinh": np.sinh, "cosh": np.cosh, "tanh": np.tanh, "asinh": np.arcsinh, "acosh": np.arccosh, "atanh": np.arctanh,
    "exp": np.exp, "exp2": np.exp2, "log": np.log, "log2": np.log2, "log10": np.log10, "log1p": np.log1p, "expm1": np.expm1,
    "pow": np.power, "sqrt": np.sqrt, "cbrt": np.cbrt, "hypot": np.hypot, "fabs": np.abs, "abs": np.abs, "floor": np.floor,
    "ceil": np.ceil, "round": cround, "trunc": np.trunc, "fmod": fmod, "fmin": np.minimum, "fmax": np.maximum,
    "min": np.minimum, "max": np.maximum, "copysign": np.copysign, "erf": erf, "erfc": erfc, "sqr": sqr, "sign": sign,
    "lgamma": lgamma, "tgamma": tgamma, "isnan": np.isnan, "isinf": np.isinf, "labs": np.abs, "llabs": np.abs,
    "lround": lambda x: to_int(cround(x)), "lrint": lambda x: to_int(np.rint(x)), "rint": np.rint, "nearbyint": np.rint,
    "ldexp": np.ldexp, "fdim": lambda a, b: np.maximum(a - b, 0.0), "fma": lambda a, b, c: a * b + c,
}
