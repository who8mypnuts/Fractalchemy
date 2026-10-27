/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/truchet2/truchet2.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2009 Joel Faber

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/

// Must define this structure before we include apoplugin.h
typedef struct
{
        double Truchet2_exponent1, Truchet2_exponent2;
        double Truchet2_width1, Truchet2_width2;
        double Truchet2_scale;
        double Truchet2_seed;
        int Truchet2_inverse;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("Truchet2");

// Define the Variables
APO_VARIABLES(
    VAR_REAL_RANGE(Truchet2_exponent1, -1.0, 3.0, 1.0),
    VAR_REAL_RANGE(Truchet2_exponent2, -1.0, 3.0, 2.0),
    VAR_REAL_RANGE(Truchet2_width1, -1.0, 2.0, 0.5),
    VAR_REAL_RANGE(Truchet2_width2, -1.0, 2.0, 0.5),
    VAR_REAL(Truchet2_scale,  10.0),
    VAR_INTEGER_RANGE(Truchet2_inverse, 0, 1, 0),
    VAR_REAL(Truchet2_seed, 50.000)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
//APO VARIABLES
    double xp = fabs((FTx / VAR(Truchet2_scale) - floor(FTx / VAR(Truchet2_scale))) - 0.5) * 2.0;
    double width = VAR(Truchet2_width1) * (1 - xp) + xp * VAR(Truchet2_width2);
    width = (width < 1.0) ? width : 1.0;

    if (width <= 0.0) {
            if (VAR(Truchet2_inverse) >= 0.5){
                FPx += (FTx) * VVAR;
                FPy += (FTy) * VVAR;
            }
    } else {
        double xp2 = VAR(Truchet2_exponent1) * (1 - xp) + xp * VAR(Truchet2_exponent2);
        double n = xp2;
        n = (n < 2.0) ? n : 2.0;

        if (n <=0 ) {
            if (VAR(Truchet2_inverse) >= 0.5){
                FPx += (FTx) * VVAR;
                FPy += (FTy) * VVAR;
            }
        } else {
            double onen = 1.0/xp2;
            double seed = fabs(VAR(Truchet2_seed));
            double seed2 = sqrt(seed + (seed/2) + EPS) / ((seed * 0.5) + EPS) * 0.25;

        //VARIABLES
            double r0 = 0.0;
            double r1 = 0.0;

        //INITIALISATION
            double x = FTx;
            double y = FTy;
            int intx = round(x);
            int inty = round(y);

            double r = x - intx;
              if (r < 0.0)
                 x = 1.0+r;
              else
                 x = r;

            r = y - inty;
              if (r < 0.0)
                 y = 1.0+r;
              else
                 y = r;

        //CALCULATE THE TILE TYPE
            double tiletype = 0.0;
            if (seed == 0.0) tiletype == 0.0;
            else if (seed == 1.0) tiletype == 1.0;
            else {
                double xrand = round(FTx);
                double yrand = round(FTy);
                xrand = xrand * seed2;
                yrand = yrand * seed2;
                double niter = xrand + yrand + xrand*yrand;
                double randint = (niter + seed) * seed2 / 2.0;
                randint = fmod((randint * 32747.0 + 12345.0), 65535.0);
                tiletype = fmod(randint, 2.0);//randint%2;
            }

        //DRAWING THE POINTS
            if (tiletype < 1.0) {
                r0 = powf((powf(fabs(x), n) + powf(fabs(y), n)), onen);
                r1 = powf((powf(fabs(x-1.0), n) + powf(fabs(y-1.0), n)), onen);
            }
            else {
                r0 = powf((powf(fabs(x-1.0), n) + powf(fabs(y), n)), onen);
                r1 = powf((powf(fabs(x), n) + powf(fabs(y-1.0), n)), onen);
            }

            double rmax = 0.5 * ( powf(2.0, onen) -1.0) * width;
            double r00 = fabs(r0 - 0.5) / rmax;
            double r11 = fabs(r1 - 0.5) / rmax;

            if (VAR(Truchet2_inverse) < 0.5){
                if (r00 < 1.0) {
                    FPx += (x + floor(FTx)) * VVAR;
                    FPy += (y + floor(FTy)) * VVAR;
                }
                if (r11 < 1.0) {
                    FPx += (x + floor(FTx)) * VVAR;
                    FPy += (y + floor(FTy)) * VVAR;
                }
            } else {
                if (r00 > 1.0 && r11 > 1.0) {
                    FPx += (x + floor(FTx)) * VVAR;
                    FPy += (y + floor(FTy)) * VVAR;
                }
            }
        }
    }

    return TRUE;
}
