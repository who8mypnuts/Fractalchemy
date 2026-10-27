/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        depth_blur2_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from depth_blur2_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double db2_power;
    double db2_range;
    double db2_blur;
    double db2_radius;
    double db2_x0;
    double db2_y0;
    double db2_mulx;
    double db2_muly;
    double db2_exp;
    double m_48;
    double m_50;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("depth_blur2");
APO_VARIABLES(
    VAR_REAL(db2_power, 5.0),
    VAR_REAL(db2_range, 0.401623),
    VAR_REAL(db2_blur, 1.0),
    VAR_REAL(db2_radius, 1.0),
    VAR_REAL(db2_x0, 0.0),
    VAR_REAL(db2_y0, 0.0),
    VAR_REAL(db2_mulx, 1.0),
    VAR_REAL(db2_muly, 1.0),
    VAR_REAL(db2_exp, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_PI / VAR(db2_power);
    double t2 = sqrt(VAR(db2_range) * VAR(db2_range) + 1.0 - (VAR(db2_range) + VAR(db2_range)) * cos(t1));
    VAR(m_50) = t2;
    VAR(m_48) = asin(sin(t1) * VAR(db2_range) / t2);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (FTx - VAR(db2_x0)) / VAR(db2_mulx);
    double t2 = (FTy - VAR(db2_y0)) / VAR(db2_muly);
    double t3 = sqrt(t1 * t1 + t2 * t2);
    double t4 = (double)((rand() ^ rand() << 15) & 268435455) * (7.450580624679404e-09 * VAR(db2_power));
    double t5 = trunc(t4);
    double t6 = (t4 - t5) * VAR(m_50);
    double t7 = cos(VAR(m_48));
    double t8 = sqrt(t6 * t6 + 1.0 - (t7 + t7) * t6);
    double t9 = exp(log(t3 - VAR(db2_radius)) * VAR(db2_exp)) * (0.1 * (t8 * VAR(db2_blur)) * sqrt(random01()));
    double t10 = (double)((int)t5 + ((int)t5 >> 31) >> 1) * (M_2PI / VAR(db2_power));
    double t11 = asin(sin(VAR(m_48)) * t6 / t8);
    double t12 = (t10 - t11) - M_PI_2;
    double t13 = t11 + t10 - M_PI_2;
    if (t3 > VAR(db2_radius)) {
        if (((int)t5 & 1) != 0) {
            FPx = (t9 * cos(t13) + FTx) * VVAR + FPx;
            FPy = (sin(t13) * t9 + FTy) * VVAR + FPy;
        } else {
            FPx = (t9 * cos(t12) + FTx) * VVAR + FPx;
            FPy = (sin(t12) * t9 + FTy) * VVAR + FPy;
        }
    } else {
        FPx = FTx * VVAR + FPx;
        FPy = FTy * VVAR + FPy;
    }
    return TRUE;
}