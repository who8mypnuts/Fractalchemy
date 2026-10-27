"""Formulas (variations / plugins) for both render engines.

    builtin/   native Python definitions (numpy + GLSL) — the flam3 classics and Apophysis built-ins
    library/   the formula library: Apophysis plugin sources in the C dialect, compiled at start-up
    lang/      the compiler for that dialect

`load_all()` registers everything into `fractal.variations.REGISTRY`; user formulas come from
the folders listed by `loader.user_formula_dirs()`.
"""

from .loader import LoadReport, last_report, load_all, user_formula_dir, user_formula_dirs

__all__ = ["LoadReport", "last_report", "load_all", "user_formula_dir", "user_formula_dirs"]
