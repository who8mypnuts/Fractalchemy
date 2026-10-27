/*
    Fractalchemy formula library — imported from the Apophysis plugin source
        splint.cpp
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

// Apo Plugin by JoelFaber, originally in Pascal
typedef struct
{
	double splint_b;
	double splint_h;
	double splint_theta;
	double theta, sint, cost;
} Variables;

// (missing include plugin.h)

// Set the name of this plugin
APO_PLUGIN("splint");


APO_VARIABLES(
	VAR_REAL(splint_b, 1.0),
	VAR_REAL(splint_h, 1.0),
	VAR_REAL(splint_theta, 0.0),
	);

// You must call the argument "vp".
int PluginVarPrepare(Variation* vp)
{
	double theta = 3.14159265358979323846 * VAR(splint_theta);
	double sina, cosa;
	fsincos(theta, &sina, &cosa);
	VAR(sint) = sina;
	VAR(cost) = cosa;
	// Always return TRUE.
	return TRUE;
}


// You must call the argument "vp".
int PluginVarCalc(Variation* vp)
{
	double t = FTx * VAR(cost) - FTy * VAR(sint);

	if (FTy>VAR(splint_h)) {
		t = VAR(splint_b);
	}
	else if (FTy<-VAR(splint_h)) {
		t = -VAR(splint_b);
	}
	else {
		t = (t>0) ? VAR(splint_b) : -VAR(splint_b);
	}

	FPx += (FTx + t) * VVAR;
	FPy += FTy * VVAR;

	// Add 3D compatibility
	FPz += VVAR * FTz;
	return TRUE;
}