/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/essential plugin pack/Sources/hypershift.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct {
    double hypershift_shift, hypershift_scale;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("hypershift");
APO_VARIABLES(
        VAR_REAL(hypershift_shift, 0.1)
        );

int PluginVarPrepare(Variation* vp) {
    VAR(hypershift_scale) = 1 - VAR(hypershift_shift) * VAR(hypershift_shift);
    return TRUE;
}

int PluginVarCalc(Variation* vp) {
    double rad = 1 / (FTx * FTx + FTy * FTy);
    double x = rad * FTx + VAR(hypershift_shift);
    double y = rad * FTy;
    rad = VVAR * VAR(hypershift_scale) / (x * x + y * y);
    FPx = rad * x + VAR(hypershift_shift);
    FPy = rad * y;
    return 1;
}
