/*
    Fractalchemy formula library — julia3D
    Ported by hand from Apophysis 7X src/Variations/varJulia3Djf.pas (the built-in julia3D, GPL v2+):
    the 3D Julia set with the depth scaled by the power. Same formula as the Pascal CalcFunction;
    Apophysis's special cases for powers ±1 / ±2 are the general formula with those values.
*/

typedef struct {
    int julia3D_power;
    double cN, absN;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("julia3D");
APO_VARIABLES(
    VAR_INTEGER_NONZERO(julia3D_power, 2)
);

int PluginVarPrepare(Variation* vp)
{
    VAR(absN) = abs(VAR(julia3D_power));
    VAR(cN) = (1.0 / VAR(julia3D_power) - 1.0) / 2.0;
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double z = FTz / VAR(absN);
    double r2d = FTx * FTx + FTy * FTy;
    double r = VVAR * pow(r2d + z * z, VAR(cN));   // r^n / sqrt(r)  -->  r^(n-0.5)
    double tmp = r * sqrt(r2d);
    double sina, cosa;
    fsincos((atan2(FTy, FTx) + M_2PI * (rand() % (int)VAR(absN))) / VAR(julia3D_power), &sina, &cosa);
    FPz += r * z;
    FPx += tmp * cosa;
    FPy += tmp * sina;
    return TRUE;
}
