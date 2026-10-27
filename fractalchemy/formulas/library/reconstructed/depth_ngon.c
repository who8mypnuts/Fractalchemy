/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        depth_ngon_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from depth_ngon_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double dn_power;
    double dn_blur;
    double dn_radius;
    double m_18;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("depth_ngon");
APO_VARIABLES(
    VAR_REAL(dn_power, 5.0),
    VAR_REAL(dn_blur, 1.0),
    VAR_REAL(dn_radius, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_18) = M_2PI / VAR(dn_power);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTy * FTy + FTx * FTx);
    double t2 = 2.3406689355471266e-08 * (double)((rand() ^ rand() << 15) & 268435455);
    double t3 = t2 - floor(t2 / VAR(m_18)) * VAR(m_18);
    double t4 = 0.1 * VAR(dn_blur) * (t1 - VAR(dn_radius));
    double t5 = t4 / cos(t3 - VAR(m_18));
    double t6 = cos(t2);
    double t7 = sin(t2);
    double t8 = t4 / cos(t3);
    if (t1 > VAR(dn_radius)) {
        if (t3 <= 0.5 * VAR(m_18)) {
            FPx = (t8 * t6 + FTx) * VVAR + FPx;
            FPy = (t7 * t8 + FTy) * VVAR + FPy;
        } else {
            FPx = (t5 * t6 + FTx) * VVAR + FPx;
            FPy = (t7 * t5 + FTy) * VVAR + FPy;
        }
    } else {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
    }
    return TRUE;
}