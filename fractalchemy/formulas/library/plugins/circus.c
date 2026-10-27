/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/circus.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2007-2009 Joel Faber
    Copyright (C) 2007-2011 Michael Faber

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
    double circus_scale;
    double circus_1_scale;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("circus");

// Define the Variables
APO_VARIABLES(
    VAR_REAL(circus_scale, 1.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(circus_1_scale) = 1.0 / VAR(circus_scale);
    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double r = sqrt(sqr(FTx) + sqr(FTy));
    double c,s;
    
    fsincos(atan2(FTy, FTx), &s, &c);
    
    if(r <= 1.0)
        r *= VAR(circus_scale);
    else
        r *= VAR(circus_1_scale);
        
    FPx += VVAR * r * c;
    FPy += VVAR * r * s;

    return TRUE;
}
