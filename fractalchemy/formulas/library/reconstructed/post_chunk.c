/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        post_chunk.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from post_chunk.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double post_chunk_a;
    double post_chunk_b;
    double post_chunk_c;
    double post_chunk_d;
    double post_chunk_e;
    double post_chunk_f;
    int post_chunk_mode;
    double m_38;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("post_chunk");
APO_VARIABLES(
    VAR_REAL(post_chunk_a, 1.0),
    VAR_REAL(post_chunk_b, 0.0),
    VAR_REAL(post_chunk_c, 1.0),
    VAR_REAL(post_chunk_d, 0.0),
    VAR_REAL(post_chunk_e, 0.0),
    VAR_REAL(post_chunk_f, -1.0),
    VAR_INTEGER(post_chunk_mode, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_38) = VAR(post_chunk_f) * VVAR;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    if (VAR(post_chunk_mode) != 0) {
        if (VAR(post_chunk_mode) - 1 != 0) {
        } else {
            if (!(FPy * (VAR(post_chunk_b) * FPx + VAR(post_chunk_e)) + (FPx * VAR(post_chunk_d) + VAR(m_38)) + FPx * FPx * VAR(post_chunk_a) + FPy * FPy * VAR(post_chunk_c) > 0.0)) {
                FPx = 0.0;
                FPy = 0.0;
            } else {
            }
        }
    } else {
        if (!(FPy * (VAR(post_chunk_b) * FPx + VAR(post_chunk_e)) + (FPx * VAR(post_chunk_d) + VAR(m_38)) + FPx * FPx * VAR(post_chunk_a) + FPy * FPy * VAR(post_chunk_c) > 0.0)) {
        } else {
            FPx = 0.0;
            FPy = 0.0;
        }
    }
    return TRUE;
}