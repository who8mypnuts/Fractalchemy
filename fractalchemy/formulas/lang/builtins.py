"""Built-in names of the formula language: math functions, constants and the plugin API."""

from __future__ import annotations

import math

from .nodes import BOOL, FLOAT, INT

# name -> (argument count(s), return type); -1 = variadic
MATH_FUNCTIONS: dict[str, tuple[tuple[int, ...], str]] = {
    "sin": ((1,), FLOAT), "cos": ((1,), FLOAT), "tan": ((1,), FLOAT), "asin": ((1,), FLOAT), "acos": ((1,), FLOAT),
    "atan": ((1, 2), FLOAT), "atan2": ((2,), FLOAT), "sinh": ((1,), FLOAT), "cosh": ((1,), FLOAT), "tanh": ((1,), FLOAT),
    "asinh": ((1,), FLOAT), "acosh": ((1,), FLOAT), "atanh": ((1,), FLOAT), "exp": ((1,), FLOAT), "exp2": ((1,), FLOAT),
    "log": ((1,), FLOAT), "log2": ((1,), FLOAT), "log10": ((1,), FLOAT), "log1p": ((1,), FLOAT), "expm1": ((1,), FLOAT),
    "pow": ((2,), FLOAT), "sqrt": ((1,), FLOAT), "cbrt": ((1,), FLOAT), "hypot": ((2,), FLOAT),
    "fabs": ((1,), FLOAT), "abs": ((1,), "same"), "floor": ((1,), FLOAT), "ceil": ((1,), FLOAT), "round": ((1,), FLOAT),
    "trunc": ((1,), FLOAT), "fmod": ((2,), FLOAT), "fmin": ((2,), FLOAT), "fmax": ((2,), FLOAT), "min": ((2,), "join"),
    "max": ((2,), "join"), "copysign": ((2,), FLOAT), "erf": ((1,), FLOAT), "erfc": ((1,), FLOAT), "sqr": ((1,), FLOAT),
    "sign": ((1,), FLOAT), "lgamma": ((1,), FLOAT), "tgamma": ((1,), FLOAT), "isnan": ((1,), BOOL), "isinf": ((1,), BOOL),
    "random01": ((0,), FLOAT), "rand": ((0,), INT), "labs": ((1,), INT), "llabs": ((1,), INT), "lround": ((1,), INT),
    "lrint": ((1,), INT), "rint": ((1,), FLOAT), "nearbyint": ((1,), FLOAT), "ldexp": ((2,), FLOAT), "frexp": ((2,), FLOAT),
    "fdim": ((2,), FLOAT), "fma": ((3,), FLOAT), "modf": ((2,), FLOAT), "srand": ((1,), INT), "time": ((1,), INT),
    "conj": ((1,), "same"), "norm": ((1,), FLOAT), "arg": ((1,), FLOAT), "creal": ((1,), FLOAT), "cimag": ((1,), FLOAT),
}

# functions that accept a complex argument and return a complex (numpy does these natively; GLSL via c* helpers)
COMPLEX_FUNCTIONS = {"exp", "log", "sqrt", "sin", "cos", "tan", "sinh", "cosh", "tanh", "asin", "acos", "atan", "asinh",
                     "acosh", "atanh", "pow", "conj"}
COMPLEX_TO_REAL = {"creal": "real", "cimag": "imag", "abs": "abs", "norm": "norm", "arg": "arg"}

# two-output helpers from the SDK header: name -> (input count, output names)
OUT_FUNCTIONS = {"fsincos": (1, ("sin", "cos")), "sinhcosh": (1, ("sinh", "cosh"))}

CONSTANTS: dict[str, tuple[float | int, str]] = {
    "M_PI": (math.pi, FLOAT), "M_PI_2": (math.pi / 2, FLOAT), "M_PI_4": (math.pi / 4, FLOAT), "M_1_PI": (1 / math.pi, FLOAT),
    "M_2_PI": (2 / math.pi, FLOAT), "M_2PI": (2 * math.pi, FLOAT), "M_3PI_4": (3 * math.pi / 4, FLOAT),
    "M_E": (math.e, FLOAT), "M_LOG2E": (math.log2(math.e), FLOAT), "M_LOG10E": (math.log10(math.e), FLOAT),
    "M_LN2": (math.log(2), FLOAT), "M_LN10": (math.log(10), FLOAT), "M_2_SQRTPI": (2 / math.sqrt(math.pi), FLOAT),
    "M_SQRT2": (math.sqrt(2), FLOAT), "M_SQRT1_2": (math.sqrt(0.5), FLOAT), "M_SQRT3": (math.sqrt(3), FLOAT),
    "M_SQRT3_2": (math.sqrt(3) / 2, FLOAT), "M_SQRT5": (math.sqrt(5), FLOAT), "M_PHI": ((1 + math.sqrt(5)) / 2, FLOAT),
    "M_1_2PI": (1 / (2 * math.pi), FLOAT), "EPS": (1e-20, FLOAT), "TRUE": (1, INT), "FALSE": (0, INT),
    "DBL_MAX": (1.7976931348623157e308, FLOAT), "DBL_MIN": (2.2250738585072014e-308, FLOAT), "DBL_EPSILON": (2.220446049250313e-16, FLOAT),
    "FLT_MAX": (3.4028234663852886e38, FLOAT), "FLT_MIN": (1.1754943508222875e-38, FLOAT), "FLT_EPSILON": (1.1920929e-07, FLOAT),
    "INT_MAX": (2147483647, INT), "INT_MIN": (-2147483648, INT), "RAND_MAX": (32767, INT), "NULL": (0, INT),
    "LONG_MAX": (2147483647, INT), "LONG_MIN": (-2147483648, INT), "UINT_MAX": (4294967295, INT),
    "HUGE_VAL": (float("inf"), FLOAT), "INFINITY": (float("inf"), FLOAT), "NAN": (float("nan"), FLOAT),
    "true": (1, BOOL), "false": (0, BOOL),
}

# point-state names: FT* is the point after the pre-affine (input), FP* the accumulator (output), TC the colour
STATE_NAMES = ("FTx", "FTy", "FTz", "FPx", "FPy", "FPz", "TC")
AFFINE_NAMES = ("a", "b", "c", "d", "e", "f")
VARIABLE_MACROS = {"VAR_REAL": 2, "VAR_INTEGER": 2, "VAR_REAL_RANGE": 4, "VAR_INTEGER_RANGE": 4, "VAR_INTEGER_NONZERO": 2,
                   "VAR_REAL_CYCLE": 4, "VAR_BOOL": 2, "VAR_REAL_NONZERO": 2}

# C99 float / long-double spellings map onto the double functions
FLOAT_SUFFIX_ALIASES = {f"{name}{suffix}": name for name in MATH_FUNCTIONS for suffix in ("f", "l")
                        if name not in ("rand", "random01", "time", "srand")}
