/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        post_heat.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from post_heat.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz', 32: 'TC'} var_base=88

typedef struct {
    double post_heat_theta_period;
    double post_heat_theta_phase;
    double post_heat_theta_amp;
    double post_heat_phi_period;
    double post_heat_phi_phase;
    double post_heat_phi_amp;
    double post_heat_r_period;
    double post_heat_r_phase;
    double post_heat_r_amp;
    double m_48;
    double m_50;
    double m_58;
    double m_60;
    double m_68;
    double m_70;
    double m_78;
    double m_80;
    double m_88;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("post_heat");
APO_VARIABLES(
    VAR_REAL(post_heat_theta_period, 1.0),
    VAR_REAL(post_heat_theta_phase, 0.0),
    VAR_REAL(post_heat_theta_amp, 1.0),
    VAR_REAL(post_heat_phi_period, 1.0),
    VAR_REAL(post_heat_phi_phase, 0.0),
    VAR_REAL(post_heat_phi_amp, 0.0),
    VAR_REAL(post_heat_r_period, 1.0),
    VAR_REAL(post_heat_r_phase, 0.0),
    VAR_REAL(post_heat_r_amp, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    double t1 = VAR(post_heat_theta_amp) * VVAR;
    double t2 = 1.0 / VAR(post_heat_theta_period);
    double t3 = M_2PI * t2;
    double t4 = t2 * VAR(post_heat_theta_phase);
    double t5 = VAR(post_heat_phi_amp) * VVAR;
    double t6 = 1.0 / VAR(post_heat_phi_period);
    double t7 = M_2PI * t6;
    double t8 = t6 * VAR(post_heat_phi_phase);
    double t9 = VVAR * VAR(post_heat_r_amp);
    double t10 = 1.0 / VAR(post_heat_r_period);
    double t11 = M_2PI * t10;
    double t12 = t10 * VAR(post_heat_r_phase);
    if (!(VAR(post_heat_theta_period) != 0.0)) {
        if (!(VAR(post_heat_phi_period) != 0.0)) {
            if (!(VAR(post_heat_r_period) != 0.0)) {
                VAR(m_48) = t1;
                VAR(m_50) = 0.0;
                VAR(m_58) = 0.0;
                VAR(m_60) = t5;
                VAR(m_68) = 0.0;
                VAR(m_70) = 0.0;
                VAR(m_78) = t9;
                VAR(m_80) = 0.0;
                VAR(m_88) = 0.0;
            } else {
                VAR(m_48) = t1;
                VAR(m_50) = 0.0;
                VAR(m_58) = 0.0;
                VAR(m_60) = t5;
                VAR(m_68) = 0.0;
                VAR(m_70) = 0.0;
                VAR(m_78) = t9;
                VAR(m_80) = t11;
                VAR(m_88) = t12;
            }
        } else {
            if (!(VAR(post_heat_r_period) != 0.0)) {
                VAR(m_48) = t1;
                VAR(m_50) = 0.0;
                VAR(m_58) = 0.0;
                VAR(m_60) = t5;
                VAR(m_68) = t7;
                VAR(m_70) = t8;
                VAR(m_78) = t9;
                VAR(m_80) = 0.0;
                VAR(m_88) = 0.0;
            } else {
                VAR(m_48) = t1;
                VAR(m_50) = 0.0;
                VAR(m_58) = 0.0;
                VAR(m_60) = t5;
                VAR(m_68) = t7;
                VAR(m_70) = t8;
                VAR(m_78) = t9;
                VAR(m_80) = t11;
                VAR(m_88) = t12;
            }
        }
    } else {
        if (!(VAR(post_heat_phi_period) != 0.0)) {
            if (!(VAR(post_heat_r_period) != 0.0)) {
                VAR(m_48) = t1;
                VAR(m_50) = t3;
                VAR(m_58) = t4;
                VAR(m_60) = t5;
                VAR(m_68) = 0.0;
                VAR(m_70) = 0.0;
                VAR(m_78) = t9;
                VAR(m_80) = 0.0;
                VAR(m_88) = 0.0;
            } else {
                VAR(m_48) = t1;
                VAR(m_50) = t3;
                VAR(m_58) = t4;
                VAR(m_60) = t5;
                VAR(m_68) = 0.0;
                VAR(m_70) = 0.0;
                VAR(m_78) = t9;
                VAR(m_80) = t11;
                VAR(m_88) = t12;
            }
        } else {
            if (!(VAR(post_heat_r_period) != 0.0)) {
                VAR(m_48) = t1;
                VAR(m_50) = t3;
                VAR(m_58) = t4;
                VAR(m_60) = t5;
                VAR(m_68) = t7;
                VAR(m_70) = t8;
                VAR(m_78) = t9;
                VAR(m_80) = 0.0;
                VAR(m_88) = 0.0;
            } else {
                VAR(m_48) = t1;
                VAR(m_50) = t3;
                VAR(m_58) = t4;
                VAR(m_60) = t5;
                VAR(m_68) = t7;
                VAR(m_70) = t8;
                VAR(m_78) = t9;
                VAR(m_80) = t11;
                VAR(m_88) = t12;
            }
        }
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FPz * FPz + (FPx * FPx + FPy * FPy));
    double t2 = sin(VAR(m_80) * t1 + VAR(m_88)) * VAR(m_78) + t1;
    double t3 = VAR(m_48) * sin(VAR(m_50) * t2 + VAR(m_58)) + atan2(FPy, FPx);
    double t4 = FPz / t2;
    double t5 = VAR(m_60) * sin(VAR(m_68) * t2 + VAR(m_70)) + atan2(sqrt(1.0 - t4 * t4), t4);
    double t6 = sin(t5);
    FPx = cos(t3) * t6 * t2;
    FPy = t6 * sin(t3) * t2;
    FPz = t2 * cos(t5);
    return TRUE;
}