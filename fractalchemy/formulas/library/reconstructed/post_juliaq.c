/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        post_juliaq.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from post_juliaq.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int post_juliaq_power;
    int post_juliaq_divisor;
    double m_10;
    double m_18;
    double m_8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("post_juliaq");
APO_VARIABLES(
    VAR_INTEGER(post_juliaq_power, 3),
    VAR_INTEGER_NONZERO(post_juliaq_divisor, 2)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = 1.0 / (double)VAR(post_juliaq_power);
    VAR(m_10) = (double)VAR(post_juliaq_divisor) * t1;
    VAR(m_8) = 0.5 * (double)VAR(post_juliaq_divisor) * t1;
    VAR(m_18) = M_2PI * t1;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan2(FPy, FPx) * VAR(m_10) + VAR(m_18) * (double)rand();
    double t2 = pow(FPx * FPx + FPy * FPy, VAR(m_8)) * VVAR;
    FPx = cos(t1) * t2;
    FPy = t2 * sin(t1);
    return TRUE;
}