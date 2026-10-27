/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        wedge_julia.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2007-2009 Michael Faber

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
        double wedge_julia_angle;
        int wedge_julia_count;
        double comp_fac;
        double C1_2PI;
        int wedge_julia_power;
        double wedge_julia_dist;
        int rN;
        double cn;
        
} Variables;

#define _USE_MATH_DEFINES
// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("wedge_julia");

// Define the Variables
APO_VARIABLES(
              VAR_REAL(wedge_julia_angle, M_PI_2),
              VAR_INTEGER_RANGE(wedge_julia_count, 1, INT_MAX, 2), 
              VAR_INTEGER_NONZERO(wedge_julia_power, 2),
              VAR_REAL(wedge_julia_dist, 1.0)
              
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(C1_2PI) = M_1_PI*0.5;
    VAR(comp_fac) = 1.0 - VAR(wedge_julia_angle)*VAR(wedge_julia_count)*VAR(C1_2PI);
    
    VAR(rN) = (int)fabs((double)VAR(wedge_julia_power));
    VAR(cn) = VAR(wedge_julia_dist) / VAR(wedge_julia_power) / 2;
    
    // Always return TRUE.
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double r, a, cosa, sina;
    int c;
    
    r = VVAR * pow(FTx*FTx + FTy*FTy, VAR(cn));
    a = (atan2(FTy, FTx) + 2 * M_PI * (rand() % VAR(rN)))/ VAR(wedge_julia_power);
    c = floor( (VAR(wedge_julia_count)*a + M_PI)*VAR(C1_2PI) );
    
    a = a*VAR(comp_fac) + c*VAR(wedge_julia_angle);
    
    fsincos(a, &sina, &cosa);
    FPx += r * cosa;
    FPy += r * sina;
    return TRUE;
}

