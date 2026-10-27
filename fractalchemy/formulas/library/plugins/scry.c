/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        scry.c
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
	double VVAR_inv;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("scry");

// Define the Variables
APO_VARIABLES(
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	VAR(VVAR_inv) = 1.0 / (VVAR + EPS);
    return TRUE; // Always return TRUE.
}

int PluginVarCalc(Variation* vp)
{
    double t = sqr(FTx) + sqr(FTy);
	double r = 1.0 / (sqrt(t) * (t + VAR(VVAR_inv)));

	FPx += FTx * r;
	FPy += FTy * r;

    return TRUE;
}
