/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/petal/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

#define APO_NOVARIABLES
#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	typedef struct
	{
	} Variables;
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("petal");
// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: petal

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

int PluginVarPrepare(Variation* vp)
{
	return 1;
}

int PluginVarCalc(Variation* vp)
{
	/* 
		-x- holy shit!! let me fix that for you, boy
		
		double a = cos(FTx);
		double bx = (cos(FTx)*cos(FTy))*(cos(FTx)*cos(FTy))*(cos(FTx)*cos(FTy));
		double by = (sin(FTx)*cos(FTy))*(sin(FTx)*cos(FTy))*(sin(FTx)*cos(FTy));
	*/
	double cosx, cosy, sinx, siny; 
	fsincos(FTx, &sinx, &cosx); 
	fsincos(FTy, &siny, &cosy);
	
	const double a = cosx;
	const double bx = (cosx * cosy) * (cosx * cosy) * (cosx * cosy); // cos³(x) * cos³(y)
	const double by = (sinx * cosy) * (sinx * cosy) * (sinx * cosy); // sin³(x) * cos³(y)

	FPx += VVAR * a * bx;
	FPy += VVAR * a * by;

	return TRUE;
}
