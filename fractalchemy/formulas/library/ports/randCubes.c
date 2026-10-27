/*
    Fractalchemy formula library — randCubes
    Ported by hand from randCubes.cpp (bezo97, 2017-09, "thanks for inspiration dark-beam"):
    the double4 output vector of the original is written out as scalars, which is all that changed.
    Parameter names are the plugin's own (blockSize, blockHeight, spread, seed, density).
*/

typedef struct {
    double blockSize;
    double blockHeight;
    double spread;
    int seed;
    double density;
} Variables;

#include "apoplugin.h"

APO_PLUGIN("randCubes");
APO_VARIABLES(
    VAR_REAL(blockSize, 1.0),
    VAR_REAL(blockHeight, 1.0),
    VAR_REAL(spread, 3.0),
    VAR_INTEGER(seed, 1),
    VAR_REAL(density, 1.0)
);

double hash(int a)   // http://burtleburtle.net/bob/hash/integer.html
{
    a = (a ^ 61) ^ (a >> 16);
    a = a + (a << 3);
    a = a ^ (a >> 4);
    a = a * 0x27d4eb2d;
    a = a ^ (a >> 15);
    return (double)a / (double)INT_MAX;
}

int PluginVarPrepare(Variation* vp)
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)
{
    double vx = floor(log(random01()) * (rand() % 2 ? VAR(spread) : -VAR(spread)));   // from tile_log
    double vy = floor(log(random01()) * (rand() % 2 ? VAR(spread) : -VAR(spread)));

    int blockx = (int)floor(vx);
    int blocky = (int)floor(vy);
    double z = hash(blockx * VAR(seed)) + hash(blockx + blocky * VAR(seed));   // random height for each block

    vx = ((double)blockx * VAR(density) + random01()) * VAR(blockSize);
    vy = ((double)blocky * VAR(density) + random01()) * VAR(blockSize);
    double vz = VAR(blockHeight) * z * pow(random01(), 0.125);   // fade out down

    FPx = vx * VVAR;   // not +=
    FPy = vy * VVAR;
    FPz = vz * VVAR;
    TC = z / 2.0;      // block height -> palette location
    return TRUE;
}
