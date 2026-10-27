/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        post_curl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from post_curl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double post_curl_c1;
    double post_curl_c2;
    double m_10;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("post_curl");
APO_VARIABLES(
    VAR_REAL(post_curl_c1, 0.0),
    VAR_REAL(post_curl_c2, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = VVAR * VAR(post_curl_c2);
    VAR(m_18) = t1;
    VAR(m_10) = VVAR * VAR(post_curl_c1);
    VAR(m_20) = t1 + t1;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (VAR(m_10) + VAR(m_20) * FPx) * FPy;
    double t2 = VAR(m_10) * FPx + (FPx * FPx - FPy * FPy) * VAR(m_18) + 1.0;
    double t3 = 1.0 / (t1 * t1 + t2 * t2);
    FPx = t3 * (FPy * t1 + t2 * FPx);
    FPy = (FPy * t2 - t1 * FPx) * t3;
    return TRUE;
}