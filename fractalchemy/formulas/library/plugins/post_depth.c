/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        post_depth.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct {
    double post_depth_power;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("post_depth");
APO_VARIABLES(
        VAR_REAL(post_depth_power, 1.0)
        );

int PluginVarPrepare(Variation* vp) {
    return 1;
}

int PluginVarCalc(Variation* vp) {
    double coeff = fabs(FTz);
    if (coeff != 0.0 && VAR(post_depth_power) != 1.0)
        coeff = exp(log(coeff) * VAR(post_depth_power));

    FPx = VVAR * (FTx + FPx * coeff);
    FPy = VVAR * (FTy + FPy * coeff);
    FPz = VVAR * (FTz + FPz * coeff);
    return 1;
}
