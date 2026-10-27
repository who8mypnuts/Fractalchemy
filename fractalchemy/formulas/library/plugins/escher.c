/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        escher.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2007-2009 Joel Faber

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
    double escher_beta;

    double c;
    double d;
} Variables;

#define _USE_MATH_DEFINES
// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("escher");


// Define the Variables
APO_VARIABLES(
    VAR_REAL_CYCLE(escher_beta, -M_PI, M_PI, 0.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    fsincos(VAR(escher_beta), &VAR(d), &VAR(c));
    VAR(c) = 0.5 * (1.0 + VAR(c));
    VAR(d) = 0.5 * VAR(d);
    return TRUE; // Always return TRUE.
}

/*
Escher's Map: ( http://mathworld.wolfram.com/EschersMap.html )
  z' = z^[(1 + cos(beta) + i*sin(beta)) / 2]

Simplified using formula:
    (a + i*b)^(c + i*d) = rho^c * e^(-d * theta) * [cos(c * theta + d * ln(rho) + i * sin(c * theta + d * ln(rho)],
    where (rho, theta) is the polar coordinate equivalent of z=(x, y).
*/

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double sn, cs;
    double a = atan2(FTy, FTx); // Angular polar dimension
    double lnr = 0.5 * log(FTx*FTx + FTy*FTy); // Natural logarithm of the radial polar dimension.

    double m = VVAR * exp(VAR(c) * lnr - VAR(d) * a);

    fsincos(VAR(c) * a + VAR(d) * lnr, &sn, &cs);

    FPx += m * cs;
    FPy += m * sn;

    return TRUE;
}
