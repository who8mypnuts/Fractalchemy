/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/xcurl2/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
    double xcurl2_c1, xcurl2_c2, xcurl2_c3;

} Variables;

#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("xcurl2");
APO_VARIABLES(
	VAR_REAL(xcurl2_c1, 0.0),
	VAR_REAL(xcurl2_c2, 0.0),
	VAR_REAL(xcurl2_c3, 0.0)
);

// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: xcurl2

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

inline double cub(const double x) { return x * x * x; }

int PluginVarCalc(Variation* vp)
{
	// old, probably wrong version of curl2...

	const double re = 1 + 
		VAR(xcurl2_c1) * (FTx) + 
		VAR(xcurl2_c2) * (sqr(FTx) - sqr(FTy)) +
		VAR(xcurl2_c3) * (cub(FTx) - 3 * FTx);
		
	const double im = 
		VAR(xcurl2_c1) * (FTy) +
		VAR(xcurl2_c2) * (2 * FTx * FTy) +
		VAR(xcurl2_c3) * (3 * FTx * FTy - 1);
		
	const double r = VVAR / (sqr(re) + sqr(im));
	
	FPx += (FTx * re + FTy * im) * r;
	FPy += (FTy * re + FTx * im) * r;
	FPz += VVAR * FTz;

    return 1;
}
