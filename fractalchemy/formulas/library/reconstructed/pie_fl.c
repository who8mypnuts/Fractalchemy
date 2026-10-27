/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        pie_fl.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from pie_fl.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double pie_fl_slices;
    double pie_fl_thickness;
    double pie_fl_rotation;
    double m_18;
} Variables;
#include "apoplugin.h"
APO_PLUGIN("pie_fl");
APO_VARIABLES(
    VAR_REAL(pie_fl_slices, 6.0),
    VAR_REAL(pie_fl_thickness, 0.43333),
    VAR_REAL_CYCLE(pie_fl_rotation, 0.0, M_2PI, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    if (!(fabs(VAR(pie_fl_slices)) >= 1.0)) {
        VAR(m_18) = M_2PI * VAR(pie_fl_slices);
    } else {
        VAR(m_18) = M_2PI * (1.0 / (VAR(pie_fl_slices) + 1e-20));
    }
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = (random01() * VAR(pie_fl_thickness) + trunc(random01() * VAR(pie_fl_slices))) * VAR(m_18) + VAR(pie_fl_rotation);
    double t2 = 16777216 * (double)((rand() ^ rand() << 15) & 268435455) * VVAR;
    FPx = cos(t1) * t2 + FPx;
    FPy = t2 * sin(t1) + FPy;
    return TRUE;
}