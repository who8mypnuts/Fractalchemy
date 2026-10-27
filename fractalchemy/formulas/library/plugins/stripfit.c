/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        stripfit.cpp
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

// Apo Plugin by Dark-Beam: jac_asn
typedef struct
{
	double stripfit_dx;
	double dx;
} Variables;

// (missing include plugin.h)

// Set the name of this plugin
APO_PLUGIN("stripfit");


APO_VARIABLES(
	VAR_REAL(stripfit_dx, 1.0),
	);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	VAR(dx) = -0.5* VAR(stripfit_dx);
	// Always return TRUE.
	return TRUE;
}


// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	// fits a strip of unit X size and arbitrary Y size into an horizontal strip, dividing it into squares.
	// Also works for inclined strips, but adjust the strip size accordingly, example change VVAR...
	double fity;
	if (VVAR != 0.) {
		FPx += VVAR * FTx;

		if (FTy > 1.) {
			fity = fmod(FTy + 1., 2.);
			FPy += VVAR * (-1. + fity);
			FPx += (FTy - fity + 1.) * VAR(dx);
		}
		else if (FTy < -1.) {
			fity = fmod(1. - FTy, 2.);
			FPy += VVAR * (1. - fity);
			FPx += (FTy + fity - 1.) * VAR(dx);
		}
		else FPy += VVAR * FTy;
	}

	// Add 3D compatibility
	FPz += VVAR * FTz;

	return TRUE;
}