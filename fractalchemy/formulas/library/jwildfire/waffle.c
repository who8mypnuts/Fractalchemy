/*
    Fractalchemy formula library — translated from the JWildfire variation
        WaffleFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    int waffle_slices;
    double waffle_xthickness;
    double waffle_ythickness;
    double waffle_rotation;
    double waffle_vsinr;
    double waffle_vcosr;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("waffle");

APO_VARIABLES(
    VAR_INTEGER(waffle_slices, 6),
    VAR_REAL(waffle_xthickness, 0.5),
    VAR_REAL(waffle_ythickness, 0.5),
    VAR_REAL(waffle_rotation, 0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(waffle_vcosr) = VVAR * cos(VAR(waffle_rotation));
    VAR(waffle_vsinr) = VVAR * sin(VAR(waffle_rotation));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double a = 0.0, r = 0.0;
    switch((int)(random01() *  5)) {
        case 0 : a = ((int)(random01() *  VAR(waffle_slices)) + random01() * VAR(waffle_xthickness)) / VAR(waffle_slices);
        r = ((int)(random01() *  VAR(waffle_slices)) + random01() * VAR(waffle_ythickness)) / VAR(waffle_slices);
        break;
        case 1 : a = ((int)(random01() *  VAR(waffle_slices)) + random01()) / VAR(waffle_slices);
        r = ((int)(random01() *  VAR(waffle_slices)) + VAR(waffle_ythickness)) / VAR(waffle_slices);
        break;
        case 2 : a = ((int)(random01() *  VAR(waffle_slices)) + VAR(waffle_xthickness)) / VAR(waffle_slices);
        r = ((int)(random01() *  VAR(waffle_slices)) + random01()) / VAR(waffle_slices);
        break;
        case 3 : a = random01();
        r = ((int)(random01() *  VAR(waffle_slices)) + VAR(waffle_ythickness) + random01() * (1 - VAR(waffle_ythickness))) / VAR(waffle_slices);
        break;
        case 4 : a = ((int)(random01() *  VAR(waffle_slices)) + VAR(waffle_xthickness) + random01() * (1 - VAR(waffle_xthickness))) / VAR(waffle_slices);
        r = random01();
        break;
        default : break;
    }
    FPx += (VAR(waffle_vcosr) * a + VAR(waffle_vsinr) * r);
    FPy += (- VAR(waffle_vsinr) * a + VAR(waffle_vcosr) * r);
    
    return TRUE;
}
