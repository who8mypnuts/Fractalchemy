/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/Bubble2_Apophysis_Plugin_by_FracFx/bubble2.c
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
    double bubble_x;
    double bubble_y;
    double bubble_z;
} Variables;

// (SDK header apoplugin.h implied)


// Set the name of this plugin
APO_PLUGIN("bubble2");

// Define the Variables
APO_VARIABLES(
    VAR_REAL(bubble_x, 1.0),
    VAR_REAL(bubble_y, 1.0),
    VAR_REAL(bubble_z, 0.0)  
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    // Multiplication is faster than division, so divide in precalc, multiply in calc.


    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
;

	double T, r;
    T = ((sqr(FTx) + sqr(FTy)+ sqr(FTz))/4 + 1);
    r = VVAR / T;
	FPx += FTx * r * VAR(bubble_x);
	FPy += FTy * r * VAR(bubble_y);
		if(FTz >= 0.0)
		FPz += VVAR * (FTz + VAR(bubble_z));
	else
		FPz += VVAR * (FTz - VAR(bubble_z));
        FPz += FTz * r * VAR(bubble_z);  
 
    return TRUE;
}

