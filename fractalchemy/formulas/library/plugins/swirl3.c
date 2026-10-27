/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/essential plugin pack/Sources/swirl3.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct {
    double swirl3_shift;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("swirl3");
APO_VARIABLES(
        VAR_REAL(swirl3_shift, 0.5)
        );

int PluginVarPrepare(Variation* vp) {
    return TRUE;
}

int PluginVarCalc(Variation* vp) {
    double rad = sqrt(FTx * FTx + FTy * FTy);
    double ang = atan2(FTy, FTx) + log(rad) * VAR(swirl3_shift);
    double s, c;
    fsincos(ang, &s, &c);
    FPx += VVAR * rad * c;
    FPy += VVAR * rad * s;
    return 1;
}
