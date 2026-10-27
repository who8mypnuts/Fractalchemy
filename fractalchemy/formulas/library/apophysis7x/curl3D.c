/*
    Fractalchemy formula library — curl3D
    Ported by hand from Apophysis 7X src/Variations/varCurl3D.pas (the built-in curl3D, GPL v2+):
    the general CalcFunction (Apophysis's specialised variants for single non-zero coefficients
    give the same result).
*/

typedef struct {
    double curl3D_cx, curl3D_cy, curl3D_cz;
    double c2x, c2y, c2z, c2;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("curl3D");
APO_VARIABLES(
    VAR_REAL(curl3D_cx, 0.0),
    VAR_REAL(curl3D_cy, 0.0),
    VAR_REAL(curl3D_cz, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(c2x) = 2 * VAR(curl3D_cx);
    VAR(c2y) = 2 * VAR(curl3D_cy);
    VAR(c2z) = 2 * VAR(curl3D_cz);
    VAR(c2) = sqr(VAR(curl3D_cx)) + sqr(VAR(curl3D_cy)) + sqr(VAR(curl3D_cz));
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2 = sqr(FTx) + sqr(FTy) + sqr(FTz);
    double r = VVAR / (r2 * VAR(c2) + VAR(c2x) * FTx - VAR(c2y) * FTy + VAR(c2z) * FTz + 1);
    FPx += r * (FTx + VAR(curl3D_cx) * r2);
    FPy += r * (FTy - VAR(curl3D_cy) * r2);
    FPz += r * (FTz + VAR(curl3D_cz) * r2);
    return TRUE;
}
