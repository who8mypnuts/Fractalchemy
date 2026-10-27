/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        taurus3.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from taurus3.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int taurus3_case;
    double taurus3_r;
    double taurus3_n;
    double taurus3_sph;
    double taurus3_tor;
    double taurus3_inv;
    double taurus3_sor;
    double taurus3_svf;
    double taurus3_rr;
    double taurus3_xpow;
    double taurus3_ypow;
    double taurus3_zpow;
    double m_58;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("taurus3");
APO_VARIABLES(
    VAR_INTEGER(taurus3_case, 6),
    VAR_REAL(taurus3_r, 0.0),
    VAR_REAL(taurus3_n, 0.0),
    VAR_REAL(taurus3_sph, 1.0),
    VAR_REAL(taurus3_tor, 0.0),
    VAR_REAL(taurus3_inv, 0.0),
    VAR_REAL(taurus3_sor, 0.0),
    VAR_REAL(taurus3_svf, 0.0),
    VAR_REAL(taurus3_rr, 0.0),
    VAR_REAL(taurus3_xpow, 1.0),
    VAR_REAL(taurus3_ypow, 1.0),
    VAR_REAL(taurus3_zpow, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_58) = (VAR(taurus3_xpow) + VAR(taurus3_ypow) + VAR(taurus3_zpow)) / 3.0;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = cos(VAR(taurus3_n) * FTx) * VAR(taurus3_r) * (1.0 - VAR(taurus3_inv)) + VAR(taurus3_inv) * VAR(taurus3_r);
    double t2 = sin(FTy);
    double t3 = 1.0 - VAR(taurus3_svf);
    double t4 = t1 * t2 * VAR(taurus3_svf) + t3 * (t1 + t2);
    double t5 = cos(FTx);
    double t6 = pow(t4 * t5, VAR(taurus3_xpow));
    double t7 = sin(FTx);
    double t8 = pow(t4 * t7, VAR(taurus3_ypow));
    double t9 = cos(FTy);
    double t10 = pow(t3 * VAR(taurus3_sor) * t9 + (1.0 - VAR(taurus3_sor)) * FTy + t1 * t5 * VAR(taurus3_svf), VAR(taurus3_zpow));
    double t11 = t6 * t6 + t8 * t8 + t10 * t10 + 1e-20;
    double t12 = 1.0 - VAR(taurus3_rr);
    double t13 = VVAR / VAR(m_58);
    double t14 = cos(FTy * VAR(taurus3_n));
    double t15 = t5 * t14 * t9;
    double t16 = t7 * t14 * t9;
    double t17 = t14 * t2;
    double t18 = t15 * t15 + t16 * t16 + t17 * t17 + 1e-20;
    double t19 = t14 / VAR(taurus3_n) + VAR(taurus3_r);
    double t20 = t19 * t5;
    double t21 = t19 * t7;
    double t22 = t20 * t20 + t21 * t21 + FTy * FTy + 1e-20;
    double t23 = t9 + cos(FTx * VAR(taurus3_n)) * VAR(taurus3_r);
    double t24 = t23 * t5;
    double t25 = t23 * t7;
    double t26 = t2 * t2;
    double t27 = t24 * t24 + t25 * t25 + t26 + 1e-20;
    double t28 = VAR(taurus3_rr) * t2;
    double t29 = t12 * t2;
    double t30 = t9 + VAR(taurus3_r);
    double t31 = t30 * t5;
    double t32 = t30 * t7;
    double t33 = t31 * t31 + t32 * t32 + t26 + 1e-20;
    double t34 = t9 * t5;
    double t35 = pow(t34, 3.0);
    double t36 = t9 * t7;
    double t37 = pow(t36, 3.0);
    double t38 = pow(t2, 3.0);
    double t39 = t35 * t35 + t37 * t37 + t38 * t38 + 1e-20;
    double t40 = t34 * t34 + t36 * t36 + t26 + 1e-20;
    double t41 = 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + 0.0 /* uninitialised local */ * 0.0 /* uninitialised local */ + 1e-20;
    if (VAR(taurus3_case) > 6) {
        FPx = (VAR(taurus3_rr) * 0.0 /* uninitialised local */ / t41 + t12 * 0.0 /* uninitialised local */) * t13 + FPx;
        FPy = (VAR(taurus3_rr) * 0.0 /* uninitialised local */ / t41 + t12 * 0.0 /* uninitialised local */) * t13 + FPy;
        FPz = (VAR(taurus3_rr) * 0.0 /* uninitialised local */ / t41 + t12 * 0.0 /* uninitialised local */) * t13 + FPz;
    } else {
        if (VAR(taurus3_case) == 0) {
            FPx = (VAR(taurus3_rr) * t34 / t40 + t12 * t34) * t13 + FPx;
            FPy = (VAR(taurus3_rr) * t36 / t40 + t12 * t36) * t13 + FPy;
            FPz = (t28 / t40 + t29) * t13 + FPz;
        } else if (VAR(taurus3_case) == 1) {
            FPx = (VAR(taurus3_rr) * t35 / t39 + t12 * t35) * t13 + FPx;
            FPy = (VAR(taurus3_rr) * t37 / t39 + t12 * t37) * t13 + FPy;
            FPz = (VAR(taurus3_rr) * t38 / t39 + t12 * t38) * t13 + FPz;
        } else if (VAR(taurus3_case) == 2) {
            FPx = (VAR(taurus3_rr) * t31 / t33 + t12 * t31) * t13 + FPx;
            FPy = (VAR(taurus3_rr) * t32 / t33 + t12 * t32) * t13 + FPy;
            FPz = (t28 / t33 + t29) * t13 + FPz;
        } else if (VAR(taurus3_case) == 3) {
            FPx = (VAR(taurus3_rr) * t24 / t27 + t12 * t24) * t13 + FPx;
            FPy = (VAR(taurus3_rr) * t25 / t27 + t12 * t25) * t13 + FPy;
            FPz = (t28 / t27 + t29) * t13 + FPz;
        } else if (VAR(taurus3_case) == 4) {
            FPx = (VAR(taurus3_rr) * t20 / t22 + t12 * t20) * t13 + FPx;
            FPy = (VAR(taurus3_rr) * t21 / t22 + t12 * t21) * t13 + FPy;
            FPz = (VAR(taurus3_rr) * FTy / t22 + t12 * FTy) * t13 + FPz;
        } else if (VAR(taurus3_case) == 5) {
            FPx = (VAR(taurus3_rr) * t15 / t18 + t12 * t15) * t13 + FPx;
            FPy = (VAR(taurus3_rr) * t16 / t18 + t12 * t16) * t13 + FPy;
            FPz = (VAR(taurus3_rr) * t17 / t18 + t12 * t17) * t13 + FPz;
        } else if (VAR(taurus3_case) == 6) {
            FPx = (VAR(taurus3_rr) * t6 / t11 + t12 * t6) * t13 + FPx;
            FPy = (VAR(taurus3_rr) * t8 / t11 + t12 * t8) * t13 + FPy;
            FPz = (VAR(taurus3_rr) * t10 / t11 + t12 * t10) * t13 + FPz;
        }
    }
    return TRUE;
}