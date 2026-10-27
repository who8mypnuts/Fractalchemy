/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        mobiq.dll   (x86 (32-bit), no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

// Reconstructed from mobiq.dll (x86) by tools/apo_decompile.py — review before use.
// layout: vvar@0 pointers={20: 'FPx', 24: 'FPy', 28: 'FPz', 8: 'FTx', 12: 'FTy', 16: 'FTz'} var_base=32

typedef struct {
    double mobiq_at;
    double mobiq_ax;
    double mobiq_ay;
    double mobiq_az;
    double mobiq_bt;
    double mobiq_bx;
    double mobiq_by;
    double mobiq_bz;
    double mobiq_ct;
    double mobiq_cx;
    double mobiq_cy;
    double mobiq_cz;
    double mobiq_dt;
    double mobiq_dx;
    double mobiq_dy;
    double mobiq_dz;

} Variables;
#include "apoplugin.h"
APO_PLUGIN("mobiq");
APO_VARIABLES(
    VAR_REAL(mobiq_at, 1.0),
    VAR_REAL(mobiq_ax, 0.0),
    VAR_REAL(mobiq_ay, 0.0),
    VAR_REAL(mobiq_az, 0.0),
    VAR_REAL(mobiq_bt, 0.0),
    VAR_REAL(mobiq_bx, 0.0),
    VAR_REAL(mobiq_by, 0.0),
    VAR_REAL(mobiq_bz, 0.0),
    VAR_REAL(mobiq_ct, 0.0),
    VAR_REAL(mobiq_cx, 0.0),
    VAR_REAL(mobiq_cy, 0.0),
    VAR_REAL(mobiq_cz, 0.0),
    VAR_REAL(mobiq_dt, 1.0),
    VAR_REAL(mobiq_dx, 0.0),
    VAR_REAL(mobiq_dy, 0.0),
    VAR_REAL(mobiq_dz, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double t1 = ((VAR(mobiq_at) * FTx - VAR(mobiq_ax) * FTy) - VAR(mobiq_ay) * FTz) + VAR(mobiq_bt);
    double t2 = ((VAR(mobiq_ct) * FTx - VAR(mobiq_cx) * FTy) - VAR(mobiq_cy) * FTz) + VAR(mobiq_dt);
    double t3 = (VAR(mobiq_at) * FTy + VAR(mobiq_ax) * FTx - VAR(mobiq_az) * FTz) + VAR(mobiq_bx);
    double t4 = (VAR(mobiq_ct) * FTy + VAR(mobiq_cx) * FTx - VAR(mobiq_cz) * FTz) + VAR(mobiq_dx);
    double t5 = VAR(mobiq_at) * FTz + VAR(mobiq_ay) * FTx + VAR(mobiq_az) * FTy + VAR(mobiq_by);
    double t6 = VAR(mobiq_ct) * FTz + VAR(mobiq_cy) * FTx + VAR(mobiq_cz) * FTy + VAR(mobiq_dy);
    double t7 = (VAR(mobiq_az) * FTx + VAR(mobiq_ax) * FTz - VAR(mobiq_ay) * FTy) + VAR(mobiq_bz);
    double t8 = (VAR(mobiq_cz) * FTx + VAR(mobiq_cx) * FTz - VAR(mobiq_cy) * FTy) + VAR(mobiq_dz);
    double t9 = VVAR / (t8 * t8 + (t6 * t6 + (t4 * t4 + t2 * t2)));
    FPx = FPx + (t1 * t2 + t3 * t4 + t5 * t6 + t7 * t8) * t9;
    FPy = FPy + (((t3 * t2 - t1 * t4) - t5 * t8) + t7 * t6) * t9;
    FPz = FPz + (((t5 * t2 - t1 * t6) - t7 * t4) + t3 * t8) * t9;
    return TRUE;
}