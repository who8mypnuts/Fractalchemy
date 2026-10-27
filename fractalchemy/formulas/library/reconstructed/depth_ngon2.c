/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        depth_ngon2_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from depth_ngon2_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double dn2_power;
    double dn2_blur;
    double dn2_radius;
    double dn2_x0;
    double dn2_y0;
    double dn2_mulx;
    double dn2_muly;
    double dn2_exp;
    double m_40;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("depth_ngon2");
APO_VARIABLES(
    VAR_REAL(dn2_power, 5.0),
    VAR_REAL(dn2_blur, 1.0),
    VAR_REAL(dn2_radius, 1.0),
    VAR_REAL(dn2_x0, 0.0),
    VAR_REAL(dn2_y0, 0.0),
    VAR_REAL(dn2_mulx, 1.0),
    VAR_REAL(dn2_muly, 1.0),
    VAR_REAL(dn2_exp, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_40) = M_2PI / VAR(dn2_power);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (FTx - VAR(dn2_x0)) / VAR(dn2_mulx);
    double t2 = (FTy - VAR(dn2_y0)) / VAR(dn2_muly);
    double t3 = sqrt(t1 * t1 + t2 * t2);
    double t4 = 2.3406689355471266e-08 * (double)((rand() ^ rand() << 15) & 268435455);
    double t5 = t4 - floor(t4 / VAR(m_40)) * VAR(m_40);
    double t6 = 0.1 * (exp(log(t3 - VAR(dn2_radius)) * VAR(dn2_exp)) * VAR(dn2_blur));
    double t7 = t6 / cos(t5 - VAR(m_40));
    double t8 = cos(t4);
    double t9 = sin(t4);
    double t10 = t6 / cos(t5);
    if (t3 > VAR(dn2_radius)) {
        if (t5 <= 0.5 * VAR(m_40)) {
            FPx = (t10 * t8 + FTx) * VVAR + FPx;
            FPy = (t9 * t10 + FTy) * VVAR + FPy;
        } else {
            FPx = (t7 * t8 + FTx) * VVAR + FPx;
            FPy = (t9 * t7 + FTy) * VVAR + FPy;
        }
    } else {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
    }
    return TRUE;
}