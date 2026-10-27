/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        Experimental_Apo_Plugin_by_piritipany.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from Experimental_Apo_Plugin_by_piritipany.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double chladni_l;
    double chladni_m;
    double chladni_n;
    int chladni_mode;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("chladni");
APO_VARIABLES(
    VAR_REAL(chladni_l, 1.0),
    VAR_REAL(chladni_m, 1.0),
    VAR_REAL(chladni_n, 1.0),
    VAR_INTEGER(chladni_mode, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx + 1e-20;
    double t2 = FTy + 1e-20;
    double t3 = M_PI * VAR(chladni_m);
    double t4 = t3 * t2 / VAR(chladni_l);
    double t5 = M_PI * VAR(chladni_n);
    double t6 = t5 * t1 / VAR(chladni_l);
    double t7 = cos(t6);
    double t8 = FTx * (sin(t4) * t7) + FPx;
    double t9 = t5 * t2 / VAR(chladni_l);
    double t10 = t3 * t1 / VAR(chladni_l);
    double t11 = cos(t10);
    double t12 = cos(t9);
    double t13 = FTx * 0.0 /* uninitialised local */ + FPx;
    double t14 = FTy * 0.0 /* uninitialised local */ + FPy;
    if (VAR(chladni_mode) > 5) {
        FPx = t13;
        FPy = t14;
    } else {
        if (VAR(chladni_mode) == 0) {
            FPx = t13;
            FPy = t14;
        } else if (VAR(chladni_mode) == 1) {
            FPx = FTx * (cos(t4) * t7) + FPx;
            FPy = FTy * (t12 * t11) + FPy;
        } else if (VAR(chladni_mode) == 2) {
            FPx = t8;
            FPy = FTy * (t12 * sin(t10)) + FPy;
        } else if (VAR(chladni_mode) == 3) {
            FPx = FTx * (tan(t4) * tan(t6)) + FPx;
            FPy = FTy * (tan(t9) * tan(t10)) + FPy;
        } else if (VAR(chladni_mode) == 4) {
            FPx = t8;
            FPy = FTy * (sin(t9) * t11) + FPy;
        } else if (VAR(chladni_mode) == 5) {
            FPx = FTx * sin(t1) + FPx;
            FPy = FTy * cos(t2) + FPy;
        }
    }
    return TRUE;
}