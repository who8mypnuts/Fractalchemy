/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        separation.c
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
	double separation_x;
	double separation_y;
	double separation_xinside;
	double separation_yinside;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("separation");

// Define the Variables
APO_VARIABLES(
	VAR_REAL(separation_x, 1.0),
	VAR_REAL(separation_y, 1.0),
	VAR_REAL(separation_xinside, 0.0),
	VAR_REAL(separation_yinside, 0.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	if(FTx > 0.0)
		FPx += VVAR * (sqrt(sqr(FTx) + sqr(VAR(separation_x)))- FTx * VAR(separation_xinside));
	else 
		FPx -= VVAR * (sqrt(sqr(FTx) + sqr(VAR(separation_x)))+ FTx * VAR(separation_xinside)) ;
	if(FTy > 0.0)
		FPy += VVAR * (sqrt(sqr(FTy) + sqr(VAR(separation_y)))- FTy * VAR(separation_yinside));
	else 
		FPy -= VVAR * (sqrt(sqr(FTy) + sqr(VAR(separation_y)))+ FTy * VAR(separation_yinside)) ;
    return TRUE;
}
