/*
    Fractalchemy formula library — julia3Dz
    Ported by hand from Apophysis 7X src/Variations/varJulia3Dz.pas (the built-in julia3Dz, GPL v2+).
*/

typedef struct {
    int julia3Dz_power;
    double cN, absN;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("julia3Dz");
APO_VARIABLES(
    VAR_INTEGER_NONZERO(julia3Dz_power, 2)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(absN) = abs(VAR(julia3Dz_power));
    VAR(cN) = 1.0 / VAR(julia3Dz_power) / 2.0;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double r2d = FTx * FTx + FTy * FTy;
    double r = VVAR * pow(r2d, VAR(cN));
    double sina, cosa;
    FPz += r * FTz / (sqrt(r2d) * VAR(absN));
    fsincos((atan2(FTy, FTx) + M_2PI * (rand() % (int)VAR(absN))) / VAR(julia3Dz_power), &sina, &cosa);
    FPx += r * cosa;
    FPy += r * sina;
    return TRUE;
}
