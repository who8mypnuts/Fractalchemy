/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        squish.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2007-2012 Joel Faber
    Copyright (C) 2007-2012 Michael Faber

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
    int squish_power;
    double inv_power;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("squish");

// Define the Variables
APO_VARIABLES(
    VAR_INTEGER_RANGE(squish_power, 2, INT_MAX, 2)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(inv_power) = 1.0 / (double) VAR(squish_power);
    // Always return TRUE.
    return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double x = fabs(FTx);
    double y = fabs(FTy);
    double s;
    double p;
    double x2, y2;

    if ( x > y)
    {
        s = x;

        if( FTx > 0.0)
        {
            p = FTy;
        }
        else
        {
            p = 4.0 * s - FTy;
        }
    }
    else
    {
        s = y;
        if( FTy > 0.0)
        {
            p = 2.0 * s - FTx;
        }
        else
        {
            p = 6.0 * s + FTx;
        }
    }

    p = VAR(inv_power) * (p + 8.0 * s * floor(VAR(squish_power) * random01()));

    if( p <= 1.0 * s )
    {
        FPx += VVAR * s;
        FPy += VVAR * p;
    }
    else if( p <= 3.0 * s)
    {
        FPx += VVAR * ( 2.0 * s - p);
        FPy += VVAR * (s);
    }
    else if( p <= 5.0 * s)
    {
        FPx -= VVAR * (s);
        FPy += VVAR * ( 4.0 * s - p);
    }
    else if( p <= 7.0 * s)
    {
        FPx -= VVAR * (6.0 * s - p);
        FPy -= VVAR * (s);
    }
    else
    {
        FPx += VVAR * (s);
        FPy -= VVAR * ( 8.0 * s - p);
    }



    return TRUE;
}
