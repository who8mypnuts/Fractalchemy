/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        juliascope_fl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from juliascope_fl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double juliascope_fl_power;
    double juliascope_fl_dist;
    double m_18;
    double m_20;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("juliascope_fl");
APO_VARIABLES(
    VAR_REAL(juliascope_fl_power, 2.0),
    VAR_REAL(juliascope_fl_dist, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    if (fabs(VAR(juliascope_fl_power)) >= 1.0) {
        VAR(m_20) = VAR(juliascope_fl_power);
        VAR(m_18) = 0.5 * ((1.0 / VAR(juliascope_fl_power)) * VAR(juliascope_fl_dist));
    } else {
        VAR(m_20) = VAR(juliascope_fl_power);
        VAR(m_18) = 0.5 * (VAR(juliascope_fl_power) * VAR(juliascope_fl_dist));
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = fabs(VAR(m_20));
    double t2 = 1.0 / VAR(m_20);
    double t3 = atan2(FTy, FTx);
    double t4 = M_2PI * (double)(int)trunc(random01() * (t1 - 1e-05));
    double t5 = t3 + t4;
    double t6 = t2 * t5;
    double t7 = pow(FTy * FTy + FTx * FTx, VAR(m_18)) * VVAR;
    double t8 = VAR(m_20) * t5;
    double t9 = -t3 + t4;
    double t10 = VAR(m_20) * t9;
    double t11 = t2 * t9;
    if (((int)trunc(random01() * (t1 - 1e-05)) & 1) != 0) {
        if (t1 > 1.0) {
            FPx = cos(t11) * t7 + FPx;
            FPy = t7 * sin(t11) + FPy;
        } else {
            FPx = cos(t10) * t7 + FPx;
            FPy = t7 * sin(t10) + FPy;
        }
    } else {
        if (!(t1 > 1.0)) {
            FPx = cos(t8) * t7 + FPx;
            FPy = t7 * sin(t8) + FPy;
        } else {
            FPx = cos(t6) * t7 + FPx;
            FPy = t7 * sin(t6) + FPy;
        }
    }
    return TRUE;
}