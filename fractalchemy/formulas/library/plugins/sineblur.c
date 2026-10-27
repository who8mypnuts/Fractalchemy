/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        sineblur.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct {
    double sineblur_power;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("sineblur");
APO_VARIABLES(
        VAR_REAL(sineblur_power, 1.0)
        );

int PluginVarPrepare(Variation* vp) {
    if (VAR(sineblur_power) < 0) VAR(sineblur_power) = 0.0;
}

int PluginVarCalc(Variation* vp) {
    double ang = random01() * M_2PI, r = VVAR * (VAR(sineblur_power) == 1.0 ? acos(random01() * 2 - 1) / M_PI : acos(exp(log(random01()) * VAR(sineblur_power)) * 2 - 1) / M_PI);
    double s, c;
    fsincos(ang, &s, &c);
    FPx += r * c;
    FPy += r * s;
    return 1;
}