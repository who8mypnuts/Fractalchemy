/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        tripolar.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from tripolar.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double tripolar_r1;
    double tripolar_a1;
    double tripolar_r2;
    double tripolar_a2;
    double tripolar_r3;
    double tripolar_a3;
    double m_30;
    double m_38;
    double m_40;
    double m_48;
    double m_50;
    double m_58;
    double m_60;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("tripolar");
APO_VARIABLES(
    VAR_REAL(tripolar_r1, 1.0),
    VAR_REAL(tripolar_a1, 0.0),
    VAR_REAL(tripolar_r2, 1.0),
    VAR_REAL(tripolar_a2, 1.3333333333333333),
    VAR_REAL(tripolar_r3, 1.0),
    VAR_REAL(tripolar_a3, -1.3333333333333333)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = M_PI_2 * VAR(tripolar_a1);
    double t2 = M_PI_2 * VAR(tripolar_a2);
    double t3 = M_PI_2 * VAR(tripolar_a3);
    VAR(m_30) = cos(t1) * VAR(tripolar_r1);
    VAR(m_38) = sin(t1) * VAR(tripolar_r1);
    VAR(m_40) = cos(t2) * VAR(tripolar_r2);
    VAR(m_48) = sin(t2) * VAR(tripolar_r2);
    VAR(m_50) = cos(t3) * VAR(tripolar_r3);
    VAR(m_58) = sin(t3) * VAR(tripolar_r3);
    VAR(m_60) = M_2_PI * VVAR;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTy * VAR(m_38) + 1.0 - FTx * VAR(m_30);
    double t2 = -FTy;
    double t3 = t2 * VAR(m_30) - FTx * VAR(m_38);
    double t4 = 0.5 * log(t1 * t1 + t3 * t3);
    double t5 = atan2(t3, t1);
    double t6 = FPx - (VAR(m_30) * t4 + VAR(m_38) * t5) * VAR(m_60);
    double t7 = (t4 * VAR(m_38) - t5 * VAR(m_30)) * VAR(m_60) + FPy;
    double t8 = FTy * VAR(m_48) + 1.0 - FTx * VAR(m_40);
    double t9 = t2 * VAR(m_40) - FTx * VAR(m_48);
    double t10 = 0.5 * log(t8 * t8 + t9 * t9);
    double t11 = atan2(t9, t8);
    double t12 = t6 - (VAR(m_40) * t10 + VAR(m_48) * t11) * VAR(m_60);
    double t13 = (t10 * VAR(m_48) - t11 * VAR(m_40)) * VAR(m_60) + t7;
    double t14 = FTy * VAR(m_58) + 1.0 - FTx * VAR(m_50);
    double t15 = t2 * VAR(m_50) - FTx * VAR(m_58);
    double t16 = 0.5 * log(t14 * t14 + t15 * t15);
    double t17 = atan2(t15, t14);
    FPx = t12 - (VAR(m_50) * t16 + VAR(m_58) * t17) * VAR(m_60);
    FPy = (t16 * VAR(m_58) - t17 * VAR(m_50)) * VAR(m_60) + t13;
    return TRUE;
}