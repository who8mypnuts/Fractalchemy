/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        plusrecip.cpp
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

// Apo Plugin by DarkBeam

typedef struct
{
	double plusrecip_ar, plusrecip_ai;
} Variables;

// (missing include plugin.h)
#include <complex>

typedef std::complex<double> cp_t;

// Set the name of this plugin
APO_PLUGIN("plusrecip");

APO_VARIABLES(
	VAR_REAL(plusrecip_ar, 4.0),
	VAR_REAL(plusrecip_ai, 0.0)
	);


int PluginVarPrepare(Variation* vp)
{
	// Always return TRUE.
	return TRUE;
}

// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	cp_t z(FTx, FTy);
	cp_t k;
	cp_t a(VAR(plusrecip_ar), VAR(plusrecip_ai));
	double aa = abs(a);
	k = z + sqrt(z*z - a);

	if (abs(k*k) < aa) {
		k = -a / aa * conj(k); // forces it to stay in its half plane but ONLY when imag(a) = 0.
	}

	if (k.real() < 0) {
		k = -k; // fixes the issue when imag(a) != 0.
	}
	FPx += VVAR * k.real();
	FPy += VVAR * k.imag();

	// Add 3D compatibility
	FPz += VVAR * FTz;
	return TRUE;
}
