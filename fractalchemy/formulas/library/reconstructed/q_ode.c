/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        q_ode.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from q_ode.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double q_ode01;
    double q_ode02;
    double q_ode03;
    double q_ode04;
    double q_ode05;
    double q_ode06;
    double q_ode07;
    double q_ode08;
    double q_ode09;
    double q_ode10;
    double q_ode11;
    double q_ode12;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("q_ode");
APO_VARIABLES(
    VAR_REAL(q_ode01, 1.0),
    VAR_REAL(q_ode02, -1.0),
    VAR_REAL(q_ode03, 0.0),
    VAR_REAL(q_ode04, 0.0),
    VAR_REAL(q_ode05, 0.0),
    VAR_REAL(q_ode06, 0.0),
    VAR_REAL(q_ode07, 1.0),
    VAR_REAL(q_ode08, 0.0),
    VAR_REAL(q_ode09, 0.0),
    VAR_REAL(q_ode10, 0.0),
    VAR_REAL(q_ode11, 0.0),
    VAR_REAL(q_ode12, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = FTx * (VAR(q_ode03) * FTx) + (VAR(q_ode02) * VVAR * FTx + VAR(q_ode01)) + FPx;
    double t2 = FTx * (VAR(q_ode09) * FTx) + (VAR(q_ode08) * FTx + VAR(q_ode07)) + FPy;
    FPx = t1 + (FTx * VAR(q_ode04) * FTy + VAR(q_ode05) * FTy + FTy * (VAR(q_ode06) * FTy));
    FPy = t2 + (FTy * (VAR(q_ode12) * FTy) + (VAR(q_ode11) * VVAR * FTy + FTx * VAR(q_ode10) * FTy));
    return TRUE;
}