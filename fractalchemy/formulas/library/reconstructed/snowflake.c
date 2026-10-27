/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        snowflake.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from snowflake.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double snowflake_3;
    double snowflake_c;
    double snowflake_c1;
    double snowflake_c2;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("snowflake");
APO_VARIABLES(
    VAR_REAL(snowflake_3, 3.0),
    VAR_REAL(snowflake_c, 0.5),
    VAR_REAL(snowflake_c1, 1.6),
    VAR_REAL(snowflake_c2, 0.7)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_18) = VAR(snowflake_c) - VAR(snowflake_c1);
    VAR(m_20) = exp((VAR(snowflake_c1) - VAR(snowflake_c)) / ((VAR(snowflake_c1) - VAR(snowflake_c2)) + 1e-20)) / (1.0 / exp(2.0)) + 1e+20;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (VVAR / (FTx * FTx + FTy * FTy + 1e-20)) * ((1.0 - pow(pow(sin(VAR(snowflake_3) * atan2(FTy, FTx)), 2.0), VAR(m_20))) * VAR(m_18) + VAR(snowflake_c));
    FPx = t1 * FTx + FPx;
    FPy = t1 * FTy + FPy;
    return TRUE;
}