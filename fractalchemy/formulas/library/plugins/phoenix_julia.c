/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/PhoenixJulia_Apophysis_Plugin_by_TyrantWave/PJulia.c
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
	double phoenix_power;
	double phoenix_dist;
	double x_distort;
	double y_distort;
	
	double cN;
	double invN;
	double inv2PI_N;
	
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("phoenix_julia");

// Define the Variables
APO_VARIABLES(
	VAR_REAL(phoenix_power, 2.0),
	VAR_REAL(phoenix_dist, 1.0),
	VAR_REAL(x_distort, -0.5),
	VAR_REAL(y_distort, 0.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(invN) = VAR(phoenix_dist) / VAR(phoenix_power);
    VAR(inv2PI_N) = M_2PI / VAR(phoenix_power);
    VAR(cN) = VAR(phoenix_dist) / VAR(phoenix_power) / 2;

    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double preX = FTx * (VAR(x_distort) + 1.0);
    double preY = FTy * (VAR(y_distort) + 1.0);
    
    double sina, cosa;
    
    fsincos(atan2(preY, preX) * VAR(invN) + rand()*VAR(inv2PI_N), &sina, &cosa);
    double r = VVAR * pow(sqr(FTx) + sqr(FTy), VAR(cN));
    
    FPx += r * cosa;
    FPy += r * sina;
    	

    return TRUE;
}
