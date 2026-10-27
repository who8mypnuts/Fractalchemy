/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        swirl2.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from swirl2.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double swirl2_twistamount;
    double swirl2_radius;
    double swirl2_centerx;
    double swirl2_centery;
    double m_20;
    double m_28;
    double m_30;
    double m_38;
    double m_40;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("swirl2");
APO_VARIABLES(
    VAR_REAL(swirl2_twistamount, 0.5),
    VAR_REAL(swirl2_radius, 1.0),
    VAR_REAL(swirl2_centerx, 0.0),
    VAR_REAL(swirl2_centery, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_PI * VAR(swirl2_twistamount);
    double t2 = isnan(VAR(swirl2_radius));
    if (t2) {
        VAR(m_20) = t1;
        VAR(m_28) = VAR(swirl2_centerx);
        VAR(m_30) = VAR(swirl2_centery);
        VAR(m_38) = VAR(swirl2_radius);
        VAR(m_40) = VVAR;
    } else {
        if (VAR(swirl2_radius) == 0.0) {
            VAR(m_20) = t1;
            VAR(m_28) = VAR(swirl2_centerx);
            VAR(m_30) = VAR(swirl2_centery);
            VAR(m_38) = 1e-20;
            VAR(m_40) = VVAR;
        } else {
            VAR(m_20) = t1;
            VAR(m_28) = VAR(swirl2_centerx);
            VAR(m_30) = VAR(swirl2_centery);
            VAR(m_38) = VAR(swirl2_radius);
            VAR(m_40) = VVAR;
        }
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx - VAR(m_28);
    double t2 = FTy - VAR(m_30);
    double t3 = (t1 * t1 + t2 * t2) * VAR(m_38);
    double t4 = sqrt(t3);
    double t5 = isnan(t4);
    double t6 = VAR(m_20) * t3;
    double t7 = t6 + atan2(t2 / t4, t1 / t4);
    double t8 = VAR(m_40) * (cos(t7) * t4 + VAR(m_28)) + FPx;
    double t9 = VAR(m_40) * (sin(t7) * t4 + VAR(m_30)) + FPy;
    double t10 = VAR(m_40) * FTz + FPz;
    double t11 = t6 + atan2(t2 / 1e-20, t1 / 1e-20);
    if (t5) {
        FPx = t8;
        FPy = t9;
        FPz = t10;
    } else {
        if (t4 == 0.0) {
            FPx = VAR(m_40) * (1e-20 * cos(t11) + VAR(m_28)) + FPx;
            FPy = VAR(m_40) * (1e-20 * sin(t11) + VAR(m_30)) + FPy;
            FPz = t10;
        } else {
            FPx = t8;
            FPy = t9;
            FPz = t10;
        }
    }
    return TRUE;
}