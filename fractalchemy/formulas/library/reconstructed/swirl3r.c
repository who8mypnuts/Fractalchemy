/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        swirl3r_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from swirl3r_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double swirl3r_shift;
    double swirl3r_min;
    double swirl3r_max;
    double m_18;
    double m_20;
    double m_28;
    double m_30;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("swirl3r");
APO_VARIABLES(
    VAR_REAL(swirl3r_shift, 0.5),
    VAR_REAL(swirl3r_min, 0.5),
    VAR_REAL(swirl3r_max, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = log(VAR(swirl3r_min)) * VAR(swirl3r_shift);
    double t2 = log(VAR(swirl3r_max)) * VAR(swirl3r_shift);
    if (VAR(swirl3r_min) >= VAR(swirl3r_max)) {
        if (!(VAR(swirl3r_max) > 0.0)) {
            if (!(VAR(swirl3r_min) > 0.0)) {
                VAR(m_28) = VAR(swirl3r_max);
                VAR(m_30) = VAR(swirl3r_min);
                VAR(m_18) = 0.0;
                VAR(m_20) = 0.0;
            } else {
                VAR(m_28) = VAR(swirl3r_max);
                VAR(m_30) = VAR(swirl3r_min);
                VAR(m_18) = 0.0;
                VAR(m_20) = t1;
            }
        } else {
            if (!(VAR(swirl3r_min) > 0.0)) {
                VAR(m_28) = VAR(swirl3r_max);
                VAR(m_30) = VAR(swirl3r_min);
                VAR(m_18) = t2;
                VAR(m_20) = 0.0;
            } else {
                VAR(m_28) = VAR(swirl3r_max);
                VAR(m_30) = VAR(swirl3r_min);
                VAR(m_18) = t2;
                VAR(m_20) = t1;
            }
        }
    } else {
        if (!(VAR(swirl3r_min) > 0.0)) {
            if (!(VAR(swirl3r_max) > 0.0)) {
                VAR(m_28) = VAR(swirl3r_min);
                VAR(m_30) = VAR(swirl3r_max);
                VAR(m_18) = 0.0;
                VAR(m_20) = 0.0;
            } else {
                VAR(m_28) = VAR(swirl3r_min);
                VAR(m_30) = VAR(swirl3r_max);
                VAR(m_18) = 0.0;
                VAR(m_20) = t2;
            }
        } else {
            if (!(VAR(swirl3r_max) > 0.0)) {
                VAR(m_28) = VAR(swirl3r_min);
                VAR(m_30) = VAR(swirl3r_max);
                VAR(m_18) = t1;
                VAR(m_20) = 0.0;
            } else {
                VAR(m_28) = VAR(swirl3r_min);
                VAR(m_30) = VAR(swirl3r_max);
                VAR(m_18) = t1;
                VAR(m_20) = t2;
            }
        }
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTx * FTx + FTy * FTy);
    double t2 = atan2(FTy, FTx);
    double t3 = t2 + log(t1) * VAR(swirl3r_shift);
    double t4 = VVAR * t1;
    double t5 = t1 * VVAR;
    double t6 = t2 + VAR(m_20);
    double t7 = t2 + VAR(m_18);
    if (!(t1 >= VAR(m_28))) {
        FPx = cos(t7) * t4 + FPx;
        FPy = sin(t7) * t5 + FPy;
    } else {
        if (t1 > VAR(m_30)) {
            FPx = cos(t6) * t4 + FPx;
            FPy = sin(t6) * t5 + FPy;
        } else {
            FPx = cos(t3) * t4 + FPx;
            FPy = sin(t3) * t5 + FPy;
        }
    }
    return TRUE;
}