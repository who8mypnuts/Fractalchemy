/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        asteria.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Mandelbrot Set Plugin v2 - Copyright 2008,2009 Jed Kelsey

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
    double asteria_alpha;
    double sina,cosa;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("asteria");

// Define the Variables
APO_VARIABLES(
    VAR_REAL_CYCLE(asteria_alpha, 0.0, 1.0, 0.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(sina) = sin(M_PI*VAR(asteria_alpha));
    VAR(cosa) = cos(M_PI*VAR(asteria_alpha));
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double x0 = VVAR * FTx;
    double y0 = VVAR * FTy;
    double xx = x0;
    double yy = y0;
    double r = sqr(xx) + sqr(yy);
    xx = sqr(fabs(xx) - 1.);
    yy = sqr(fabs(yy) - 1.);
    double r2 = sqrt(yy + xx + EPS);
    int in1 = r < 1.;
    int out2 = r2 < 1.;
    if (in1 && out2)
      in1 = ((random01()) > 0.35);
    else
      in1 = !in1;

    if (in1) { // linear
      FPx += x0;
      FPy += y0;
    } else { // asteria
      xx = x0 * VAR(cosa) - y0 * VAR(sina);
      yy = x0 * VAR(sina) + y0 * VAR(cosa);
      double nx = xx / sqrt(1.0000001 - yy * yy) * (1. - sqrt(1.0000001 - sqr(-fabs(yy) + 1.)));
      xx = nx * VAR(cosa) + yy * VAR(sina);
      yy = -nx * VAR(sina) + yy * VAR(cosa);
      FPx += xx;
      FPy += yy;
    }
    return TRUE;
}
