/*
    Fractalchemy formula library — waves2
    Ported by hand from Apophysis 7X src/Variations/varWaves2.pas (the built-in waves2, GPL v2+),
    which extends the classic plugin with a depth wave (waves2_freqz / waves2_scalez).
*/

typedef struct {
    double waves2_freqx, waves2_freqy, waves2_freqz;
    double waves2_scalex, waves2_scaley, waves2_scalez;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("waves2");
APO_VARIABLES(
    VAR_REAL(waves2_freqx, 2.0),
    VAR_REAL(waves2_freqy, 2.0),
    VAR_REAL(waves2_freqz, 0.0),
    VAR_REAL(waves2_scalex, 1.0),
    VAR_REAL(waves2_scaley, 1.0),
    VAR_REAL(waves2_scalez, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    FPx += VVAR * (FTx + VAR(waves2_scalex) * sin(FTy * VAR(waves2_freqx)));
    FPy += VVAR * (FTy + VAR(waves2_scaley) * sin(FTx * VAR(waves2_freqy)));
    FPz += VVAR * (FTz + VAR(waves2_scalez) * sin(sqrt(sqr(FTx) + sqr(FTy)) * VAR(waves2_freqz)));
    return TRUE;
}
