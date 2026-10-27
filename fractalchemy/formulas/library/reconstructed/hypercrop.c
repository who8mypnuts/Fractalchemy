/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        hypercrop_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from hypercrop_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double hypercrop_n;
    double hypercrop_rad;
    double hypercrop_zero;
    double m_18;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("hypercrop");
APO_VARIABLES(
    VAR_REAL(hypercrop_n, 4.0),
    VAR_REAL(hypercrop_rad, 1.0),
    VAR_REAL(hypercrop_zero, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_18) = 0.15915494309189535 * VAR(hypercrop_n);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = M_PI / VAR(hypercrop_n);
    double t2 = 1.0 / cos(t1);
    double t3 = t2 * (sin(t1) * VAR(hypercrop_rad));
    double t4 = floor(atan2(FTy, FTx) * VAR(m_18)) / VAR(m_18) + t1;
    double t5 = cos(t4) * t2;
    double t6 = FTx - t5;
    double t7 = sin(t4) * t2;
    double t8 = FTy - t7;
    double t9 = atan2(t8, t6);
    double t10 = 0.0 * VVAR + FPz;
    if (t3 <= sqrt(t6 * t6 + t8 * t8)) {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
        FPz = FTz * VVAR + FPz;
    } else {
        if (0.5 > VAR(hypercrop_zero)) {
            FPx = t5 * VVAR + FPx;
            FPy = t7 * VVAR + FPy;
            FPz = t10;
        } else {
            FPx = (cos(t9) * t3 + t5) * VVAR + FPx;
            FPy = (sin(t9) * t3 + t7) * VVAR + FPy;
            FPz = t10;
        }
    }
    return TRUE;
}