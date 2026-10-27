/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/Tataz Utility Pack/Source/circlesplit.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

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
    double cs_radius, cs_split;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("circlesplit");


// Define the Variables
APO_VARIABLES(
    VAR_REAL(cs_radius, 1.0),
    VAR_REAL(cs_split,  0.5)
              );

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    // Always return TRUE.
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	double x0 = FTx;
	double y0 = FTy;

    double r = sqrt(sqr(x0) + sqr(y0));

    double x1, y1;

    if (r < VAR(cs_radius) - VAR(cs_split))
    {
        x1 = x0;
        y1 = y0;
    }
    else
    {
        double a = atan2(y0, x0);
        double len = r + VAR(cs_split);
        x1 = cos(a) * len;
        y1 = sin(a) * len;
    }

    FPx += VVAR * x1;
    FPy += VVAR * y1;

    return TRUE;
}
