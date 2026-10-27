/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/xhyperbol/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
    double xhyperbol_m00, xhyperbol_m01;
	double xhyperbol_m10, xhyperbol_m11;
	double xhyperbol_m20, xhyperbol_m21;
} Variables;

#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("xhyperbol");
APO_VARIABLES(
	VAR_REAL(xhyperbol_m00, /* default: */ 1.0),
	VAR_REAL(xhyperbol_m01, /* default: */ 0.0),
	VAR_REAL(xhyperbol_m10, /* default: */ 0.0),
	VAR_REAL(xhyperbol_m11, /* default: */ 1.0),
	VAR_REAL(xhyperbol_m20, /* default: */ 0.0),
	VAR_REAL(xhyperbol_m21, /* default: */ 0.0)
);

#define m00 vp->var.xhyperbol_m00
#define m01 vp->var.xhyperbol_m01
#define m10 vp->var.xhyperbol_m10
#define m11 vp->var.xhyperbol_m11
#define m20 vp->var.xhyperbol_m20
#define m21 vp->var.xhyperbol_m21

// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: xhyperbol

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

#define epsilon 10e-300

int PluginVarPrepare(Variation* vp)
{
    return 1;
}

inline double flip(const double amount, const double x, const double y) 
{
	return amount / (sqr(x) + sqr(y) + epsilon);
}

int PluginVarCalc(Variation* vp)
{
	const double r = flip(1, FTx, FTy);
	
	const double x = FTx * r;
	const double y = FTy * r;

	const double real = m00 * x + m01 * y + m20;
	const double imag = m10 * x + m11 * y + m21;
    const double alpha = atan2(imag, real) + M_2PI;

	double s = 0.0, c = 0.0;
	fsincos(alpha, &s, &c);

	const double rsq = sqr(real) + sqr(imag);

	const double xout = rsq * c;
	const double yout = rsq * s;

	const double rinv = flip(VVAR, xout, yout);

    FPx = xout * rinv;
    FPy = yout * rinv;

    return 1;
}

