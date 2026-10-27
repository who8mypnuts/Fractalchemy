/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        apophysis-plugins/plugins/julian3Dx/apoplugin.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

typedef struct
{
	int julian3Dx_power;
	double julian3Dx_dist;

	double julian3Dx_a;
	double julian3Dx_b;
	double julian3Dx_c;
	double julian3Dx_d;
	double julian3Dx_e;
	double julian3Dx_f;

	double julian3Dx_abs_power;
	double julian3Dx_coeff_power;

} Variables;

#define _USE_MATH_DEFINES
#ifdef _APOMSVC
	// (SDK header apoplugin_msvc.h implied)
#else
	// (SDK header apoplugin.h implied)
#endif

APO_PLUGIN("julian3Dx");
APO_VARIABLES(
	VAR_INTEGER_NONZERO(julian3Dx_power, 2),
	VAR_REAL(julian3Dx_dist, 1.0),

	VAR_REAL(julian3Dx_a, 1.0),
	VAR_REAL(julian3Dx_b, 0.0),
	VAR_REAL(julian3Dx_c, 0.0),
	VAR_REAL(julian3Dx_d, 1.0),
	VAR_REAL(julian3Dx_e, 0.0),
	VAR_REAL(julian3Dx_f, 0.0)
);

#define power (vp->var.julian3Dx_power)
#define dist (vp->var.julian3Dx_dist)

#define c00 (vp->var.julian3Dx_a)
#define c01 (vp->var.julian3Dx_b)
#define c10 (vp->var.julian3Dx_c)
#define c11 (vp->var.julian3Dx_d)
#define c20 (vp->var.julian3Dx_e)
#define c21 (vp->var.julian3Dx_f)

#define x_in (*(vp->pFTx))
#define y_in (*(vp->pFTy))
#define z_in (*(vp->pFTz))

#define x_out (*(vp->pFPx))
#define y_out (*(vp->pFPy))
#define z_out (*(vp->pFPz))

#define absN (vp->var.julian3Dx_abs_power)
#define cN (vp->var.julian3Dx_coeff_power)


// (SDK header variable_info.h implied)
/*
    Apophysis Plugin: julian3Dx

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
	absN = fabs((double)power);
	cN = (dist / power - 1.0) / 2.0;

    return 1;
}

int PluginVarCalc(Variation* vp)
{
	const double z = z_in / absN;
	const double radius_square = x_in * x_in + y_in * y_in;

	const double radius_out = vp->vvar * pow(radius_square + z * z, cN);

	z_out += radius_out * z;

	const double x = c00 * x_in + c01 * y_in + c20;
	const double y = c10 * x_in + c11 * y_in + c21;

	const double rand = (int)(random01() * absN);

	const double alpha = (atan2(y, x) + M_2PI * rand) / power;
	const double gamma = radius_out * sqrt(radius_square);

	double sina, cosa;

	fsincos(alpha, &sina, &cosa);

	x_out += gamma * cosa;
	y_out += gamma * sina;

	/*
	z := FTz^ / absN;
	r2d := sqr(FTx^) + sqr(FTy^);
	r := vvar * Math.Power(r2d + sqr(z), cN); // r^n / sqrt(r)  -->  r^(n-0.5)

	FPz^ := FPz^ + r * z;

	tmp := r * sqrt(r2d);
	sincos((arctan2(FTy^, FTx^) + 2*pi*random(absN)) / N, sina, cosa);

	FPx^ := FPx^ + tmp * cosa;
	FPy^ := FPy^ + tmp * sina;
	*/

    return 1;
}
