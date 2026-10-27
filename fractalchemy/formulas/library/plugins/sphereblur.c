/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        sphereblur.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
    double sphereblur_power;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("sphereblur");
APO_VARIABLES(
        VAR_REAL(sphereblur_power, 1.0)
        );

int PluginVarPrepare(Variation* vp) {
    if (VAR(sphereblur_power) < 0) VAR(sphereblur_power) = 0.0;
}

int PluginVarCalc(Variation* vp) {
    double ang = random01() * M_2PI,
        angz = acos(random01() * 2 - 1),
        pow = VAR(sphereblur_power),
        r = VVAR * exp(log(acos((pow == 1.0 ? random01() : exp(log(random01()) * pow)) * 2 - 1) / M_PI) / 1.5);
        r = VVAR * exp(log(acos((pow == 1.0 ? random01() : exp(log(random01()) * pow)) * 2 - 1) / M_PI) / 1.5);
    double s, c;
    fsincos(ang, &s, &c);
    double sz, cz;
    fsincos(angz, &sz, &cz);
    FPx += r * c * sz;
    FPy += r * s * sz;
    FPz += r * cz;
    return 1;
}