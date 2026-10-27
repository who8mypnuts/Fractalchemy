/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        lycomplex.c
    by tools/import_apo_plugins.py. The formula compiler (fractalchemy/formulas/lang)
    runs this for both the numpy (float64) and GLSL engines, so no plugin DLL is needed.
    The original licence and attribution follow.
*/

/*
    Apophysis Plugin

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

typedef struct
{
	double lycplx_n0_r, lycplx_n1_r, lycplx_n2_r, lycplx_n3_r, lycplx_n4_r;
	double lycplx_n0_i, lycplx_n1_i, lycplx_n2_i, lycplx_n3_i, lycplx_n4_i;

	double lycplx_d0_r, lycplx_d1_r, lycplx_d2_r, lycplx_d3_r, lycplx_d4_r;
	double lycplx_d0_i, lycplx_d1_i, lycplx_d2_i, lycplx_d3_i, lycplx_d4_i;

	int lycomplexDoSqrt;
} Variables;

// (SDK header apoplugin.h implied)

APO_PLUGIN("lycomplex");

APO_VARIABLES(
	VAR_REAL(lycplx_n0_r, 0.0), VAR_REAL(lycplx_n0_i, 0.0),
	VAR_REAL(lycplx_n1_r, 1.0), VAR_REAL(lycplx_n1_i, 0.0),
	VAR_REAL(lycplx_n2_r, 0.0), VAR_REAL(lycplx_n2_i, 0.0),
	VAR_REAL(lycplx_n3_r, 0.0), VAR_REAL(lycplx_n3_i, 0.0),
	VAR_REAL(lycplx_n4_r, 0.0), VAR_REAL(lycplx_n4_i, 0.0),

	VAR_REAL(lycplx_d0_r, 0.0), VAR_REAL(lycplx_d0_i, 0.0),
	VAR_REAL(lycplx_d1_r, 0.0), VAR_REAL(lycplx_d1_i, 0.0),
	VAR_REAL(lycplx_d2_r, 1.0), VAR_REAL(lycplx_d2_i, 0.0),
	VAR_REAL(lycplx_d3_r, 0.0), VAR_REAL(lycplx_d3_i, 0.0),
	VAR_REAL(lycplx_d4_r, 0.0), VAR_REAL(lycplx_d4_i, 0.0)
);

int PluginVarPrepare(Variation* vp)
{
	VAR(lycomplexDoSqrt) = ((VAR(lycplx_n4_r) == 0.0) && (VAR(lycplx_n4_i) == 0.0) &&
							(VAR(lycplx_d4_r) == 0.0) && (VAR(lycplx_d4_r) == 0.0)) ? 0 : 1;
    return TRUE; 
}

int PluginVarCalc(Variation* vp)
{
	double z_r, z_i;
	double r2, inv_r2;
	double z2_r, z2_i;
	double invz_r, invz_i;
	double sqrtz_a, sqrtz_m;
	double sqrtz_r, sqrtz_i;
	double num_r, num_i, den_r, den_i;
	double final_inv_r2;

	// grab a local copy of z so the compiler can see it's constant
	z_r = FTx; z_i = FTy;

	// compute |z|^2 and 1/|z|^2
	r2 = z_r * z_r + z_i * z_i;
	inv_r2 = 1.0 / r2;

	// compute z^2
	z2_r = z_r * z_r - z_i * z_i;
	z2_i = 2.0 * z_r * z_i;

	// compute 1/z
	invz_r =  z_r * inv_r2;
	invz_i = -z_i * inv_r2;

	// compute sqrt(z) if it's used
	if (VAR(lycomplexDoSqrt))
	{
		sqrtz_a = atan2(z_i, z_r) + (rand() & 1) * M_PI;
		sqrtz_m = pow(r2, 0.25);
		sqrtz_r = cos(sqrtz_a) * sqrtz_m;
		sqrtz_i = sin(sqrtz_a) * sqrtz_m;
	}

	// compute real part of numerator
	num_r = (VAR(lycplx_n0_r) * z2_r - VAR(lycplx_n0_i) * z2_i) +
			(VAR(lycplx_n1_r) * z_r  - VAR(lycplx_n1_i) * z_i) +
			 VAR(lycplx_n2_r) +
			(VAR(lycplx_n3_r) * invz_r  - VAR(lycplx_n3_i) * invz_i) +
			(VAR(lycplx_n4_r) * sqrtz_r - VAR(lycplx_n4_i) * sqrtz_i);

	// compute imaginary part of numerator
	num_i = (VAR(lycplx_n0_r) * z2_i + VAR(lycplx_n0_i) * z2_r) +
			(VAR(lycplx_n1_r) * z_i  + VAR(lycplx_n1_i) * z_r) +
			 VAR(lycplx_n2_i) +
			(VAR(lycplx_n3_r) * invz_i  + VAR(lycplx_n3_i) * invz_r) +
			(VAR(lycplx_n4_r) * sqrtz_i + VAR(lycplx_n4_i) * sqrtz_r);

	// compute real part of denominator
	den_r = (VAR(lycplx_d0_r) * z2_r - VAR(lycplx_d0_i) * z2_i) +
			(VAR(lycplx_d1_r) * z_r  - VAR(lycplx_d1_i) * z_i) +
			 VAR(lycplx_d2_r) +
			(VAR(lycplx_d3_r) * invz_r  - VAR(lycplx_d3_i) * invz_i) +
			(VAR(lycplx_d4_r) * sqrtz_r - VAR(lycplx_d4_i) * sqrtz_i);

	// compute imaginary part of denominator
	den_i = (VAR(lycplx_d0_r) * z2_i + VAR(lycplx_d0_i) * z2_r) +
			(VAR(lycplx_d1_r) * z_i  + VAR(lycplx_d1_i) * z_r) +
			 VAR(lycplx_d2_i) +
			(VAR(lycplx_d3_r) * invz_i  + VAR(lycplx_d3_i) * invz_r) +
			(VAR(lycplx_d4_r) * sqrtz_i + VAR(lycplx_d4_i) * sqrtz_r);

	// output final z' = weight * numerator / denominator
	final_inv_r2 = VVAR / (den_r * den_r + den_i * den_i);
    FPx += (num_r * den_r + num_i * den_i) * final_inv_r2;
    FPy += (num_i * den_r - num_r * den_i) * final_inv_r2;
    FPz += VVAR * FTz; // support for 3D

    // must return true
    return TRUE;
}
