/*
    Fractalchemy formula library — translated from the JWildfire variation
        DiamondLatticeFunc.java
    by tools/import_jwf_variations.py (JWildfire: Copyright (C) 1995-2021 Andreas Maschke and contributors,
    GNU Lesser General Public License v2.1 or later — https://github.com/thargor6/JWildfire). The formula
    compiler (fractalchemy/formulas/lang) runs this for both the numpy (float64) and GLSL engines. Verified:
    the two translations agree on the test points (tests/test_variations.py).
*/

typedef struct {
    double diamond_lattice_scale;
    double diamond_lattice_pull;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("diamond_lattice");

APO_VARIABLES(
    VAR_REAL(diamond_lattice_scale, 2),
    VAR_REAL(diamond_lattice_pull, 0.5)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double dl_ax = FTx * VAR(diamond_lattice_scale);
    double dl_ay = FTy * VAR(diamond_lattice_scale);
    double dl_u = (dl_ax + dl_ay) * 0.7071067811865475;
    double dl_v = (dl_ax - dl_ay) * 0.7071067811865475;
    double dl_nu = round(dl_u);
    double dl_nv = round(dl_v);
    double dl_du = dl_u - dl_nu;
    double dl_dv = dl_v - dl_nv;
    double dl_bx = (dl_nu + dl_nv) * 0.7071067811865475;
    double dl_by = (dl_nu - dl_nv) * 0.7071067811865475;
    FPx += VVAR * (dl_bx + dl_du * (1.0 - VAR(diamond_lattice_pull))) / VAR(diamond_lattice_scale);
    FPy += VVAR * (dl_by + dl_dv * (1.0 - VAR(diamond_lattice_pull))) / VAR(diamond_lattice_scale);
    
    return TRUE;
}
