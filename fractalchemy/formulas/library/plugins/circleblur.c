/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        circleblur.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("circleblur");
APO_VARIABLES();

int PluginVarPrepare(Variation* vp)
{
    return 1;
}

int PluginVarCalc(Variation* vp)
{
    const double rad = sqrt(random01());
    
    double s, c;
    fsincos(random01() * M_2PI, &s, &c);
    
    FPx += VVAR * c * rad;
    FPy += VVAR * s * rad;
    return 1;
}
