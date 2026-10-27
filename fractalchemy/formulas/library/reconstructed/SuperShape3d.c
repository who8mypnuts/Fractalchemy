/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        SuperShape3d.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from SuperShape3d.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double SuperShape3d_rho;
    double SuperShape3d_phi;
    double SuperShape3d_m1;
    double SuperShape3d_m2;
    double SuperShape3d_a1;
    double SuperShape3d_a2;
    double SuperShape3d_b1;
    double SuperShape3d_b2;
    double SuperShape3d_n1_1;
    double SuperShape3d_n1_2;
    double SuperShape3d_n2_1;
    double SuperShape3d_n2_2;
    double SuperShape3d_n3_1;
    double SuperShape3d_n3_2;
    double SuperShape3d_spiral;
    int SuperShape3d_toroidmap;
    double m_80;
    double m_88;
    double m_90;
    double m_98;
    double m_a0;
    double m_a8;
    double m_b0;
    double m_b8;
    double m_c0;
    double m_c8;
    double m_d0;
    double m_d8;
    double m_e0;
    double m_e8;
    double m_f0;
    double m_f8;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("SuperShape3d");
APO_VARIABLES(
    VAR_REAL(SuperShape3d_rho, 9.9),
    VAR_REAL(SuperShape3d_phi, 2.5),
    VAR_REAL(SuperShape3d_m1, 6.0),
    VAR_REAL(SuperShape3d_m2, 3.0),
    VAR_REAL(SuperShape3d_a1, 1.0),
    VAR_REAL(SuperShape3d_a2, 1.0),
    VAR_REAL(SuperShape3d_b1, 1.0),
    VAR_REAL(SuperShape3d_b2, 1.0),
    VAR_REAL(SuperShape3d_n1_1, 1.0),
    VAR_REAL(SuperShape3d_n1_2, 1.0),
    VAR_REAL(SuperShape3d_n2_1, 1.0),
    VAR_REAL(SuperShape3d_n2_2, 1.0),
    VAR_REAL(SuperShape3d_n3_1, 1.0),
    VAR_REAL(SuperShape3d_n3_2, 1.0),
    VAR_REAL(SuperShape3d_spiral, 0.0),
    VAR_INTEGER(SuperShape3d_toroidmap, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_80) = -1.0 / VAR(SuperShape3d_n1_1);
    VAR(m_c0) = -1.0 / VAR(SuperShape3d_n1_2);
    VAR(m_88) = VAR(SuperShape3d_n2_1);
    VAR(m_c8) = VAR(SuperShape3d_n2_2);
    VAR(m_90) = VAR(SuperShape3d_n3_1);
    VAR(m_d0) = VAR(SuperShape3d_n3_2);
    VAR(m_98) = pow(fabs(1.0 / VAR(SuperShape3d_a1)), VAR(SuperShape3d_n2_1));
    VAR(m_d8) = pow(fabs(1.0 / VAR(SuperShape3d_a2)), VAR(SuperShape3d_n2_2));
    VAR(m_a0) = pow(fabs(1.0 / VAR(SuperShape3d_b1)), VAR(SuperShape3d_n3_1));
    VAR(m_e0) = pow(fabs(1.0 / VAR(SuperShape3d_b2)), VAR(SuperShape3d_n3_2));
    VAR(m_a8) = VAR(SuperShape3d_m1) / 4.0;
    VAR(m_e8) = VAR(SuperShape3d_m2) / 4.0;
    VAR(m_b8) = VAR(SuperShape3d_spiral);
    VAR(m_b0) = M_2_PI * VAR(SuperShape3d_rho);
    VAR(m_f0) = M_2_PI * VAR(SuperShape3d_phi);
    VAR(m_f8) = VAR(SuperShape3d_toroidmap);
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = random01();
    double t2 = t1 * VAR(m_b0);
    double t3 = cos(t2);
    double t4 = t1 * VAR(m_f0);
    double t5 = VAR(m_e8) * t4;
    double t6 = pow(pow(fabs(sin(t5)), VAR(m_d0)) * VAR(m_e0) + pow(fabs(cos(t5)), VAR(m_c8)) * VAR(m_d8), VAR(m_c0));
    double t7 = cos(t4);
    double t8 = VAR(m_a8) * t2;
    double t9 = pow(pow(fabs(sin(t8)), VAR(m_90)) * VAR(m_a0) + pow(fabs(cos(t8)), VAR(m_88)) * VAR(m_98), VAR(m_80)) + VAR(m_b8) * t2;
    double t10 = t6 * t7 + t9;
    double t11 = VVAR * t3 * t10 + FPx;
    double t12 = sin(t2);
    double t13 = VVAR * t12 * t10 + FPy;
    double t14 = VVAR * t6 * sin(t4) + FPz;
    double t15 = VVAR * t9;
    double t16 = t15 * t3 * t6 * t7 + FPx;
    double t17 = t15 * t12 * t6 * t7 + FPy;
    if ((int)fmod((double)rand(), 2.0) != 1) {
        if (VAR(m_f8) != 1) {
            FPx = t16;
            FPy = t17;
            FPz = t14;
        } else {
            FPx = t11;
            FPy = t13;
            FPz = t14;
        }
    } else {
        if (VAR(m_f8) != 1) {
            FPx = t16;
            FPy = t17;
            FPz = t14;
        } else {
            FPx = t11;
            FPy = t13;
            FPz = t14;
        }
    }
    return TRUE;
}