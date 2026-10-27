/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        Plugins/All/trade.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2007-2009 Joel Faber
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
    double trade_r1;
    double trade_d1;
    double trade_r2;
    double trade_d2;
    
    double c1;
    double c2;
} Variables;

// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("trade");

// Define the Variables
APO_VARIABLES(
    VAR_REAL_RANGE(trade_r1, EPS, DBL_MAX, 1.0),
    VAR_REAL_RANGE(trade_d1, 0.0, DBL_MAX, 1.0),
    VAR_REAL_RANGE(trade_r2, EPS, DBL_MAX, 1.0),
    VAR_REAL_RANGE(trade_d2, 0.0, DBL_MAX, 1.0)
);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    VAR(c1) = VAR(trade_r1) + VAR(trade_d1);
    VAR(c2) = VAR(trade_r2) + VAR(trade_d2);
    
    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
    double r;
    double s,c;
    
    if(FTx > 0.0)
    {
        r = sqrt(sqr( VAR(c1) - FTx) + sqr(FTy));
        if(r <= VAR(trade_r1))
        {
            r *= VAR(trade_r2) / VAR(trade_r1);
            fsincos( atan2(FTy, VAR(c1) - FTx), &s, &c);
            
            FPx += VVAR * (r * c - VAR(c2));
            FPy += VVAR * r * s;
        }         
        else
        {
            FPx += VVAR * FTx;
            FPy += VVAR * FTy;
        }        
    }
    else
    {
        r = sqrt(sqr( -VAR(c2) - FTx) + sqr(FTy));
        
        if(r <= VAR(trade_r2))
        {
            r *= VAR(trade_r1) / VAR(trade_r2);
            fsincos( atan2(FTy, -VAR(c2) - FTx), &s, &c);

            FPx += VVAR * (r * c + VAR(c1));
            FPy += VVAR * r * s;
        }
        else
        {
            FPx += VVAR * FTx;
            FPy += VVAR * FTy;
        }    
    }

    return TRUE;
}
