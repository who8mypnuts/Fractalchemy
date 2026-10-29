/*
    Fractalchemy formula library — translated from the JWildfire variation
        TriLatticeFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double tri_lattice_scale;
    double tri_lattice_morph;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("tri_lattice");

APO_VARIABLES(
    VAR_REAL(tri_lattice_scale, 2),
    VAR_REAL(tri_lattice_morph, 1)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double tl_ax = FTx * VAR(tri_lattice_scale);
    double tl_ay = FTy * VAR(tri_lattice_scale);
    double tl_u = tl_ax - tl_ay * 0.5773502691896257;
    double tl_v = tl_ay * 1.1547005383792515;
    double tl_fu = tl_u - round(tl_u);
    double tl_fv = tl_v - round(tl_v);
    double tl_bx = tl_fu + tl_fv * 0.5;
    double tl_by = tl_fv * 0.8660254037844386;
    FPx += VVAR * (FTx + VAR(tri_lattice_morph) * (tl_bx / VAR(tri_lattice_scale) - FTx));
    FPy += VVAR * (FTy + VAR(tri_lattice_morph) * (tl_by / VAR(tri_lattice_scale) - FTy));
    
    return TRUE;
}
