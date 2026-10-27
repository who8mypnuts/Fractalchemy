/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        blob2_alpha.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from blob2_alpha.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int blob2_n;
    double blob2_radius;
    double blob2_prescale;
    double blob2_postscale;
    double blob2_symmetry;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("blob2_alpha");
APO_VARIABLES(
    VAR_INTEGER_NONZERO(blob2_n, 5),
    VAR_REAL(blob2_radius, 1.0),
    VAR_REAL(blob2_prescale, 1.0),
    VAR_REAL(blob2_postscale, 0.5),
    VAR_REAL(blob2_symmetry, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTz * VVAR + FPz;
    double t2 = sin((double)VAR(blob2_n) * atan2(FTy, FTx)) + VAR(blob2_symmetry);
    double t3 = FTx * VVAR;
    double t4 = exp(log(t2) * VAR(blob2_prescale)) * VAR(blob2_postscale) / VAR(blob2_radius) + 1.0;
    double t5 = FTy * VVAR;
    double t6 = -(exp(log(-t2) * VAR(blob2_prescale)) * VAR(blob2_postscale)) / VAR(blob2_radius) + 1.0;
    if (0.0 > t2) {
        FPz = t1;
        FPx = t3 * t6 + FPx;
        FPy = t5 * t6 + FPy;
    } else {
        FPz = t1;
        FPx = t3 * t4 + FPx;
        FPy = t5 * t4 + FPy;
    }
    return TRUE;
}