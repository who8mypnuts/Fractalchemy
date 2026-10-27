/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        GlynnSim4.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from GlynnSim4.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double GlynnSim4_radius;
    double GlynnSim4_radius1;
    double GlynnSim4_Phi1;
    double GlynnSim4_thickness;
    double GlynnSim4_pow;
    double GlynnSim4_contrast;
    double GlynnSim4_X1;
    double GlynnSim4_Y1;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("GlynnSim4");
APO_VARIABLES(
    VAR_REAL(GlynnSim4_radius, 1.0),
    VAR_REAL(GlynnSim4_radius1, 0.1),
    VAR_REAL(GlynnSim4_Phi1, 0.0),
    VAR_REAL(GlynnSim4_thickness, 0.1),
    VAR_REAL(GlynnSim4_pow, 1.5),
    VAR_REAL(GlynnSim4_contrast, 0.5),
    VAR_REAL(GlynnSim4_X1, 0.0),
    VAR_REAL(GlynnSim4_Y1, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(GlynnSim4_pow) = fabs(VAR(GlynnSim4_pow));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = sqrt(FTx * FTx + FTy * FTy);
    double t2 = VAR(GlynnSim4_radius) / t1;
    double t3 = VAR(GlynnSim4_radius1) * VAR(GlynnSim4_radius1);
    double t4 = t2 * t2;
    double t5 = t4 * FTx;
    double t6 = t4 * FTy;
    double t7 = (t5 - VAR(GlynnSim4_X1)) + (t6 - VAR(GlynnSim4_Y1));
    double t8 = VVAR * t5 + FPx;
    double t9 = VVAR * t6 + FPy;
    double t10 = (FTx - VAR(GlynnSim4_X1)) + (FTy - VAR(GlynnSim4_Y1));
    double t11 = VVAR * FTx + FPx;
    double t12 = VVAR * FTy + FPy;
    if (VAR(GlynnSim4_radius) > t1) {
        FPx = VVAR * 0.0 /* uninitialised local */ + FPx;
        FPy = VVAR * 0.0 /* uninitialised local */ + FPy;
    } else {
        if (random01() > pow(t2, VAR(GlynnSim4_pow)) * VAR(GlynnSim4_contrast)) {
            FPx = t11;
            FPy = t12;
        } else {
            FPx = t8;
            FPy = t9;
        }
    }
    return TRUE;
}