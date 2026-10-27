/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/essential plugin pack/Sources/tile_log.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct {
    double tile_log_spread;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("tile_log");

APO_VARIABLES(
        VAR_REAL(tile_log_spread, 1.0)
        );

int PluginVarPrepare(Variation* vp) {
    return TRUE;
}

int PluginVarCalc(Variation* vp) {

    FPx += VVAR * (FTx + round(log(random01()) * (rand() % 2 ? VAR(tile_log_spread) : -VAR(tile_log_spread))));
    FPy += VVAR * FTy;

    return TRUE;
}
