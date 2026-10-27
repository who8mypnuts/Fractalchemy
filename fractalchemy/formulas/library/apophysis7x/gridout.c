/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/gridout/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

    Copyright (C) 2007-2008 Michael Faber
    Copyright (C) 2007-2008 Joel Faber

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
#ifndef _APOMSVC
typedef struct
{
} Variables;
#endif

#define APO_NOVARIABLES
// (SDK header apoplugin.h implied)

// Set the name of this plugin
APO_PLUGIN("gridout");


inline double rint(double x)
{
    int temp; temp = (x >= 0. ? (int)(x + 0.5) : (int)(x - 0.5));
    return (double)temp;
}

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
    return TRUE; // Always return TRUE.
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	double x = rint(FTx);
	double y = rint(FTy);

	if (y <= 0.0)
	{
		if (x > 0.0)
		{
			if (-y >= x)
			{
				FPx += VVAR * (FTx + 1.0);
				FPy += VVAR * FTy;
			}
			else
			{
				FPx += VVAR * FTx;
				FPy += VVAR * (FTy + 1.0);
			}
		}
		else
		{
			if (y <= x)
			{
				FPx += VVAR * (FTx + 1.0);
				FPy += VVAR * FTy;
			}
			else
			{
				FPx += VVAR * FTx;
				FPy += VVAR * (FTy - 1.0);
			}
		}
	}
	else
	{
		if (x > 0.0)
		{
			if (y >= x)
			{
				FPx += VVAR * (FTx - 1.0);
				FPy += VVAR * FTy;
			}
			else
			{
				FPx += VVAR * FTx;
				FPy += VVAR * (FTy + 1.0);
			}
		}
		else
		{
			if (y > -x)
			{
				FPx += VVAR * (FTx - 1.0);
				FPy += VVAR * FTy;
			}
			else
			{
				FPx += VVAR * FTx;
				FPy += VVAR * (FTy - 1.0);
			}
		}
	}

    return TRUE;
}

// (SDK header variable_info.h implied)
