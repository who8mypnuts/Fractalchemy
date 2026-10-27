/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        atan_x86.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from atan_x86.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    int atanMode;
    double atanStretch;
    double m_10;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("atan");
APO_VARIABLES(
    VAR_INTEGER(atanMode, 0),
    VAR_REAL(atanStretch, 1.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(m_10) = M_2_PI * VVAR;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = atan(VAR(atanStretch) * FTy) * VAR(m_10) + FPy;
    double t2 = atan(VAR(atanStretch) * FTx) * VAR(m_10) + FPx;
    if (VAR(atanMode) == 1) {
        FPx = t2;
        FPy = VVAR * FTy + FPy;
    } else {
        if (VAR(atanMode) > 1) {
            if (VAR(atanMode) == 2) {
                FPx = t2;
                FPy = t1;
            } else {
            }
        } else {
            if (VAR(atanMode) == 0) {
                FPx = VVAR * FTx + FPx;
                FPy = t1;
            } else {
            }
        }
    }
    return TRUE;
}