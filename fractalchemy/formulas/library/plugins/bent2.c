/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        bent2.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2008-2009 Michael Faber

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
	double bent2_x;
    double bent2_y;

    
    double vvarx;
    double vvary;
	//double bipilar_vvar;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("bent2");

// Define the Variables
APO_VARIABLES(
	VAR_REAL(bent2_x, 1.0),
	VAR_REAL(bent2_y, 1.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	VAR(vvarx) = VVAR * VAR(bent2_x);
	VAR(vvary) = VVAR * VAR(bent2_y);
	//VAR(bipolar_vvar) = 1

    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	if(FTx >= 0.0)
		FPx += VVAR * FTx;
	else
		FPx += VAR(vvarx) * FTx;
	if(FTy >= 0.0)
		FPy += VVAR * FTy;
	else
		FPy += VAR(vvary) * FTy;	

    return TRUE;
}
