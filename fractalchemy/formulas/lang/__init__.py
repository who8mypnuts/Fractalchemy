"""The formula language: Apophysis plugin C, compiled for the numpy and GLSL engines.

    compile_source(text)  →  CompiledFormula (with .variation)

See docs/formulas.md for the supported dialect.
"""

from .compile import Artefacts, CompiledFormula, FormulaError, compile_artefacts, compile_source, variation_from_artefacts
from .glsl_backend import GLSL_PRELUDE

__all__ = ["Artefacts", "CompiledFormula", "FormulaError", "GLSL_PRELUDE", "compile_artefacts", "compile_source",
           "variation_from_artefacts"]
