/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Half_Julian.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Half_Julian.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double half_julian_power;
    double half_julian_dist;
    double m_10;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("Half_Julian");
APO_VARIABLES(
    VAR_REAL(half_julian_power, -2.0),
    VAR_REAL(half_julian_dist, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = VAR(half_julian_dist) / VAR(half_julian_power);
    VAR(m_18) = t1;
    VAR(m_20) = M_2PI / VAR(half_julian_power);
    VAR(m_10) = t1 / 2.0;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = pow(FTy * FTy + FTx * FTx, VAR(m_10)) * VVAR;
    double t2 = atan2(FTy, FTx) * VAR(m_18) + VAR(m_20);
    FPx = t1 * cos(t2) + FPx;
    FPy = t1 * sin(t2) + FPy;
    return TRUE;
}